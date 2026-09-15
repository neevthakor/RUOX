import os
import re

class STTEngine:
    def __init__(self):
        self.model_size = os.getenv("STT_MODEL", "tiny.en")
        self.device = os.getenv("STT_DEVICE", "cpu")
        self.model = None
        self._is_available = False
        
    def initialize(self):
        if self._is_available and self.model is not None:
            return
            
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(self.model_size, device=self.device, compute_type="int8")
            self._is_available = True
        except ImportError:
            pass
        except Exception as e:
            print(f"[WARN] Error initializing STT: {e}")
            
    def is_available(self) -> bool:
        return self._is_available
        
    def transcribe(self, audio_path: str) -> str:
        if not self._is_available or not self.model:
            return ""
            
        try:
            segments, info = self.model.transcribe(audio_path, beam_size=5, vad_filter=True, vad_parameters=dict(min_silence_duration_ms=500))
            text = " ".join([segment.text for segment in segments])
            text = text.strip()
            
            # Normalize common whisper hallucinations
            lower_text = text.lower()
            hallucinations = ["thank you.", "thanks for watching.", "thanks for watching!", "you"]
            if lower_text in hallucinations:
                return ""
                
            # Basic normalization (remove multiple spaces)
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        except Exception as e:
            print(f"[WARN] STT transcription error: {e}")
            return ""
