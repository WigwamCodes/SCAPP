# Sailing Progress Tracker roadmap

_Working draft — priorities can change as the app is used. No dates or commitments yet._

## Product direction

Build a practical tool for sailing schools to manage courses and help instructors track pupils against a shared syllabus. The app is local and single-user today. Its office, instructor, and pupil views are testing profiles; real accounts and access control need to come before shared use.

## Built so far

- [x] Create named courses from stages in `syllabus.json`.
- [x] Enrol sailors in one or more courses and save checklist progress and dated notes in SQLite.
- [x] Show progress in a skills-by-pupils grid with bulk actions and collapsible syllabus categories.
- [x] Save individual checklist changes without reloading the page.
- [x] Delete courses or sailors with confirmation.
- [x] Assign named instructor profiles to courses; show instructors and pupils in the view switcher.
- [x] Filter instructor views to assigned courses and pupil views to their own enrolled progress.
- [x] Create courses with assigned instructors, enrolled pupils, a syllabus stage, session slots, and optional session dates.
- [x] Give assigned instructors a Sessions page to select syllabus criteria, set dates, and write a plan per session.
- [x] Make session entries collapsible; track planned, run, and complete states with feedback and improvement notes.
- [x] On completion, update every enrolled pupil's progress for the planned criteria after instructor confirmation.
- [x] Let the office view all session plans and feedback.
- [x] Add an office pupil directory with issued qualifications and full pupil profiles.
- [x] Put pupils with a fully completed syllabus stage into a certificate queue; issuing the certificate credits the stage on their profile.
- [x] Show cross-course instructor notes with their author on the pupil profile.
- [x] Give pupils a My awards area for issued awards and certificates waiting to be issued.
- [x] Let the office add named accolades to a pupil's awards collection.
- [x] Let office archive any course, including incomplete/resit courses, and restore them later.
- [x] Show course instructors on pupil awards using a saved instructor snapshot.
- [x] Save a course-local syllabus snapshot so course structure persists through syllabus edits and resits.
- [x] Require an instructor award comment before issuing a completed stage certificate; support guided and personal messages.
- [x] Add a seeded demo database and launch option for isolated feature walkthroughs.
- [x] Add initial small-screen layout refinements and LAN access instructions.

## Next up

- [ ] Walk through course setup and session planning with a real teaching example; refine the flow.
- [ ] Let the office remove an instructor from a course and review the course's assigned instructors.
- [ ] Finish mobile usability work, including a better touch interaction for the wide progress grid.
- [ ] Try the seeded demo from a phone/tablet and refine any layout issues found.

## Possible next feature paths

Choose one path after trying the current workflow:

### Running lessons

- Add registers for attendance.
- Assign instructors and boats to individual sessions, including safety boats.
- Add risk assessments and reusable session plans.
- A library of drills and coaching ideas.

### Pupil records

- Pupil profile with previous experience and course history.
- Notes scoped to sessions as well as general pupil notes.
- Pupil-facing progress summaries that can be shared safely.
- Decide what personal details are necessary before collecting more pupil data.

### Reports and outcomes

- Printable course and pupil progress reports.
- Generate or print the certificates in the issue queue.
- Export and backup/restore for course and pupil records.

### Office and multi-user operation

- Real instructor and office accounts, sign-in, and permissions.
- Decide on authenticated, protected LAN/shared hosting before using real pupil data across devices.
- Multiple organizations or clubs with isolated records.
- Shared hosting, data ownership, and recovery plan before deployment.
- Define exactly what office staff, instructors, and pupils can view and change.

## Decisions to make

- [ ] Which records can instructors edit, archive, or delete: courses, enrolments, progress, and notes?
- [ ] Should instructors be assigned to a whole course or to individual sessions?
- [ ] What is the minimum useful pupil profile, and who may see it?
- [ ] How should the progress grid work for large classes, long skill descriptions, and phones?
- [ ] What needs to be included in exports, backups, and restore?
- [ ] What should office staff be able to do that instructors cannot?
- [ ] Is RYA data import available and useful for this workflow?

## Cleanup and foundations

- [ ] Retire the legacy console demo (`SC APP.py`) and old in-memory tracking model.
- [ ] Keep syllabus loading separate from the legacy model as that model is retired.
- [ ] Revisit stable skill IDs and syllabus-change migration when syllabus edits become common.

## Ideas to keep

- Sailkor search: preview a sailor's previous experience and notes on their profile.
- Add ideas that come up while teaching with the app; prioritize them after workflow trials.
