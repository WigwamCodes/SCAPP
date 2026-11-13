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
                stage TEXT NOT NULL
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
                FOREIGN KEY (sailor_id) REFERENCES sailors(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS certificates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sailor_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                issued_on TEXT NOT NULL,
                FOREIGN KEY (sailor_id) REFERENCES sailors(id)
                    ON DELETE CASCADE
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


def get_courses(database_path):
    """Retrieve course instances with overall checklist completion."""
    connection = get_connection(database_path)

    try:
        rows = connection.execute(
            """
            SELECT courses.id, courses.name, courses.stage,
                   COUNT(DISTINCT enrolments.sailor_id) AS sailor_count,
                   COUNT(progress.criterion) AS total_criteria,
                   COALESCE(SUM(progress.completed), 0) AS completed_criteria
            FROM courses
            LEFT JOIN enrolments ON enrolments.course_id = courses.id
            LEFT JOIN progress ON progress.enrolment_id = enrolments.id
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
            "SELECT id, name, stage FROM courses WHERE id = ?", (course_id,)
        ).fetchone()
        return dict(row) if row is not None else None

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
                SELECT text, created_at
                FROM notes
                WHERE sailor_id = ?
                ORDER BY id
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
                        {"text": item["text"], "created_at": item["created_at"]}
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


def add_note(database_path, sailor_name, note, created_at):
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
            INSERT INTO notes (sailor_id, text, created_at)
            VALUES (?, ?, ?)
            """,
            (sailor["id"], note, created_at),
        )

        connection.commit()
        return True

    finally:
        connection.close()
