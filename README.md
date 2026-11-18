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

## Demo and phone/tablet access

Run the seeded demo on an isolated database with:

```powershell
& ".\.venv\Scripts\python.exe" web_app.py --demo
```

The demo binds to the local network on port `5001` and uses
`instance/scapp-demo.sqlite3`, leaving the normal course database untouched.
On this computer, open <http://127.0.0.1:5001>. On another device connected to
the same Wi-Fi, find this computer's IPv4 address with `ipconfig` and open
`http://<computer-ip>:5001` (for example, `http://192.168.1.20:5001`). If
Windows asks whether Python can accept connections on a private network, allow
it for the private network. Stop the server with `Ctrl+C`.

For mobile layout work with the real database, use
`python web_app.py --host 0.0.0.0 --port 5000` and visit the same computer IP
on port `5000`. The app has no login yet, so use the seeded demo for shared
device testing. The view switcher is a test identity selector, not account
authentication or a security boundary.

## Data storage

The web app stores data in SQLite at `instance/scapp.sqlite3`. The database is
created automatically when the app starts. Sailors, instructor profiles,
course assignments, course instances, session dates and plans, planned session
criteria, enrolments, checklist progress, and dated notes persist when the app
is stopped and started again. Certificate requests and issued qualifications
are also recorded there. Back up this database file to preserve the data.

The dashboard lists created courses, not every syllabus stage. Office creates a
course in the setup dialog by choosing a name, syllabus stage, instructors,
pupils, session count, and optional dates. Multiple courses can use the same
stage. A stage with no created courses does not appear on the dashboard. The
selected stage initializes pupil checklists and supplies the criteria available
to plan each session. Assigned instructors can open the Sessions page to select
planned criteria, set dates, and write a plan for each collapsible session. They
can mark a session as run, then fill in feedback and ways to improve. After
confirming that every pupil achieved the planned criteria, marking the session
complete updates those criteria for all pupils in the course. On the course
page, instructors can also update individual criteria or use the course-wide
bulk actions. Office can review all session plans, browse pupils and their
qualifications, and issue certificates from the waiting list. Completing all
criteria in a syllabus stage adds a pending certificate; issuing it credits the
stage on the pupil profile. Instructor notes include their author and course,
and office/instructor profiles show notes from across courses. The pupil view
has a My awards area that collects issued awards and certificates waiting for
the office to issue. Office can also record named accolades on a pupil profile.

Existing databases are migrated on startup: enrolled stage-based records are
preserved as courses, while un-enrolled stage placeholders are removed. Progress
is stored by criterion text. Each course now keeps the syllabus structure it
was created from, so future edits to `syllabus.json` do not rewrite that
course's checklist. Existing databases receive a snapshot from the current
syllabus on migration where the stage is still available.

## Current scope

Office can archive any course, including an incomplete course or a resit, and
restore it later from Archived courses. Each course keeps the syllabus version
it started with, so later syllabus edits do not change its criteria. When a
pupil completes a stage, the assigned instructor adds a required award comment
using guided prompts or a personal message before the office can issue the
certificate. The pupil and office can see the saved comment. Stage awards also
keep a snapshot of assigned instructor names so pupils can see who taught them.

This is a local app with no login or authenticated user accounts. The view
switcher is a testing tool: office can assign instructor profiles to courses,
instructors only see and update assigned courses, and pupil profiles only see
their own enrolled course progress. Because there is no authentication yet,
these views do not provide a security boundary. Sailors can be enrolled in
multiple courses. Notes are attached to the pupil profile and record their
author and course when added through a course; instructors can see notes from
other instructors on the profile.
