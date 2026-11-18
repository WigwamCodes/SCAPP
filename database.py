import json
import sqlite3
from pathlib import Path


def get_connection(database_path):
    """Open a connection to the SQLite database."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(database_path, syllabus):
    """Create the database tables and migrate existing stage-based courses."""

    database_path = Path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = get_connection(database_path)

    try:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS sailors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                name_key TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                stage TEXT NOT NULL,
                archived_at TEXT NOT NULL DEFAULT '',
                syllabus_snapshot TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS instructors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                name_key TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS course_instructors (
                course_id INTEGER NOT NULL,
                instructor_id INTEGER NOT NULL,
                UNIQUE (course_id, instructor_id),
                FOREIGN KEY (course_id) REFERENCES courses(id),
                FOREIGN KEY (instructor_id) REFERENCES instructors(id)
            );

            CREATE TABLE IF NOT EXISTS course_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                session_number INTEGER NOT NULL,
                session_date TEXT NOT NULL DEFAULT '',
                plan TEXT NOT NULL DEFAULT '',
                is_done INTEGER NOT NULL DEFAULT 0 CHECK (is_done IN (0, 1)),
                is_complete INTEGER NOT NULL DEFAULT 0 CHECK (is_complete IN (0, 1)),
                feedback TEXT NOT NULL DEFAULT '',
                improvements TEXT NOT NULL DEFAULT '',
                UNIQUE (course_id, session_number),
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS session_criteria (
                session_id INTEGER NOT NULL,
                criterion TEXT NOT NULL,
                PRIMARY KEY (session_id, criterion),
                FOREIGN KEY (session_id) REFERENCES course_sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS enrolments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sailor_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                UNIQUE (sailor_id, course_id),
                FOREIGN KEY (sailor_id) REFERENCES sailors(id),
                FOREIGN KEY (course_id) REFERENCES courses(id)
            );

            CREATE TABLE IF NOT EXISTS progress (
                enrolment_id INTEGER NOT NULL,
                criterion TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0
                    CHECK (completed IN (0, 1)),
                PRIMARY KEY (enrolment_id, criterion),
                FOREIGN KEY (enrolment_id)
                    REFERENCES enrolments(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sailor_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                course_id INTEGER,
                instructor_id INTEGER,
                FOREIGN KEY (sailor_id) REFERENCES sailors(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES courses(id),
                FOREIGN KEY (instructor_id) REFERENCES instructors(id)
            );

            CREATE TABLE IF NOT EXISTS certificates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sailor_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                issued_on TEXT NOT NULL DEFAULT '',
                stage TEXT NOT NULL DEFAULT '',
                course_id INTEGER,
                status TEXT NOT NULL DEFAULT 'issued'
                    CHECK (status IN ('pending', 'issued', 'cancelled')),
                requested_at TEXT NOT NULL DEFAULT '',
                issued_by TEXT NOT NULL DEFAULT '',
                award_comment TEXT NOT NULL DEFAULT '',
                feedback_mode TEXT NOT NULL DEFAULT '',
                best_element TEXT NOT NULL DEFAULT '',
                good_attribute TEXT NOT NULL DEFAULT '',
                top_tip TEXT NOT NULL DEFAULT '',
                practice TEXT NOT NULL DEFAULT '',
                personal_message TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (sailor_id) REFERENCES sailors(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES courses(id)
            );
        """)

        course_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(courses)")
        }
        if "stage" not in course_columns:
            connection.execute("ALTER TABLE courses ADD COLUMN stage TEXT")
            connection.execute("UPDATE courses SET stage = name")
            connection.execute(
                """
                DELETE FROM courses
                WHERE id NOT IN (SELECT course_id FROM enrolments)
                """
            )
        if "archived_at" not in course_columns:
            connection.execute(
                "ALTER TABLE courses ADD COLUMN archived_at TEXT NOT NULL DEFAULT ''"
            )
        if "syllabus_snapshot" not in course_columns:
            connection.execute("ALTER TABLE courses ADD COLUMN syllabus_snapshot TEXT NOT NULL DEFAULT ''")
        for saved_course in connection.execute(
            "SELECT id, stage FROM courses WHERE syllabus_snapshot = ''"
        ).fetchall():
            if saved_course["stage"] in syllabus:
                connection.execute(
                    "UPDATE courses SET syllabus_snapshot = ? WHERE id = ?",
                    (json.dumps(syllabus[saved_course["stage"]]), saved_course["id"]),
                )

        session_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(course_sessions)")
        }
        for column_name, column_definition in (
            ("is_done", "INTEGER NOT NULL DEFAULT 0 CHECK (is_done IN (0, 1))"),
            ("is_complete", "INTEGER NOT NULL DEFAULT 0 CHECK (is_complete IN (0, 1))"),
            ("feedback", "TEXT NOT NULL DEFAULT ''"),
            ("improvements", "TEXT NOT NULL DEFAULT ''"),
        ):
            if column_name not in session_columns:
                connection.execute(
                    f"ALTER TABLE course_sessions ADD COLUMN {column_name} {column_definition}"
                )

        note_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(notes)")
        }
        for column_name, column_definition in (
            ("course_id", "INTEGER REFERENCES courses(id)"),
            ("instructor_id", "INTEGER REFERENCES instructors(id)"),
        ):
            if column_name not in note_columns:
                connection.execute(
                    f"ALTER TABLE notes ADD COLUMN {column_name} {column_definition}"
                )

        certificate_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(certificates)")
        }
        for column_name, column_definition in (
            ("stage", "TEXT NOT NULL DEFAULT ''"),
            ("course_id", "INTEGER REFERENCES courses(id)"),
            ("status", "TEXT NOT NULL DEFAULT 'issued'"),
            ("requested_at", "TEXT NOT NULL DEFAULT ''"),
            ("issued_by", "TEXT NOT NULL DEFAULT ''"),
            ("instructors", "TEXT NOT NULL DEFAULT '[]'"),
            ("award_comment", "TEXT NOT NULL DEFAULT ''"),
            ("feedback_mode", "TEXT NOT NULL DEFAULT ''"),
            ("best_element", "TEXT NOT NULL DEFAULT ''"),
            ("good_attribute", "TEXT NOT NULL DEFAULT ''"),
            ("top_tip", "TEXT NOT NULL DEFAULT ''"),
            ("practice", "TEXT NOT NULL DEFAULT ''"),
            ("personal_message", "TEXT NOT NULL DEFAULT ''"),
        ):
            if column_name not in certificate_columns:
                connection.execute(
                    f"ALTER TABLE certificates ADD COLUMN {column_name} {column_definition}"
                )
        for certificate in connection.execute(
            "SELECT id, course_id FROM certificates WHERE instructors = '[]' AND course_id IS NOT NULL"
        ).fetchall():
            instructor_names = [row["name"] for row in connection.execute(
                """SELECT instructors.name FROM instructors JOIN course_instructors
                   ON course_instructors.instructor_id = instructors.id
                   WHERE course_instructors.course_id = ? ORDER BY instructors.name COLLATE NOCASE""",
                (certificate["course_id"],),
            ).fetchall()]
            connection.execute("UPDATE certificates SET instructors = ? WHERE id = ?",
                               (json.dumps(instructor_names), certificate["id"]))
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS certificates_one_stage_per_sailor "
            "ON certificates (sailor_id, stage) WHERE stage <> ''"
        )

        connection.commit()

    finally:
        connection.close()


