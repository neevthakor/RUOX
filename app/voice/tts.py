import os
import threading
import queue

class TTSEngine:
    def __init__(self):
        self._is_available = False
        self._q = queue.Queue()
        self._worker_thread = None
        self._running = False
        
    def initialize(self):
        try:
            import pyttsx3
            # Test initialization to see if the module works
            temp_engine = pyttsx3.init()
            del temp_engine
            
            self._is_available = True
            self._running = True
            
            # SAPI5 on Windows requires COM to be initialized on the same thread it is used.
            # We spawn a dedicated worker thread to handle all pyttsx3 interactions.
            self._worker_thread = threading.Thread(target=self._tts_worker, daemon=True)
            self._worker_thread.start()
        except ImportError:
            pass
        except Exception as e:
            print(f"[WARN] Error initializing TTS: {e}")
            
    def _tts_worker(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            rate = int(os.getenv("TTS_RATE", "150"))
            volume = float(os.getenv("TTS_VOLUME", "1.0"))
            engine.setProperty('rate', rate)
            engine.setProperty('volume', volume)
            
            while self._running:
                try:
                    text = self._q.get(timeout=0.5)
                    if text is None:
                        # Stop signal
                        break
                    
                    if text == "__STOP__":
                        engine.stop()
                        self._q.task_done()
                        continue
                        
                    engine.say(text)
                    engine.runAndWait()
                    self._q.task_done()
                except queue.Empty:
                    pass
                except Exception as e:
                    print(f"[WARN] TTS Worker Error: {e}")
        except Exception as e:
            print(f"[WARN] TTS Worker Initialization Error: {e}")
            self._is_available = False
            
    def is_available(self) -> bool:
        return self._is_available
        
    def speak(self, text: str):
        if not self._is_available or not self._running:
            return
        # Put text into queue for the worker thread to process
        self._q.put(text)

    def stop(self):
        if self._is_available and self._running:
            # We put a special token or clear queue
            with self._q.mutex:
                self._q.queue.clear()
            self._q.put("__STOP__")
