# Sailing Progress Tracker

A local web app for instructors to track sailors against the sailing syllabus,
record checklist progress, and write dated notes. Course stages and criteria
are loaded from `syllabus.json`.

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
created automatically when the app starts. Sailors, course instances,
enrolments, checklist progress, and dated notes persist when the app is stopped
and started again. Back up this database file to preserve the data.

The dashboard lists created courses, not every syllabus stage. Create a course
by giving it a distinct name and choosing a stage from `syllabus.json`; multiple
courses can use the same stage. A stage with no created courses does not appear
on the dashboard. Add sailors to a course to initialize their checklist for
that course. On a course page, instructors can view each sailor's progress,
update individual criteria, set one criterion for the whole course, or complete
or clear a category for one sailor or all sailors in that course.

Existing databases are migrated on startup: enrolled stage-based records are
preserved as courses, while un-enrolled stage placeholders are removed. Progress
is stored by criterion text; changing syllabus criteria does not migrate or
reconcile existing checklists automatically. If a course's stage is removed
from `syllabus.json`, the saved course remains visible and its saved checklist
can still be viewed, but updates are disabled until that stage is restored.

## Current scope

This is a local, single-user app with no login or instructor accounts. Sailors
can be enrolled in multiple courses, and notes are attached to a sailor rather
than to a specific course, so the same notes appear wherever that sailor is
viewed.
