# Sailing Progress Tracker roadmap

_Working draft — add, reorder, rename, or remove items as the product takes shape. No dates or commitments yet._

## Product direction

Build a practical tool for sailing instructors to track pupils' progress against a shared syllabus. The browser app works locally today; the longer-term goal is to support multiple instructors and an office/team.

## Next up

- [ ] Redesign course progress as a grid of skills and pupils, with a checkbox at each intersection.
- [ ] Let an instructor mark one skill complete for everyone, or all skills complete for one pupil. Make the scope of each bulk action obvious.
- [ ] Be able to delete sailors and courses
- [ ] Keep syllabus categories clear and make the grid usable on smaller screens.
- [ ] Try the proposed workflow and adjust it before adding more features.

## Later

- [ ] Support multiple organizations/teams, with individual instructor accounts and office/admin roles.
- [ ] Plan shared hosting, permissions, and account management before implementing multi-user access.
- [ ] Add notes to the course or session(when thats added), or click on a pupil and add notes to them
- [ ] Add certificates. Keep the existing database structure available for this future feature.
- [ ] Have a way to change view between office, instructor, student and what they should be able to see

## Cleanup and foundations

- [ ] Retire the legacy console demo (`SC APP.py`) and old in-memory tracking model.
- [ ] Keep the syllabus as the central source of skills to import; separate syllabus loading from the legacy model when cleaning it up.
- [ ] Revisit stable skill identifiers and syllabus-change migration when syllabus edits or wording changes become a priority.

## Decisions to make

- [ ] Which records should instructors be able to edit, archive, or delete? Consider courses, pupil enrolments, and notes.
- [ ] What export, backup, or restore options are needed?
- [ ] How should the progress grid behave on phones and with large groups or long skill descriptions?
- [ ] What should office/admin users be allowed to do that instructors cannot?

## Ideas to add

- [ ] Session planning area + risk assessments
- [ ] Drill Ideas for coaching
- [ ] Sailkor search - preview your sailors previous experience and notes on their profile

### Teaching and course workflow

- _What else would make running a course or tracking a lesson easier?_

### Pupil records and communication

- _What pupil details, history, or communication would be useful to keep?_

### Reports and certificates

- _What progress summaries, printouts, or certificate features would you want?_
- [ ] Course reports and student reports should be available showing 

### Scheduling and administration

- _Any needs around dates, attendance, instructors, boats, or office tasks?_
- [ ] Course dates should be added
- [ ] adding registers for each session
- [ ]boat assignment so instructors know what boats they are assigned (safety boats and club boats - especially if parents book them)

### Imports, exports, and integrations

- [ ] Can we have RYA data pulled in

### Other ideas

- _Add anything that doesn't fit above._