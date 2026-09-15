import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import tempfile
import os
import threading
import time

class AudioRecorder:
    def __init__(self, sample_rate=16000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.max_duration = int(os.getenv("VOICE_MAX_RECORD_SECONDS", "30"))
        self.min_duration = int(os.getenv("VOICE_MIN_RECORD_SECONDS", "1"))
        self.silence_threshold = float(os.getenv("VOICE_SILENCE_THRESHOLD", "0.01"))
        
    def record_until_interrupt(self, filename=None) -> str:
        """Records audio until silence is detected."""
        if filename is None:
            fd, filename = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            
        print("Listening... (Speak now, auto-stops on silence)")
        
        recording = []
        try:
            stream = sd.InputStream(samplerate=self.sample_rate, channels=self.channels, dtype='int16')
        except Exception as e:
            print(f"[WARN] Microphone error: {e}")
            return None
            
        with stream:
            start_time = time.time()
            silence_start = None
            
            while True:
                data, overflowed = stream.read(self.sample_rate // 10) # 100ms chunks
                recording.append(data)
                
                # Check silence (RMS energy)
                data_float = data.astype(np.float32) / 32768.0
                rms = np.sqrt(np.mean(data_float**2))
                
                duration = time.time() - start_time
                
                if rms < self.silence_threshold:
                    if silence_start is None:
                        silence_start = time.time()
                    elif (time.time() - silence_start) > 1.5 and duration >= self.min_duration:
                        # 1.5 seconds of silence
                        break
                else:
                    silence_start = None
                    
                if duration >= self.max_duration:
                    break
                
        if not recording:
            return None
            
        audio_data = np.concatenate(recording, axis=0)
        wav.write(filename, self.sample_rate, audio_data)
        
        return filename

    def start_recording(self):
        """Starts background recording for UI."""
        self._stop_event = threading.Event()
        self._recording_data = []
        try:
            self._recording_stream = sd.InputStream(samplerate=self.sample_rate, channels=self.channels, dtype='int16')
            self._recording_stream.start()
        except Exception as e:
            print(f"[WARN] Microphone error: {e}")
            return
        
        def _record_loop():
            start_time = time.time()
            while not self._stop_event.is_set():
                if time.time() - start_time > self.max_duration:
                    break
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
        if hasattr(self, '_record_thread') and self._record_thread.is_alive():
            self._record_thread.join(timeout=1.0)
            
        if hasattr(self, '_recording_stream'):
            self._recording_stream.stop()
            self._recording_stream.close()
        
        if not self._recording_data:
            return None
            
        fd, filename = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        
        audio_data = np.concatenate(self._recording_data, axis=0)
        wav.write(filename, self.sample_rate, audio_data)
        return filename
