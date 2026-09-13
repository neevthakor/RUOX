import os
import threading

class TTSEngine:
    def __init__(self):
        self._is_available = False
        self.engine = None
        self._lock = threading.Lock()
        
    def initialize(self):
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            rate = int(os.getenv("TTS_RATE", "150"))
            volume = float(os.getenv("TTS_VOLUME", "1.0"))
            self.engine.setProperty('rate', rate)
            self.engine.setProperty('volume', volume)
            self._is_available = True
        except ImportError:
            pass
        except Exception as e:
            print(f"[WARN] Error initializing TTS: {e}")
            
    def is_available(self) -> bool:
        return self._is_available
        
    def speak(self, text: str):
        if not self._is_available or not self.engine:
            return
            
        with self._lock:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except RuntimeError:
                pass

    def stop(self):
        if self._is_available and self.engine:
            try:
                self.engine.stop()
            except Exception:
                pass
