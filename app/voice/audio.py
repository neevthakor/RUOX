import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import tempfile
import os
import threading

class AudioRecorder:
    def __init__(self, sample_rate=16000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels

    def record_until_interrupt(self, filename=None) -> str:
        """Records audio until the user presses Enter."""
        if filename is None:
            fd, filename = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            
        print("Recording... (Press Enter to stop)")
        
        recording = []
        stream = sd.InputStream(samplerate=self.sample_rate, channels=self.channels, dtype='int16')
        
        with stream:
            stop_event = threading.Event()
            
            def wait_for_enter():
                input()
                stop_event.set()
                
            t = threading.Thread(target=wait_for_enter)
            t.daemon = True
            t.start()
            
            while not stop_event.is_set():
                data, overflowed = stream.read(self.sample_rate // 2)
                recording.append(data)
                
        if not recording:
            return None
            
        audio_data = np.concatenate(recording, axis=0)
        wav.write(filename, self.sample_rate, audio_data)
        
        return filename

    def start_recording(self):
        """Starts background recording for UI."""
        self._stop_event = threading.Event()
        self._recording_data = []
        self._recording_stream = sd.InputStream(samplerate=self.sample_rate, channels=self.channels, dtype='int16')
        self._recording_stream.start()
        
        def _record_loop():
            while not self._stop_event.is_set():
                # use a short read to remain responsive
                try:
                    data, overflowed = self._recording_stream.read(1024)
                    self._recording_data.append(data)
                except Exception:
                    break
                    
        self._record_thread = threading.Thread(target=_record_loop, daemon=True)
        self._record_thread.start()

    def stop_recording(self) -> str:
        """Stops background recording and returns filename."""
        if not hasattr(self, '_stop_event') or self._stop_event.is_set():
            return None
            
        self._stop_event.set()
        self._record_thread.join()
        self._recording_stream.stop()
        self._recording_stream.close()
        
        if not self._recording_data:
            return None
            
        fd, filename = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        
        audio_data = np.concatenate(self._recording_data, axis=0)
        wav.write(filename, self.sample_rate, audio_data)
        return filename
