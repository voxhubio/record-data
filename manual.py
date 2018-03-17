# Manual audio recording script, based on Silvius
__author__ = 'dwk'

import argparse
import threading
import sys
import pyaudio
import audioop  # for resampling audio at 16KHz
import time

reconnect_mode = False
fatal_error = False

class SpeechRecorder():
    def __init__(self, mic=1, byterate=16000):
        self.mic = mic
        self.byterate = byterate
        self.chunk = 0
        self.audio_gate = 0

    def start(self):
        pa = pyaudio.PyAudio()
        sample_rate = self.byterate
        stream = None 
        
        while stream is None:
            try:
                # try adjusting this if you want fewer network packets
                self.chunk = 2048 * 2 * sample_rate / self.byterate

                mic = self.mic
                if mic == -1:
                    mic = pa.get_default_input_device_info()['index']
                    print >> sys.stderr, "Selecting default mic"
                print >> sys.stderr, "Using mic #", mic
                stream = pa.open(
                    rate = sample_rate,
                    format = pyaudio.paInt16,
                    channels = 1,
                    input = True,
                    input_device_index = mic,
                    frames_per_buffer = self.chunk)
            except IOError, e:
                if(e.errno == -9997 or e.errno == 'Invalid sample rate'):
                    new_sample_rate = int(pa.get_device_info_by_index(mic)['defaultSampleRate'])
                    if(sample_rate != new_sample_rate):
                        sample_rate = new_sample_rate
                        continue
                print >> sys.stderr, "\n", e
                print >> sys.stderr, "\nCould not open microphone. Please try a different device."
                global fatal_error
                fatal_error = True
                sys.exit(0)
     
        def mic_to_ws():  # uses stream
            try:
                print >> sys.stderr, "\nLISTENING TO MICROPHONE"
                last_state = None
                while True:
                    data = stream.read(self.chunk)
                    if self.audio_gate > 0:
                        rms = audioop.rms(data, 2)
                        if rms < self.audio_gate:
                            data = '\00' * len(data)
                    #if sample_chan == 2:
                    #    data = audioop.tomono(data, 2, 1, 1)
                    if sample_rate != self.byterate:
                        (data, last_state) = audioop.ratecv(data, 2, 1, sample_rate, self.byterate, last_state)

                    self.send_data(data)
            except IOError, e:
                # usually a broken pipe
                print e
            except AttributeError:
                # currently raised when the socket gets closed by main thread
                pass

            try:
                self.close()
            except IOError:
                pass

        threading.Thread(target=mic_to_ws).start()


def setup():
    parser = argparse.ArgumentParser(description='Microphone client for silvius')
    parser.add_argument('-d', '--device', default="-1", dest="device", type=int, help="Select a different microphone (give device ID)")
    #parser.add_argument('-k', '--keep-going', action="store_true", help="Keep reconnecting to the server after periods of silence")
    #parser.add_argument('-g', '--audio-gate', default=0, type=int, help="Audio-gate level to reduce detections when not talking")
    parser.add_argument('-L', '--log-keystrokes', default=0, type=int, help="Record and log all X11 keystrokes")
    args = parser.parse_args()

    recorder = SpeechRecorder(byterate=16000, mic=args.device, log_keystrokes=args.log_keystrokes)
    recorder.start()

def main():
    try:
        setup()
    except KeyboardInterrupt:
        print >> sys.stderr, "\nexiting..."

if __name__ == "__main__":
    main()

