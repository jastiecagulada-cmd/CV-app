# LabCV (sorted)

**What is this (r/ELI5):** A tiny local app where a camera looks at lab items, the computer spots what they are, and the app records who borrowed/returned them in a notebook file.

## How to run (beginner steps)
1. Create a virtual environment (r/ELI5: a clean sandbox for Python):
   - Windows: `py -m venv .venv && .venv\Scripts\activate`
   - macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`
2. Install packages (r/ELI5: buy everything on the shopping list):
   ```bash
   pip install -r requirements.txt
   ```
3. Start the app (r/ELI5: turn on the tiny traffic cop and open the page):
   ```bash
   python app.py
   ```
   Then open http://127.0.0.1:5000 in your browser.

## Project layout
- `app.py` — Flask server (r/ELI5: traffic cop for requests) **kept unchanged** so nothing breaks.
- `templates/` — HTML pages (r/ELI5: what you see).
- `static/` — CSS/JS (r/ELI5: looks + small messengers).
- `database.db` — SQLite file (r/ELI5: one-file notebook of records).
- `models/` — YOLO weights (r/ELI5: the brain file), if any.
- `dataset/` — training images/labels (r/ELI5: practice exams).
- `experiments/runs/` — YOLO outputs/logs (r/ELI5: lab notes).
- `requirements.txt` — packages list (r/ELI5: shopping list).
- `.gitignore` — Git ignore rules (r/ELI5: don't pack these).

## Notes
- We intentionally **did not move or edit `app.py`** to avoid breaking imports or paths.
- If you later split code (optional), create `src/` with helpers (`detection.py`, `db.py`, `crack.py`) and update imports carefully.
