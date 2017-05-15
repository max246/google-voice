import snowboydecoder
import threading

class Wakeup:

    def __init__(self,model,cb):
        self._detector = snowboydecoder.HotwordDetector(model, sensitivity=0.5)
        self._interruped = False
        self._cb = cb

    def start_audio(self):
        self._interruped = False
        self._detector.start_audio()

    def callback(self):
        snowboydecoder.play_audio_file()
        self._cb()

    def run(self):
        self._detector.start(detected_callback=self.callback,
               interrupt_check=self.interrupt_callback,
               sleep_time=0.03)
        self._detector.terminate()

    def interrupt_callback(self):
        return self._interruped

    def stop(self):
        self._interruped = True


class ThreadWakeup(threading.Thread):

    def __init__(self,wakeup):
         super(ThreadWakeup, self).__init__()
         self._stop = threading.Event()
         self._wakeup = wakeup

    def run(self):
        self._wakeup.run()

    def stop(self):
        self._wakeup.stop()
