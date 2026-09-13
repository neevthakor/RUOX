import os
import glob
from app.vision.models import BoundingBox

class VisionSecurityError(Exception):
    pass

def validate_coordinates(bbox: BoundingBox, screen_w: int, screen_h: int) -> bool:
    """Validate coordinates are within screen boundaries."""
    if bbox.x < 0 or bbox.y < 0:
        return False
    if bbox.x + bbox.w > screen_w:
        return False
    if bbox.y + bbox.h > screen_h:
        return False
    return True

def get_temp_screenshot_dir() -> str:
    path = os.getenv("SCREEN_TEMP_DIR", "data/runtime/screens/")
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path

def cleanup_screenshots():
    """Removes temporary screenshots."""
    dir_path = get_temp_screenshot_dir()
    for f in glob.glob(os.path.join(dir_path, "*.png")):
        try:
            os.remove(f)
        except Exception:
            pass
