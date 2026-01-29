# CODEBASE.md - JLSatiro Clipper AI

> This file provides an overview of the codebase and its dependencies.

---

## 📁 System Architecture

### Core Components
- `app.py`: Main application entry point (Streamlit).
- `modules/`: Contains core logic for video processing, transcription, and uploading.
  - `modules/youtube_uploader.py`: Handles interaction with the YouTube API.
  - `modules/cropper.py`: Video cropping logic.
  - `modules/renderer.py`: Video rendering and processing.

### Documentation & Config
- `.agent/`: Antigravity Kit configuration, agents, and workflows.
- `GEMINI.md`: AI behavior rules.
- `ARCHITECTURE.md`: Technical architecture overview (located in `.agent/ARCHITECTURE.md`).

---

## 🔗 File Dependencies

- `app.py` → `modules/`
- `modules/youtube_uploader.py` → `credentials.json`, `token.pickle`
- `launcher.py` → `app.py`
