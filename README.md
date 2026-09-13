# RUOX — Personal AI Operating Assistant

RUOX is a local-first, voice-capable, tool-using personal AI agent.

## Core Principles
LOCAL-FIRST, PRIVACY-FIRST, SECURITY-FIRST, VOICE-FIRST, PROACTIVE, MODEL-AGNOSTIC, TOOL-DRIVEN, CONTEXT-AWARE, EXTENSIBLE, RELIABLE.

## Privacy Classification
- **SECRET**: Local only. Full stop. No exceptions.
- **SENSITIVE / PRIVATE**: Local only by default.
- **INTERNAL**: Local (cloud only for high complexity if user enabled).
- **PUBLIC**: Cloud allowed if configured, local otherwise.

A user-facing **"LOCAL ONLY" master switch** overrides all routing logic, ensuring no external AI services are used.

# RUOX Local AI Assistant

RUOX is a fully local, secure AI desktop assistant powered by Ollama and Qwen 2.5 7B.

## Development Status
* **P0**: Foundation (LLM Router, Agent Loop, Tool Registry, Security/Permissions, Redaction) - **COMPLETE**
* **P1**: Interactive & Voice Mode (faster-whisper STT, pyttsx3 TTS, CLI REPL) - **COMPLETE**
* **P2**: Controlled Computer Automation (Filesystem, Shell, App Launcher, Safety Policy) - **COMPLETE**

## Features & Available Tools
* **Voice Mode**: Push-to-talk voice interface using lightweight, fully local models.
* **Computer Tools**:
  * `open_application`: Launch common apps safely (e.g., Chrome, VS Code, Notepad).
  * `list_directory`, `get_file_info`: Read-only filesystem exploration.
  * `create_directory`, `open_path`: Controlled filesystem modifications.
  * `run_command`: Controlled shell command execution.
* **System Tools**: `get_current_time`, `get_system_info`.

## Security Model
RUOX runs strictly in `LOCAL_ONLY=true` mode. It guarantees:
1. **No Data Exfiltration**: No API calls to cloud LLMs, cloud TTS, or cloud STT.
2. **Permission Model**: Every tool defines a permission level (`READ`, `LOW_RISK`, `MEDIUM_RISK`, `HIGH_RISK`).
3. **Shell Safety Policy**: Commands are actively classified as `SAFE`, `BLOCKED`, or `CONFIRMATION_REQUIRED` by the security layer, NOT the LLM.
4. **Action Previews**: Any action requiring confirmation displays a preview of the arguments and pauses for explicit `y/n` user approval.
5. **Redaction**: Common secret patterns (API keys, passwords, tokens) are aggressively redacted from tool output before being sent to the LLM.

## How to Run

### Text Mode
```bash
python -m app.main
```
Try asking:
- "What time is it?"
- "Open Notepad."
- "List the files in this directory."
- "Run the python tests."

### Voice Mode
```bash
python -m app.main --voice
```
*(Press Enter to stop recording after speaking)*

### Diagnostics & Tests
To verify your system compatibility and safety policies:
```bash
python -m scripts.diagnostics
python -m unittest discover tests
```

## Windows Setup Instructions

### 1. Python Environment
Requires Python 3.10+.
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Ollama & Model
1. Install Ollama from [ollama.com](https://ollama.com).
2. Start Ollama and download the model:
```powershell
ollama run qwen2.5:7b
```

### 3. Configuration
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Leave `LOCAL_ONLY=true` to maintain the strict local security boundary.

### 4. Diagnostics
Run the diagnostic script to ensure all components are operational:
```powershell
python -m scripts.diagnostics
```

### 5. Running the Assistant (Text Interaction)
Launch the interactive text session:
```powershell
python -m app.main
```
Type your query. Press Ctrl+C while the model is typing to cancel the generation.

### 6. Voice Setup
Voice is supported. `faster-whisper` requires `STT_MODEL` (default: tiny.en).
`pyttsx3` uses native Windows voices and requires no extra downloads.
*(Note: Voice command interface integration is a work in progress for P2, but the backend `app/voice` modules are ready and testable).*
