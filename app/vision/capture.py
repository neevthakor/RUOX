import os
import time
import uuid
import ctypes
from PIL import ImageGrab, Image
from typing import Dict, Any, Optional
from app.vision.safety import get_temp_screenshot_dir

class ScreenCapturer:
    def __init__(self):
        self.max_width = int(os.getenv("SCREEN_MAX_WIDTH", "3840"))
        self.max_height = int(os.getenv("SCREEN_MAX_HEIGHT", "2160"))

    def get_active_window_title(self) -> Optional[str]:
        """Gets the title of the foreground window on Windows."""
        if os.name != 'nt':
            return None
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
            return title if title else None
        except Exception:
            return None

    def capture(self) -> Dict[str, Any]:
        """Captures the primary screen, scales if necessary, and saves temporarily."""
        # Grab primary monitor
        img = ImageGrab.grab(all_screens=False)
        w, h = img.size
        
        # Validate dimensions
        if w > self.max_width or h > self.max_height:
            # Scale down
            ratio = min(self.max_width / w, self.max_height / h)
            new_w, new_h = int(w * ratio), int(h * ratio)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            w, h = new_w, new_h

        screenshot_id = f"scr_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        filepath = os.path.join(get_temp_screenshot_dir(), f"{screenshot_id}.png")
        img.save(filepath, format="PNG")

        return {
            "screenshot_id": screenshot_id,
            "filepath": filepath,
            "width": w,
            "height": h,
            "timestamp": time.time(),
            "active_window": self.get_active_window_title()
        }

screen_capturer = ScreenCapturer()