def create_course(database_path, name, stage):
    """Create a named course instance based on a syllabus stage."""
    connection = get_connection(database_path)

    try:
        result = connection.execute(
            "INSERT OR IGNORE INTO courses (name, stage) VALUES (?, ?)",
            (name, stage),
        )
        connection.commit()
        if result.rowcount == 0:
            return None
        return result.lastrowid

    finally:
        connection.close()


def create_course_setup(
    database_path, name, stage, criteria, instructor_names, pupil_ids,
    new_pupil_names, session_dates, syllabus_snapshot=None,
):
    """Create a course, enroll pupils, assign instructors, and create sessions atomically."""
    connection = get_connection(database_path)
    try:
        result = connection.execute(
            "INSERT OR IGNORE INTO courses (name, stage, syllabus_snapshot) VALUES (?, ?, ?)",
            (name, stage, json.dumps(syllabus_snapshot) if syllabus_snapshot else ""),
        )
        if result.rowcount == 0:
            connection.rollback()
            return None
        course_id = result.lastrowid

        for instructor_name in instructor_names:
            name_key = instructor_name.casefold()
            connection.execute(
                "INSERT OR IGNORE INTO instructors (name, name_key) VALUES (?, ?)",
                (instructor_name, name_key),
            )
            instructor = connection.execute(
                "SELECT id FROM instructors WHERE name_key = ?", (name_key,)
            ).fetchone()
            connection.execute(
                "INSERT OR IGNORE INTO course_instructors (course_id, instructor_id) VALUES (?, ?)",
                (course_id, instructor["id"]),
            )

        valid_pupils = {
            row["id"] for row in connection.execute("SELECT id FROM sailors")
        }
        if not set(pupil_ids).issubset(valid_pupils):
            raise ValueError("Choose existing pupils from the list.")

        selected_pupils = set(pupil_ids)
        for pupil_name in new_pupil_names:
            name_key = pupil_name.casefold()
            connection.execute(
                "INSERT OR IGNORE INTO sailors (name, name_key) VALUES (?, ?)",
                (pupil_name, name_key),
            )
            pupil = connection.execute(
                "SELECT id FROM sailors WHERE name_key = ?", (name_key,)
            ).fetchone()
            selected_pupils.add(pupil["id"])

        for pupil_id in selected_pupils:
            connection.execute(
                "INSERT INTO enrolments (sailor_id, course_id) VALUES (?, ?)",
                (pupil_id, course_id),
            )
            enrolment = connection.execute(
                "SELECT id FROM enrolments WHERE sailor_id = ? AND course_id = ?",
                (pupil_id, course_id),
            ).fetchone()
            for criterion in criteria:
                connection.execute(
                    "INSERT OR IGNORE INTO progress (enrolment_id, criterion, completed) VALUES (?, ?, 0)",
                    (enrolment["id"], criterion),
                )

        for session_number, session_date in enumerate(session_dates, start=1):
            connection.execute(
                "INSERT INTO course_sessions (course_id, session_number, session_date) VALUES (?, ?, ?)",
                (course_id, session_number, session_date),
            )

        connection.commit()
        return course_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_sessions_for_course(database_path, course_id):
    connection = get_connection(database_path)
    try:
        sessions = connection.execute(
            "SELECT id, session_number, session_date, plan, is_done, is_complete, feedback, improvements "
            "FROM course_sessions "
            "WHERE course_id = ? ORDER BY session_number",
            (course_id,),
        ).fetchall()
        result = []
        for session_row in sessions:
            item = dict(session_row)
            item["criteria"] = [
                row["criterion"]
                for row in connection.execute(
                    "SELECT criterion FROM session_criteria WHERE session_id = ? ORDER BY criterion",
                    (item["id"],),
                ).fetchall()
            ]
            result.append(item)
        return result
    finally:
        connection.close()


