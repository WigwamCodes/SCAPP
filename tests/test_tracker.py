import sqlite3
import tempfile
import unittest
from pathlib import Path

from database import get_courses, get_sailors_for_course
from scapp import Course, Office, syllabus_data
from web_app import create_app


TEST_SYLLABUS = {
    "Stage 1": {
        "Practical": {
            "Sailing": ["Can steer", "Can tack"],
        }
    },
    "Stage 2": {
        "Practical": {
            "Sailing": ["Can gybe"],
        }
    },
}


class CourseTests(unittest.TestCase):
    def test_office_creates_course_with_default_syllabus(self):
        course = Office("Office").CreateCourse("Stage 1")

        self.assertIsInstance(course, Course)
        self.assertEqual(course.syllabus, syllabus_data)

    def test_course_info_includes_its_criteria(self):
        course = Course("Stage 1", TEST_SYLLABUS)

        self.assertEqual(
            course.get_course_info()["criteria"], ["Can steer", "Can tack"]
        )


class TrackerWebTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test.sqlite3"
        self.app = create_app(TEST_SYLLABUS, self.database_path)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.course_id = self.create_course()

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_course(self, name="Tuesday group", stage="Stage 1"):
        response = self.client.post(
            "/courses", data={"name": name, "stage": stage}
        )
        self.assertEqual(response.status_code, 302)
        return int(response.location.rsplit("/", 1)[1])

    def add_sailor(self, name="Alex", course_id=None):
        course_id = self.course_id if course_id is None else course_id
        return self.client.post(
            f"/courses/{course_id}/sailors",
            data={"name": name},
            follow_redirects=True,
        )

    def test_new_dashboard_can_have_no_courses(self):
        empty_path = Path(self.temp_dir.name) / "empty.sqlite3"
        app = create_app(TEST_SYLLABUS, empty_path)
        response = app.test_client().get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No courses yet", response.data)
        self.assertNotIn(b'class="course-card"', response.data)

    def test_missing_course_shows_a_useful_not_found_page(self):
        response = self.client.get("/courses/999999")

        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Page not found", response.data)
        self.assertIn(b"Back to all courses", response.data)

    def find_sailor(self, course_id, name):
        return next(
            sailor
            for sailor in get_sailors_for_course(self.database_path, course_id)
            if sailor["name"].casefold() == name.casefold()
        )

    def test_dashboard_lists_created_courses_not_empty_syllabus_stages(self):
        second_same_stage = self.create_course("Thursday group")
        stage_two = self.create_course("Stage 2 group", "Stage 2")

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Tuesday group", response.data)
        self.assertIn(b"Thursday group", response.data)
        self.assertIn(b"Stage 2 group", response.data)
        self.assertEqual(len(get_courses(self.database_path)), 3)
        self.assertNotEqual(self.course_id, second_same_stage)
        self.assertNotEqual(self.course_id, stage_two)

    def test_add_sailor_and_render_progress_checklist(self):
        response = self.add_sailor()

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Alex", response.data)
        self.assertIn(b"Can steer", response.data)
        self.assertIn(b"0/2", response.data)

    def test_criterion_can_be_ticked_and_unticked(self):
        self.add_sailor()
        sailor = self.find_sailor(self.course_id, "Alex")
        url = f"/courses/{self.course_id}/sailors/{sailor['id']}/criteria"

        ticked = self.client.post(
            url,
            data={"criterion": "Can steer", "completed": "on"},
            follow_redirects=True,
        )
        self.assertIn(b"1/2", ticked.data)

        unticked = self.client.post(
            url,
            data={"criterion": "Can steer"},
            follow_redirects=True,
        )
        self.assertIn(b"0/2", unticked.data)

    def test_note_is_shown_with_a_timestamp(self):
        self.add_sailor()
        sailor = self.find_sailor(self.course_id, "Alex")
        response = self.client.post(
            f"/courses/{self.course_id}/sailors/{sailor['id']}/notes",
            data={"note": "Good progress on the water."},
            follow_redirects=True,
        )

        self.assertIn(b"Good progress on the water.", response.data)
        self.assertIn(b"T", response.data)

    def test_duplicate_sailor_is_not_added_twice_to_one_course(self):
        self.add_sailor("Alex")
        response = self.add_sailor("alex")

        self.assertIn(b"already in this course", response.data)
        self.assertEqual(
            len(get_sailors_for_course(self.database_path, self.course_id)), 1
        )

    def test_unknown_criterion_is_rejected(self):
        self.add_sailor()
        sailor = self.find_sailor(self.course_id, "Alex")
        response = self.client.post(
            f"/courses/{self.course_id}/sailors/{sailor['id']}/criteria",
            data={"criterion": "Not on the syllabus"},
        )

        self.assertEqual(response.status_code, 400)

    def test_same_sailor_can_join_different_course_instances_at_same_stage(self):
        another_course = self.create_course("Wednesday group")
        self.add_sailor("Alex", self.course_id)
        response = self.add_sailor("Alex", another_course)

        self.assertIn(b"Alex", response.data)
        self.assertEqual(
            len(get_sailors_for_course(self.database_path, self.course_id)), 1
        )
        self.assertEqual(
            len(get_sailors_for_course(self.database_path, another_course)), 1
        )

    def test_criterion_bulk_update_is_limited_to_that_course(self):
        another_course = self.create_course("Wednesday group")
        self.add_sailor("Alex", self.course_id)
        self.add_sailor("Sam", self.course_id)
        self.add_sailor("Alex", another_course)

        response = self.client.post(
            f"/courses/{self.course_id}/criteria",
            data={"criterion": "Can steer", "completed": "1"},
            follow_redirects=True,
        )

        self.assertIn(b"Criterion completed for all sailors", response.data)
        for name in ("Alex", "Sam"):
            self.assertTrue(
                self.find_sailor(self.course_id, name)["progress"]["Can steer"]
            )
        self.assertFalse(
            self.find_sailor(another_course, "Alex")["progress"]["Can steer"]
        )

    def test_category_can_be_set_for_one_sailor_or_the_whole_course(self):
        self.add_sailor("Alex")
        self.add_sailor("Sam")
        alex = self.find_sailor(self.course_id, "Alex")
        category_url = f"/courses/{self.course_id}/categories"

        self.client.post(
            category_url,
            data={
                "section": "Practical",
                "category": "Sailing",
                "sailor_id": str(alex["id"]),
                "completed": "1",
            },
        )
        self.assertTrue(
            all(self.find_sailor(self.course_id, "Alex")["progress"].values())
        )
        self.assertFalse(
            any(self.find_sailor(self.course_id, "Sam")["progress"].values())
        )

        self.client.post(
            category_url,
            data={
                "section": "Practical",
                "category": "Sailing",
                "completed": "1",
            },
        )
        self.assertTrue(
            all(self.find_sailor(self.course_id, "Sam")["progress"].values())
        )

        self.client.post(
            category_url,
            data={
                "section": "Practical",
                "category": "Sailing",
                "completed": "0",
            },
        )
        self.assertFalse(
            any(self.find_sailor(self.course_id, "Alex")["progress"].values())
        )
        self.assertFalse(
            any(self.find_sailor(self.course_id, "Sam")["progress"].values())
        )

    def test_old_stage_courses_migrate_and_empty_stages_are_removed(self):
        legacy_path = Path(self.temp_dir.name) / "legacy.sqlite3"
        connection = sqlite3.connect(legacy_path)
        connection.executescript(
            """
            CREATE TABLE courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE sailors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                name_key TEXT NOT NULL UNIQUE
            );
            CREATE TABLE enrolments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sailor_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                UNIQUE (sailor_id, course_id)
            );
            CREATE TABLE progress (
                enrolment_id INTEGER NOT NULL,
                criterion TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (enrolment_id, criterion)
            );
            INSERT INTO courses (id, name) VALUES (1, 'Stage 1'), (2, 'Stage 2');
            INSERT INTO sailors (id, name, name_key) VALUES (1, 'Alex', 'alex');
            INSERT INTO enrolments (id, sailor_id, course_id) VALUES (1, 1, 1);
            INSERT INTO progress (enrolment_id, criterion, completed)
                VALUES (1, 'Can steer', 1);
            """
        )
        connection.commit()
        connection.close()

        app = create_app(TEST_SYLLABUS, legacy_path)
        app.config["TESTING"] = True
        response = app.test_client().get("/")
        courses = get_courses(legacy_path)

        self.assertIn(b"Stage 1", response.data)
        self.assertEqual(
            [(course["name"], course["stage"]) for course in courses],
            [("Stage 1", "Stage 1")],
        )
        sailors = get_sailors_for_course(legacy_path, courses[0]["id"])
        self.assertTrue(sailors[0]["progress"]["Can steer"])

    def test_course_with_removed_syllabus_stage_remains_viewable(self):
        self.add_sailor("Alex")
        sailor = self.find_sailor(self.course_id, "Alex")
        self.client.post(
            f"/courses/{self.course_id}/sailors/{sailor['id']}/criteria",
            data={"criterion": "Can steer", "completed": "on"},
        )

        updated_app = create_app({"Stage 2": TEST_SYLLABUS["Stage 2"]}, self.database_path)
        updated_app.config["TESTING"] = True
        updated_client = updated_app.test_client()
        dashboard = updated_client.get("/")
        detail = updated_client.get(
            f"/courses/{self.course_id}?sailor_id={sailor['id']}"
        )

        self.assertIn(b"Tuesday group", dashboard.data)
        self.assertIn(b"missing from the current syllabus", dashboard.data)
        self.assertEqual(detail.status_code, 200)
        self.assertIn(b"Can steer", detail.data)
        self.assertIn(b"read-only", detail.data)
        self.assertNotIn(b'type="checkbox"', detail.data)

        response = updated_client.post(
            f"/courses/{self.course_id}/criteria",
            data={"criterion": "Can steer", "completed": "1"},
        )
        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
