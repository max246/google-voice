from google.assistant.embedded.v1alpha1 import embedded_assistant_pb2
from google.rpc import code_pb2

import logging
import os.path
import sys
import re


from googlesamples.assistant import (
    assistant_helpers,
    audio_helpers,
    auth_helpers,
    common_settings
)

ASSISTANT_API_ENDPOINT = 'embeddedassistant.googleapis.com'
END_OF_UTTERANCE = embedded_assistant_pb2.ConverseResponse.END_OF_UTTERANCE
DIALOG_FOLLOW_ON = embedded_assistant_pb2.ConverseResult.DIALOG_FOLLOW_ON
CLOSE_MICROPHONE = embedded_assistant_pb2.ConverseResult.CLOSE_MICROPHONE

api_endpoint = ASSISTANT_API_ENDPOINT
credentials = os.path.join(
                  os.path.dirname(os.path.realpath(__file__)), "..",
                  common_settings.ASSISTANT_CREDENTIALS_FILENAME
              )

verbose = False
input_audio_file = None
output_audio_file = None
audio_sample_rate = common_settings.DEFAULT_AUDIO_SAMPLE_RATE
audio_sample_width = common_settings.DEFAULT_AUDIO_SAMPLE_WIDTH
audio_iter_size = common_settings.DEFAULT_AUDIO_ITER_SIZE
audio_block_size = common_settings.DEFAULT_AUDIO_DEVICE_BLOCK_SIZE
audio_flush_size = common_settings.DEFAULT_AUDIO_DEVICE_FLUSH_SIZE
grpc_deadline = common_settings.DEFAULT_GRPC_DEADLINE

class Voice:

    def __init__(self):

        self._conversation_state_bytes = None
        self._volume_percentage = 100

        #   logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)

        self._found_command = False
        self._stop_playback = True

        self.init_grpc()

    def init_grpc(self):
        try:
            creds = auth_helpers.load_credentials(
                credentials, scopes=[common_settings.ASSISTANT_OAUTH_SCOPE]
            )
        except Exception as e:
            logging.error('Error loading credentials: %s', e)
            logging.error('Run auth_helpers to initialize new OAuth2 credentials.')

        # Create gRPC channel
        grpc_channel = auth_helpers.create_grpc_channel(
            api_endpoint, creds,
            ssl_credentials_file=None,
            grpc_channel_options=None
        )
        logging.info('Connecting to %s', api_endpoint)
        # Create Google Assistant API gRPC client.
        self._assistant = embedded_assistant_pb2.EmbeddedAssistantStub(grpc_channel)

    def init_sound(self):
        # Configure audio source and sink.
        audio_device = None
        if input_audio_file:
            self._audio_source = audio_helpers.WaveSource(
                open(input_audio_file, 'rb'),
                sample_rate=audio_sample_rate,
                sample_width=audio_sample_width
            )
        else:
            self._audio_source = audio_device = (
                audio_device or audio_helpers.SoundDeviceStream(
                    sample_rate=audio_sample_rate,
                    sample_width=audio_sample_width,
                    block_size=audio_block_size,
                    flush_size=audio_flush_size
                )
            )
        if output_audio_file:
            self._audio_sink = audio_helpers.WaveSink(
                open(output_audio_file, 'wb'),
                sample_rate=audio_sample_rate,
                sample_width=audio_sample_width
            )
        else:
            self._audio_sink = audio_device = (
                audio_device or audio_helpers.SoundDeviceStream(
                    sample_rate=audio_sample_rate,
                    sample_width=audio_sample_width,
                    block_size=audio_block_size,
                    flush_size=audio_flush_size
                )
            )

        # Create conversation stream with the given audio source and sink.
        self._conversation_stream = audio_helpers.ConversationStream(
            source=self._audio_source,
            sink=self._audio_sink,
            iter_size=audio_iter_size,
        )

    # This generator yields ConverseRequest to send to the gRPC
    # Google Assistant API.
    def gen_converse_requests(self):
        converse_state = None
        if self._conversation_state_bytes:
            logging.debug('Sending converse_state: %s',
                          self._conversation_state_bytes)
            converse_state = embedded_assistant_pb2.ConverseState(
                conversation_state=self._conversation_state_bytes,
            )
        config = embedded_assistant_pb2.ConverseConfig(
            audio_in_config=embedded_assistant_pb2.AudioInConfig(
                encoding='LINEAR16',
                sample_rate_hertz=int(audio_sample_rate),
            ),
            audio_out_config=embedded_assistant_pb2.AudioOutConfig(
                encoding='LINEAR16',
                sample_rate_hertz=int(audio_sample_rate),
                volume_percentage=self._volume_percentage,
            ),
            converse_state=converse_state
        )
        # The first ConverseRequest must contain the ConverseConfig
        # and no audio data.
        yield embedded_assistant_pb2.ConverseRequest(config=config)
        for data in self._conversation_stream:
            # Subsequent requests need audio data, but not config.
            yield embedded_assistant_pb2.ConverseRequest(audio_in=data)


    def iter_converse_requests(self):
        for c in self.gen_converse_requests():
            assistant_helpers.log_converse_request_without_audio(c)
            yield c
        self._conversation_stream.start_playback()


    def search_command(self,command):
        #Return True if the command has been found otherwise False
        return False

    def run(self):
        wait_for_user_trigger = False
        self._conversation_stream.start_recording()
        logging.info('Recording audio request.')

        i = -1

        # This generator yields ConverseResponse proto messages
        # received from the gRPC Google Assistant API.
        for resp in self._assistant.Converse(self.iter_converse_requests(),
                                       grpc_deadline):
            assistant_helpers.log_converse_response_without_audio(resp)
            if resp.error.code != code_pb2.OK:
                logging.error('server error: %s', resp.error.message)
                break
            if resp.event_type == END_OF_UTTERANCE:
                logging.info('End of audio request detected')
                self._conversation_stream.stop_recording()
            if resp.result.spoken_request_text:
                i = 0
                self._stop_playback = False
                logging.info('Transcript of user request: "%s".',
                             resp.result.spoken_request_text)
                logging.info('Playing assistant response.')
                #Check if the voice spoken is part of a USER COMMAND, otherwise use Google Assistant SDK
                if self.search_command(resp.result.spoken_request_text):
                    self._found_command = True
                else:
                    i = -1
                    self._stop_playback = True

            if len(resp.audio_out.audio_data) > 0:
                self._conversation_stream.write(resp.audio_out.audio_data)
            if resp.result.spoken_response_text:
                logging.info(
                    'Transcript of TTS response '
                    '(only populated from IFTTT): "%s".',
                    resp.result.spoken_response_text)
            if resp.result.conversation_state:
                conversation_state_bytes = resp.result.conversation_state
            if resp.result.volume_percentage != 0:
                volume_percentage = resp.result.volume_percentage
                logging.info('Volume should be set to %s%%', volume_percentage)
            if resp.result.microphone_mode == DIALOG_FOLLOW_ON:
                wait_for_user_trigger = False
                logging.info('Expecting follow-on query from user.')
                print "expetinggg"
            elif resp.result.microphone_mode == CLOSE_MICROPHONE:
                wait_for_user_trigger = True

            #Little hack to break the loop after 2 times, this has been found out that can block play back audio if the command is custom
            if i >= 0:
                i = i+1
            if i > 2:
                break
        logging.info('Finished playing assistant response.')
        self._conversation_stream.stop_playback()
        return wait_for_user_trigger

    def stop(self):
        self._conversation_stream.close()