def add_course_sessions(database_path, course_id, count):
    connection = get_connection(database_path)
    try:
        current = connection.execute(
            "SELECT COALESCE(MAX(session_number), 0) AS last_number FROM course_sessions WHERE course_id = ?",
            (course_id,),
        ).fetchone()["last_number"]
        for session_number in range(current + 1, current + count + 1):
            connection.execute(
                "INSERT INTO course_sessions (course_id, session_number) VALUES (?, ?)",
                (course_id, session_number),
            )
        connection.commit()
    finally:
        connection.close()


def save_course_session(
    database_path, course_id, session_id, session_date, plan, criteria,
    feedback, improvements, is_done,
):
    connection = get_connection(database_path)
    try:
        result = connection.execute(
            "UPDATE course_sessions SET session_date = ?, plan = ?, feedback = ?, "
            "improvements = ?, is_done = ? WHERE id = ? AND course_id = ?",
            (session_date, plan, feedback, improvements, int(is_done), session_id, course_id),
        )
        if result.rowcount == 0:
            connection.rollback()
            return False
        connection.execute("DELETE FROM session_criteria WHERE session_id = ?", (session_id,))
        connection.executemany(
            "INSERT INTO session_criteria (session_id, criterion) VALUES (?, ?)",
            [(session_id, criterion) for criterion in criteria],
        )
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def complete_course_session(
    database_path, course_id, session_id, session_date, plan, feedback,
    improvements, criteria,
):
    """Complete a run session and mark its planned criteria for every pupil atomically."""
    if not criteria:
        return False
    connection = get_connection(database_path)
    try:
        result = connection.execute(
            "UPDATE course_sessions SET session_date = ?, plan = ?, feedback = ?, "
            "improvements = ?, is_done = 1, is_complete = 1 "
            "WHERE id = ? AND course_id = ?",
            (session_date, plan, feedback, improvements, session_id, course_id),
        )
        if result.rowcount == 0:
            connection.rollback()
            return False

        for criterion in criteria:
            connection.execute(
                """INSERT OR IGNORE INTO progress (enrolment_id, criterion, completed)
                   SELECT id, ?, 0 FROM enrolments WHERE course_id = ?""",
                (criterion, course_id),
            )
        placeholders = ", ".join("?" for _ in criteria)
        connection.execute(
            f"""UPDATE progress SET completed = 1
                WHERE criterion IN ({placeholders})
                  AND enrolment_id IN (SELECT id FROM enrolments WHERE course_id = ?)""",
            [*criteria, course_id],
        )
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_courses(database_path, include_archived=False):
    """Retrieve course instances with overall checklist completion."""
    connection = get_connection(database_path)

    try:
        archive_filter = "" if include_archived else "WHERE courses.archived_at = ''"
        rows = connection.execute(
            f"""
            SELECT courses.id, courses.name, courses.stage, courses.archived_at,
                   courses.syllabus_snapshot,
                   COUNT(DISTINCT enrolments.sailor_id) AS sailor_count,
                   COUNT(progress.criterion) AS total_criteria,
                   COALESCE(SUM(progress.completed), 0) AS completed_criteria
            FROM courses
            LEFT JOIN enrolments ON enrolments.course_id = courses.id
            LEFT JOIN progress ON progress.enrolment_id = enrolments.id
            {archive_filter}
            GROUP BY courses.id
            ORDER BY courses.stage COLLATE NOCASE, courses.name COLLATE NOCASE
            """
        ).fetchall()
        return [dict(row) for row in rows]

    finally:
        connection.close()


