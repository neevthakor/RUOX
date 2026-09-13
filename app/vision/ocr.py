import abc
import os
from typing import List, Optional
from PIL import Image
from app.vision.models import TextElement, BoundingBox

class OCRProvider(abc.ABC):
    @abc.abstractmethod
    def extract_text(self, filepath: str) -> List[TextElement]:
        pass

class TesseractOCRProvider(OCRProvider):
    def __init__(self):
        # Allow custom path via env
        import pytesseract
        tess_path = os.getenv("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if os.path.exists(tess_path):
            pytesseract.pytesseract.tesseract_cmd = tess_path
            self.available = True
        else:
            # We don't crash, we just mark as unavailable
            self.available = False
            
    def extract_text(self, filepath: str) -> List[TextElement]:
        if not self.available:
            raise RuntimeError("OCR Provider is unavailable. Tesseract is not installed or configured properly.")
            
        import pytesseract
        img = Image.open(filepath)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        
        elements = []
        n_boxes = len(data['level'])
        for i in range(n_boxes):
            text = data['text'][i].strip()
            if text:
                try:
                    conf = float(data['conf'][i])
                except ValueError:
                    conf = 0.0
                
                # Only keep reasonably confident text
                if conf > 30.0:
                    bbox = BoundingBox(
                        x=data['left'][i],
                        y=data['top'][i],
                        w=data['width'][i],
                        h=data['height'][i]
                    )
                    elements.append(TextElement(text=text, bbox=bbox, confidence=conf))
                    
        return elements

def get_ocr_provider() -> OCRProvider:
    return TesseractOCRProvider()
