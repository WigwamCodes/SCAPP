# Sailing Progress Tracker

A local web app for instructors to track sailors against the sailing syllabus,
record checklist progress, and write dated notes. Course stages and criteria are
loaded from `syllabus.json`.

## Run locally

From the project directory, create a virtual environment if needed, install the
dependencies, and start the app:

```powershell
if (-not (Test-Path ".venv")) { python -m venv .venv }
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" web_app.py
```

Open <http://127.0.0.1:5000> in a browser. Use `Ctrl+C` in the terminal to stop
the app. The original console demonstration can still be run with
`python "SC APP.py"`.

## Data storage

The web app stores data in SQLite at `instance/scapp.sqlite3`. The database is
created automatically when the app starts. Sailors, course enrolments,
checklist progress, and dated notes persist when the app is stopped and started
again. Back up this database file to preserve the data.

The syllabus is read from `syllabus.json` when the app starts. The app registers
the listed course stages in the database, and initializes checklist progress
when a sailor is enrolled in a stage. Existing progress is stored by criterion
text; changing syllabus criteria does not migrate or reconcile existing
checklists automatically.

## Current scope

This is a local, single-user app with no login or instructor accounts. Sailors
can be enrolled in multiple stages, and notes are attached to a sailor rather
than to a specific stage, so the same notes appear wherever that sailor is
viewed.