def get_course_by_id(database_path, course_id):
    """Retrieve one course instance."""
    connection = get_connection(database_path)

    try:
        row = connection.execute(
            "SELECT id, name, stage, archived_at, syllabus_snapshot FROM courses WHERE id = ? AND archived_at = ''", (course_id,)
        ).fetchone()
        return dict(row) if row is not None else None

    finally:
        connection.close()


def set_course_archived(database_path, course_id, archived_at=""):
    connection = get_connection(database_path)
    try:
        result = connection.execute(
            "UPDATE courses SET archived_at = ? WHERE id = ?",
            (archived_at, course_id),
        )
        connection.commit()
        return result.rowcount > 0
    finally:
        connection.close()


def get_instructors(database_path):
    connection = get_connection(database_path)
    try:
        rows = connection.execute(
            "SELECT id, name FROM instructors ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_sailors(database_path):
    connection = get_connection(database_path)
    try:
        rows = connection.execute(
            "SELECT id, name FROM sailors ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_sailor_profile(database_path, sailor_id):
    connection = get_connection(database_path)
    try:
        sailor_row = connection.execute(
            "SELECT id, name FROM sailors WHERE id = ?", (sailor_id,)
        ).fetchone()
        if sailor_row is None:
            return None
        sailor = dict(sailor_row)
        sailor["qualifications"] = [
            dict(row)
            for row in connection.execute(
                """SELECT certificates.name, certificates.stage, certificates.issued_on,
                          certificates.issued_by, certificates.instructors,
                          certificates.award_comment, certificates.personal_message,
                          courses.name AS course_name
                   FROM certificates
                   LEFT JOIN courses ON courses.id = certificates.course_id
                   WHERE certificates.sailor_id = ? AND certificates.status = 'issued'
                   ORDER BY certificates.issued_on DESC, certificates.id DESC""",
                (sailor_id,),
            ).fetchall()
        ]
        for qualification in sailor["qualifications"]:
            try:
                qualification["instructors"] = json.loads(qualification["instructors"] or "[]")
            except (TypeError, json.JSONDecodeError):
                qualification["instructors"] = []
        sailor["pending_certificates"] = [
            dict(row)
            for row in connection.execute(
                """SELECT certificates.stage, certificates.requested_at,
                          certificates.award_comment, certificates.personal_message,
                          certificates.instructors,
                          courses.name AS course_name FROM certificates
                   LEFT JOIN courses ON courses.id = certificates.course_id
                   WHERE certificates.sailor_id = ? AND certificates.status = 'pending'
                   ORDER BY certificates.requested_at DESC""",
                (sailor_id,),
            ).fetchall()
        ]
        for pending in sailor["pending_certificates"]:
            try:
                pending["instructors"] = json.loads(pending["instructors"] or "[]")
            except (TypeError, json.JSONDecodeError):
                pending["instructors"] = []
        sailor["notes"] = [
            dict(row)
            for row in connection.execute(
                """SELECT notes.text, notes.created_at,
                          COALESCE(instructors.name, 'Unattributed') AS author,
                          courses.name AS course_name
                   FROM notes
                   LEFT JOIN instructors ON instructors.id = notes.instructor_id
                   LEFT JOIN courses ON courses.id = notes.course_id
                   WHERE notes.sailor_id = ? ORDER BY notes.id DESC""",
                (sailor_id,),
            ).fetchall()
        ]
        sailor["courses"] = [
            dict(row)
            for row in connection.execute(
                """SELECT courses.id, courses.name, courses.stage FROM courses
                   JOIN enrolments ON enrolments.course_id = courses.id
                   WHERE enrolments.sailor_id = ?
                   ORDER BY courses.name COLLATE NOCASE""",
                (sailor_id,),
            ).fetchall()
        ]
        return sailor
    finally:
        connection.close()


def instructor_can_view_sailor(database_path, instructor_id, sailor_id):
    connection = get_connection(database_path)
    try:
        return connection.execute(
            """SELECT 1 FROM course_instructors
               JOIN enrolments ON enrolments.course_id = course_instructors.course_id
               WHERE course_instructors.instructor_id = ? AND enrolments.sailor_id = ?""",
            (instructor_id, sailor_id),
        ).fetchone() is not None
    finally:
        connection.close()


def get_office_sessions(database_path):
    connection = get_connection(database_path)
    try:
        rows = connection.execute(
            """SELECT course_sessions.id, course_sessions.course_id,
                      course_sessions.session_number, course_sessions.session_date,
                      course_sessions.plan, course_sessions.is_done,
                      course_sessions.is_complete, course_sessions.feedback,
                      course_sessions.improvements, courses.name AS course_name,
                      courses.stage
               FROM course_sessions JOIN courses ON courses.id = course_sessions.course_id
               ORDER BY CASE WHEN course_sessions.session_date = '' THEN 1 ELSE 0 END,
                        course_sessions.session_date, courses.name COLLATE NOCASE,
                        course_sessions.session_number"""
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["criteria"] = [
                criterion["criterion"]
                for criterion in connection.execute(
                    "SELECT criterion FROM session_criteria WHERE session_id = ? ORDER BY criterion",
                    (item["id"],),
                ).fetchall()
            ]
            item["instructors"] = [
                instructor["name"]
                for instructor in connection.execute(
                    """SELECT instructors.name FROM instructors
                       JOIN course_instructors ON course_instructors.instructor_id = instructors.id
                       WHERE course_instructors.course_id = ?
                       ORDER BY instructors.name COLLATE NOCASE""",
                    (item["course_id"],),
                ).fetchall()
            ]
            result.append(item)
        return result
    finally:
        connection.close()


def get_pending_certificates(database_path):
    connection = get_connection(database_path)
    try:
        rows = connection.execute(
            """SELECT certificates.id, certificates.sailor_id, certificates.stage,
                      certificates.requested_at, certificates.award_comment,
                      certificates.personal_message,
                      certificates.instructors, sailors.name AS sailor_name,
                      courses.name AS course_name
               FROM certificates JOIN sailors ON sailors.id = certificates.sailor_id
               LEFT JOIN courses ON courses.id = certificates.course_id
               WHERE certificates.status = 'pending'
               ORDER BY certificates.requested_at, sailors.name COLLATE NOCASE"""
        ).fetchall()
        result = [dict(row) for row in rows]
        for item in result:
            try:
                item["instructors"] = json.loads(item["instructors"] or "[]")
            except (TypeError, json.JSONDecodeError):
                item["instructors"] = []
        return result
    finally:
        connection.close()


def issue_certificate(database_path, certificate_id, issued_on):
    connection = get_connection(database_path)
    try:
        result = connection.execute(
            """UPDATE certificates SET status = 'issued', issued_on = ?, issued_by = 'Office'
               WHERE id = ? AND status = 'pending'
                 AND (stage = '' OR award_comment <> '')""",
            (issued_on, certificate_id),
        )
        connection.commit()
        return result.rowcount > 0
    finally:
        connection.close()


def get_pending_stage_certificates_for_course(database_path, course_id):
    connection = get_connection(database_path)
    try:
        return [dict(row) for row in connection.execute(
            """SELECT certificates.id, certificates.sailor_id, certificates.stage,
                      certificates.award_comment, certificates.feedback_mode,
                      certificates.best_element, certificates.good_attribute,
                      certificates.top_tip, certificates.practice,
                      certificates.personal_message,
                      sailors.name AS sailor_name
               FROM certificates JOIN sailors ON sailors.id = certificates.sailor_id
               WHERE certificates.course_id = ? AND certificates.status = 'pending'
                     AND certificates.stage <> ''
               ORDER BY sailors.name COLLATE NOCASE""",
            (course_id,),
        ).fetchall()]
    finally:
        connection.close()


def save_certificate_feedback(database_path, course_id, certificate_id, mode,
                              comment, best_element="", good_attribute="",
                              top_tip="", practice="", personal_message=""):
    connection = get_connection(database_path)
    try:
        result = connection.execute(
            """UPDATE certificates SET feedback_mode = ?, award_comment = ?,
                      best_element = ?, good_attribute = ?, top_tip = ?, practice = ?,
                      personal_message = ?
               WHERE id = ? AND course_id = ? AND status = 'pending' AND stage <> ''""",
            (mode, comment, best_element, good_attribute, top_tip, practice, personal_message,
             certificate_id, course_id),
        )
        connection.commit()
        return result.rowcount > 0
    finally:
        connection.close()


def add_sailor_award(database_path, sailor_id, name, issued_on):
    connection = get_connection(database_path)
    try:
        result = connection.execute(
            """INSERT INTO certificates
               (sailor_id, name, issued_on, stage, status, issued_by)
               SELECT id, ?, ?, '', 'issued', 'Office' FROM sailors WHERE id = ?""",
            (name, issued_on, sailor_id),
        )
        connection.commit()
        return result.rowcount > 0
    finally:
        connection.close()


def sync_stage_certificate_requests(database_path, course_id, stage, criteria, requested_at):
    if not criteria:
        return
    connection = get_connection(database_path)
    try:
        instructors = [row["name"] for row in connection.execute(
            """SELECT instructors.name FROM instructors JOIN course_instructors
               ON course_instructors.instructor_id = instructors.id
               WHERE course_instructors.course_id = ? ORDER BY instructors.name COLLATE NOCASE""",
            (course_id,),
        ).fetchall()]
        instructor_snapshot = json.dumps(instructors)
        pupils = connection.execute(
            "SELECT sailors.id, enrolments.id AS enrolment_id FROM sailors "
            "JOIN enrolments ON enrolments.sailor_id = sailors.id WHERE enrolments.course_id = ?",
            (course_id,),
        ).fetchall()
        for pupil in pupils:
            progress_rows = connection.execute(
                "SELECT criterion, completed FROM progress WHERE enrolment_id = ?",
                (pupil["enrolment_id"],),
            ).fetchall()
            progress = {row["criterion"]: bool(row["completed"]) for row in progress_rows}
            stage_complete = all(progress.get(criterion, False) for criterion in criteria)
            existing = connection.execute(
                "SELECT id, status, course_id FROM certificates WHERE sailor_id = ? AND stage = ?",
                (pupil["id"], stage),
            ).fetchone()
            if stage_complete and existing is None:
                connection.execute(
                    """INSERT INTO certificates
                       (sailor_id, name, issued_on, stage, course_id, status, requested_at, instructors)
                       VALUES (?, ?, '', ?, ?, 'pending', ?, ?)""",
                    (pupil["id"], stage, stage, course_id, requested_at, instructor_snapshot),
                )
            elif stage_complete and existing["status"] == "cancelled":
                connection.execute(
                    """UPDATE certificates SET status = 'pending', course_id = ?,
                       requested_at = ?, issued_on = '', instructors = ?, award_comment = '',
                       feedback_mode = '', best_element = '', good_attribute = '',
                       top_tip = '', practice = '', personal_message = '' WHERE id = ?""",
                    (course_id, requested_at, instructor_snapshot, existing["id"]),
                )
            elif (
                not stage_complete and existing is not None
                and existing["status"] == "pending"
                and existing["course_id"] == course_id
            ):
                connection.execute(
                    "UPDATE certificates SET status = 'cancelled' WHERE id = ?",
                    (existing["id"],),
                )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def add_instructor_to_course(database_path, name, course_id):
    connection = get_connection(database_path)
    try:
        name_key = name.casefold()
        connection.execute(
            "INSERT OR IGNORE INTO instructors (name, name_key) VALUES (?, ?)",
            (name, name_key),
        )
        instructor = connection.execute(
            "SELECT id, name FROM instructors WHERE name_key = ?", (name_key,)
        ).fetchone()
        result = connection.execute(
            "INSERT OR IGNORE INTO course_instructors (course_id, instructor_id) VALUES (?, ?)",
            (course_id, instructor["id"]),
        )
        connection.commit()
        return {"id": instructor["id"], "name": instructor["name"], "added": result.rowcount > 0}
    finally:
        connection.close()


def get_instructors_for_course(database_path, course_id):
    connection = get_connection(database_path)
    try:
        rows = connection.execute(
            """SELECT instructors.id, instructors.name FROM instructors
               JOIN course_instructors ON course_instructors.instructor_id = instructors.id
               WHERE course_instructors.course_id = ?
               ORDER BY instructors.name COLLATE NOCASE""",
            (course_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def instructor_can_access_course(database_path, instructor_id, course_id):
    connection = get_connection(database_path)
    try:
        return connection.execute(
            "SELECT 1 FROM course_instructors WHERE instructor_id = ? AND course_id = ?",
            (instructor_id, course_id),
        ).fetchone() is not None
    finally:
        connection.close()


def sailor_can_access_course(database_path, sailor_id, course_id):
    connection = get_connection(database_path)
    try:
        return connection.execute(
            "SELECT 1 FROM enrolments WHERE sailor_id = ? AND course_id = ?",
            (sailor_id, course_id),
        ).fetchone() is not None
    finally:
        connection.close()


def get_course_ids_for_instructor(database_path, instructor_id):
    connection = get_connection(database_path)
    try:
        rows = connection.execute(
            "SELECT course_id FROM course_instructors WHERE instructor_id = ?",
            (instructor_id,),
        ).fetchall()
        return {row["course_id"] for row in rows}
    finally:
        connection.close()


def get_course_ids_for_sailor(database_path, sailor_id):
    connection = get_connection(database_path)
    try:
        rows = connection.execute(
            "SELECT course_id FROM enrolments WHERE sailor_id = ?", (sailor_id,)
        ).fetchall()
        return {row["course_id"] for row in rows}
    finally:
        connection.close()


def delete_course(database_path, course_id):
    """Delete a course and its progress, preserving sailors elsewhere."""
    connection = get_connection(database_path)
    try:
        connection.execute("UPDATE notes SET course_id = NULL WHERE course_id = ?", (course_id,))
        connection.execute(
            "UPDATE certificates SET course_id = NULL, status = 'cancelled' "
            "WHERE course_id = ? AND status = 'pending'",
            (course_id,),
        )
        connection.execute(
            "UPDATE certificates SET course_id = NULL WHERE course_id = ?",
            (course_id,),
        )
        connection.execute("DELETE FROM course_instructors WHERE course_id = ?", (course_id,))
        connection.execute(
            "DELETE FROM progress WHERE enrolment_id IN "
            "(SELECT id FROM enrolments WHERE course_id = ?)", (course_id,)
        )
        connection.execute("DELETE FROM enrolments WHERE course_id = ?", (course_id,))
        result = connection.execute("DELETE FROM courses WHERE id = ?", (course_id,))
        connection.commit()
        return result.rowcount > 0
    finally:
        connection.close()


def delete_sailor(database_path, sailor_id):
    """Delete a sailor and all enrolments, progress, notes, and certificates."""
    connection = get_connection(database_path)
    try:
        connection.execute(
            "DELETE FROM progress WHERE enrolment_id IN "
            "(SELECT id FROM enrolments WHERE sailor_id = ?)", (sailor_id,)
        )
        connection.execute("DELETE FROM enrolments WHERE sailor_id = ?", (sailor_id,))
        connection.execute("DELETE FROM notes WHERE sailor_id = ?", (sailor_id,))
        connection.execute("DELETE FROM certificates WHERE sailor_id = ?", (sailor_id,))
        result = connection.execute("DELETE FROM sailors WHERE id = ?", (sailor_id,))
        connection.commit()
        return result.rowcount > 0
    finally:
        connection.close()


def add_sailor_to_course(database_path, name, course_id, criteria):
    """Save a sailor, enrol them on a course and initialise their progress."""

    connection = get_connection(database_path)

    try:
        name_key = name.casefold()

        # Create the sailor if they don't already exist.
        connection.execute(
            """
            INSERT OR IGNORE INTO sailors (name, name_key)
            VALUES (?, ?)
            """,
            (name, name_key),
        )

        sailor = connection.execute(
            "SELECT id FROM sailors WHERE name_key = ?", (name_key,)
        ).fetchone()

        course = connection.execute(
            "SELECT id FROM courses WHERE id = ?", (course_id,)
        ).fetchone()

        if course is None:
            raise ValueError(f"Course not found: {course_id}")

        # Enrol the sailor if they aren't already enrolled.
        connection.execute(
            """
            INSERT OR IGNORE INTO enrolments (sailor_id, course_id)
            VALUES (?, ?)
            """,
            (sailor["id"], course["id"]),
        )

        enrolment = connection.execute(
            """
            SELECT id FROM enrolments
            WHERE sailor_id = ? AND course_id = ?
            """,
            (sailor["id"], course["id"]),
        ).fetchone()

        # Create an unticked progress record for every criterion.
        for criterion in criteria:
            connection.execute(
                """
                INSERT OR IGNORE INTO progress
                    (enrolment_id, criterion, completed)
                VALUES (?, ?, 0)
                """,
                (enrolment["id"], criterion),
            )

        connection.commit()

    finally:
        connection.close()


def get_sailors_for_course(database_path, course_id):
    """Retrieve sailors, progress and notes for a course."""

    connection = get_connection(database_path)

    try:
        rows = connection.execute(
            """
            SELECT sailors.id, sailors.name, enrolments.id AS enrolment_id
            FROM sailors
            JOIN enrolments ON sailors.id = enrolments.sailor_id
            WHERE enrolments.course_id = ?
            ORDER BY sailors.name COLLATE NOCASE
            """,
            (course_id,),
        ).fetchall()

        sailors = []

        for row in rows:
            progress_rows = connection.execute(
                """
                SELECT criterion, completed
                FROM progress
                WHERE enrolment_id = ?
                """,
                (row["enrolment_id"],),
            ).fetchall()

            note_rows = connection.execute(
                """
                SELECT notes.text, notes.created_at,
                       COALESCE(instructors.name, 'Unattributed') AS author,
                       courses.name AS course_name
                FROM notes
                LEFT JOIN instructors ON instructors.id = notes.instructor_id
                LEFT JOIN courses ON courses.id = notes.course_id
                WHERE notes.sailor_id = ?
                ORDER BY notes.id DESC
                """,
                (row["id"],),
            ).fetchall()

            sailors.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "progress": {
                        item["criterion"]: bool(item["completed"])
                        for item in progress_rows
                    },
                    "notes": [
                        {
                            "text": item["text"],
                            "created_at": item["created_at"],
                            "author": item["author"],
                            "course_name": item["course_name"],
                        }
                        for item in note_rows
                    ],
                }
            )

        return sailors

    finally:
        connection.close()


def update_criteria(
    database_path, course_id, criteria, completed, sailor_id=None
):
    """Set one or more criteria for all, or one, sailor in a course."""
    if not criteria:
        return 0

    connection = get_connection(database_path)

    try:
        criterion_placeholders = ", ".join("?" for _ in criteria)
        sailor_filter = ""
        parameters = [int(completed), *criteria, course_id]
        if sailor_id is not None:
            sailor_filter = " AND sailor_id = ?"
            parameters.append(sailor_id)

        result = connection.execute(
            f"""
            UPDATE progress
            SET completed = ?
            WHERE criterion IN ({criterion_placeholders})
              AND enrolment_id IN (
                  SELECT id
                  FROM enrolments
                  WHERE course_id = ?{sailor_filter}
              )
            """,
            parameters,
        )

        connection.commit()
        return result.rowcount > 0

    finally:
        connection.close()


def add_note(database_path, sailor_name, note, created_at, course_id=None, instructor_id=None):
    """Save an instructor note against a sailor."""

    connection = get_connection(database_path)

    try:
        sailor = connection.execute(
            "SELECT id FROM sailors WHERE name_key = ?", (sailor_name.casefold(),)
        ).fetchone()

        if sailor is None:
            return False

        connection.execute(
            """
            INSERT INTO notes (sailor_id, text, created_at, course_id, instructor_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (sailor["id"], note, created_at, course_id, instructor_id),
        )

        connection.commit()
        return True

    finally:
        connection.close()
