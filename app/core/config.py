import os
from pathlib import Path

def get_project_root() -> Path:
    """
    Returns the canonical project root for RUOX.
    Resolves in this order:
    1. RUOX_PROJECT_ROOT environment variable.
    2. Dynamically determined based on the location of this file.
    """
    env_root = os.getenv("RUOX_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()
        
    # This file is in app/core/config.py
    # So parent is core, parent.parent is app, parent.parent.parent is RUOX root.
    return Path(__file__).parent.parent.parent.resolve()

def get_system_context() -> str:
    import platform
    root = get_project_root()
    cwd = Path.cwd().resolve()
    os_name = platform.system()
    
    context = (
        f"Context Info:\n"
        f"- Operating System: {os_name}\n"
        f"- RUOX Project Root: {root}\n"
        f"- Current Working Directory: {cwd}\n\n"
        f"IMPORTANT: When the user refers to 'my RUOX directory', 'the RUOX folder', "
        f"'my project', 'this project', 'the project directory', or 'RUOX tests', "
        f"ALWAYS use the exact RUOX Project Root path ({root}) as the target path or working directory."
    )
    return context
