from lib.Voice import  *
from lib.Wakeup import *
import time

_scan_voice = False
_thr_wakeup = None

def found_hot_word():
    global _scan_voice
    _scan_voice = True

wakeup = Wakeup(["jarvis.pmdl"],found_hot_word)

def init_thread_wakeup():
    global _thr_wakeup
    wakeup.start_audio()
    _thr_wakeup = ThreadWakeup(wakeup)
    _thr_wakeup.setDaemon(True)
    _thr_wakeup.start()

init_thread_wakeup()
voice = Voice()

while True:
    if _scan_voice:
        _thr_wakeup.stop()

        voice.init_sound()
        while True:#Make a loop until there is not action request
            if voice.run():
                break
        voice.stop()
        _scan_voice = False

        init_thread_wakeup()
    else:
        time.sleep(0.1)

























