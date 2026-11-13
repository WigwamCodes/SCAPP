import sqlite3
from pathlib import Path


def get_connection(database_path):
    """Open a connection to the SQLite database."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(database_path, syllabus):
    """Create the database tables and register the syllabus courses."""

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
                name TEXT NOT NULL UNIQUE
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

        for course_name in syllabus:
            connection.execute(
                "INSERT OR IGNORE INTO courses (name) VALUES (?)", (course_name,)
            )

        connection.commit()

    finally:
        connection.close()


def add_sailor_to_course(database_path, name, course_name, criteria):
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

        # Find the course's database ID.
        course = connection.execute(
            "SELECT id FROM courses WHERE name = ?", (course_name,)
        ).fetchone()

        if course is None:
            raise ValueError(f"Course not found: {course_name}")

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


def get_sailors_for_course(database_path, course_name):
    """Retrieve sailors, progress and notes for a course."""

    connection = get_connection(database_path)

    try:
        rows = connection.execute(
            """
            SELECT sailors.id, sailors.name, enrolments.id AS enrolment_id
            FROM sailors
            JOIN enrolments ON sailors.id = enrolments.sailor_id
            JOIN courses ON courses.id = enrolments.course_id
            WHERE courses.name = ?
            ORDER BY sailors.name COLLATE NOCASE
            """,
            (course_name,),
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


def update_criterion(database_path, sailor_name, course_name, criterion, completed):
    """Save a sailor's progress against a course criterion."""

    connection = get_connection(database_path)

    try:
        result = connection.execute(
            """
            UPDATE progress
            SET completed = ?
            WHERE criterion = ?
              AND enrolment_id IN (
                  SELECT enrolments.id
                  FROM enrolments
                  JOIN sailors ON sailors.id = enrolments.sailor_id
                  JOIN courses ON courses.id = enrolments.course_id
                  WHERE sailors.name_key = ?
                    AND courses.name = ?
              )
            """,
            (int(completed), criterion, sailor_name.casefold(), course_name),
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
