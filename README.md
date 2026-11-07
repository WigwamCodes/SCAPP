# Sailing Progress Tracker

A small, local web app for instructors to track sailors against the syllabus and
write dated notes.

## Run locally

From the project directory, create the virtual environment if needed, install
Flask, then start the app:

```powershell
if (-not (Test-Path ".venv")) { python -m venv .venv }
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" web_app.py
```

Open <http://127.0.0.1:5000> in a browser. Use `Ctrl+C` in the terminal to stop
the app. The original console demonstration can still be run with
`python "SC APP.py"`.

## Current limitation

Sailors, checklist changes, and notes are held in memory while the app runs.
They are lost when the process stops; persistent storage is a planned next step.
