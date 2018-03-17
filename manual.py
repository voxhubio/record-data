# Manual audio recording script, based on Silvius
__author__ = 'dwk'

import sys
import argparse
import threading
import time     # for generating unique filenames
from pynput import keyboard  # for recording keypresses

reconnect_mode = False
fatal_error = False

class SpeechRecorder():
    def __init__(self, mic=1, byterate=16000):
        self.mic = mic
        self.byterate = byterate
        self.chunk = 0
        self.audio_gate = 0
        self.running = False
        self.thread = None

    def start(self):
        # these imports are here to avoid their debugging output earlier
        import pyaudio  # for recording audio
        import audioop  # for resampling audio at 16KHz
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
                while self.running:
                    data = stream.read(self.chunk)
                    if self.audio_gate > 0:
                        rms = audioop.rms(data, 2)
                        if rms < self.audio_gate:
                            data = '\00' * len(data)
                    #if sample_chan == 2:
                    #    data = audioop.tomono(data, 2, 1, 1)
                    if sample_rate != self.byterate:
                        (data, last_state) = audioop.ratecv(data, 2, 1, sample_rate, self.byterate, last_state)

                    self.handle_data(data)
            except IOError, e:
                # usually a broken pipe
                print e
            except AttributeError:
                # currently raised when the socket gets closed by main thread
                pass
            print >> sys.stderr, "Stop listening to microphone"

            #try:
            #    self.close()
            #except IOError:
            #    pass
            self.running = False

        self.running = True
        self.thread = threading.Thread(target=mic_to_ws)
        self.thread.start()

    def handle_data(self, data):
        sys.stderr.write('.')
    def stop(self):
        self.running = False
    def join(self):
        self.thread.join()

class KeyRecorder():
    def __init__(self, filename):
        self.listener = None
        self.file = open(filename, "w")

    def start(self):
        def on_press(key):
            #try:
            #    print('alphanumeric key {0} pressed'.format(key.char))
            #except AttributeError:
            #    print('special key {0} pressed'.format(key))
            sys.stderr.write("+")
            t = "%.02f" % time.time()
            print >> self.file, t, "v", key

        def on_release(key):
            #print('{0} released'.format(key))
            sys.stderr.write("-")
            t = "%.02f" % time.time()
            print >> self.file, t, "^", key

        print >> sys.stderr, "\nRecording keypresses..."

        # Collect events until released
        self.listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.listener.start()

    def stop(self):
        self.listener.stop()
    def join(self):
        self.listener.join()
        self.file.close()
        print >> sys.stderr, "Stop recording keypresses"


class Recorder():
    def __init__(self):
        self.speech_recorder = None
        self.key_recorder = None

    def setup(self):
        parser = argparse.ArgumentParser(description='Microphone client for silvius')
        parser.add_argument('-d', '--device', default="-1", dest="device", type=int, help="Select a different microphone (give device ID)")
        #parser.add_argument('-k', '--keep-going', action="store_true", help="Keep reconnecting to the server after periods of silence")
        #parser.add_argument('-g', '--audio-gate', default=0, type=int, help="Audio-gate level to reduce detections when not talking")
        parser.add_argument('-o', '--output-directory', default='.', help="Directory to save recorded audio and keystrokes")
        parser.add_argument('-n', '--name', default='rec', help="Name of recordings, useful to tag with physical location")
        parser.add_argument('-A', '--log-audio', default=1, action="store_true", help="Record and log audio (enabled by default)")
        parser.add_argument('-L', '--log-keystrokes', action="store_true", help="Record and log all X11 keystrokes")
        args = parser.parse_args()

        filename_time = "%.02f" % time.time()
        filename_prefix = args.output_directory + '/' + args.name + "-" + filename_time

        if(args.log_audio):
            self.speech_recorder = SpeechRecorder(byterate=16000, mic=args.device)
            self.speech_recorder.start()

        if(args.log_keystrokes):
            self.key_recorder = KeyRecorder(filename=filename_prefix + ".txt")
            self.key_recorder.start()

    def main(self):
        try:
            self.setup()
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print >> sys.stderr, "\nexiting..."

        if(self.speech_recorder != None):   self.speech_recorder.stop()
        if(self.key_recorder != None):      self.key_recorder.stop()
        if(self.speech_recorder != None):   self.speech_recorder.join()
        if(self.key_recorder != None):      self.key_recorder.join()
        print >> sys.stderr, "done."

if __name__ == "__main__":
    Recorder().main()

