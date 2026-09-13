from pydantic import BaseModel
from typing import List, Optional, Tuple

class BoundingBox(BaseModel):
    x: int
    y: int
    w: int
    h: int
    
class TextElement(BaseModel):
    text: str
    bbox: Optional[BoundingBox] = None
    confidence: Optional[float] = None

class ScreenRegion(BaseModel):
    label: str
    bbox: BoundingBox

class ScreenContext(BaseModel):
    width: int
    height: int
    active_window: Optional[str] = None
    elements: List[TextElement] = []
    regions: List[ScreenRegion] = []
    timestamp: float
    screenshot_id: str
