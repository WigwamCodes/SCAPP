import unittest

from scapp import Course, Office, syllabus_data
from web_app import create_app


TEST_SYLLABUS = {
    "Stage 1": {
        "Practical": {
            "Sailing": ["Can steer", "Can tack"],
        }
    }
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
        self.app = create_app(TEST_SYLLABUS)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def add_sailor(self, name="Alex"):
        return self.client.post(
            "/sailors",
            data={"name": name, "stage": "Stage 1"},
            follow_redirects=True,
        )

    def test_add_sailor_and_render_progress_checklist(self):
        response = self.add_sailor()

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Alex", response.data)
        self.assertIn(b"Can steer", response.data)
        self.assertIn(b"0/2", response.data)

    def test_criterion_can_be_ticked_and_unticked(self):
        self.add_sailor()
        url = "/sailors/Alex/criteria"

        ticked = self.client.post(
            url,
            data={
                "stage": "Stage 1",
                "criterion": "Can steer",
                "completed": "on",
            },
            follow_redirects=True,
        )
        self.assertIn(b"1/2", ticked.data)

        unticked = self.client.post(
            url,
            data={"stage": "Stage 1", "criterion": "Can steer"},
            follow_redirects=True,
        )
        self.assertIn(b"0/2", unticked.data)

    def test_note_is_shown_with_a_timestamp(self):
        self.add_sailor()
        response = self.client.post(
            "/sailors/Alex/notes",
            data={"stage": "Stage 1", "note": "Good progress on the water."},
            follow_redirects=True,
        )

        self.assertIn(b"Good progress on the water.", response.data)
        self.assertIn(b"T", response.data)

    def test_duplicate_sailor_is_not_added_twice(self):
        self.add_sailor("Alex")
        response = self.add_sailor("alex")

        self.assertIn(b"already in this course", response.data)
        self.assertEqual(response.data.count(b'class="sailor-link'), 1)

    def test_unknown_criterion_is_rejected(self):
        self.add_sailor()
        response = self.client.post(
            "/sailors/Alex/criteria",
            data={"stage": "Stage 1", "criterion": "Not on the syllabus"},
        )

        self.assertEqual(response.status_code, 400)

    def test_sailor_can_be_enrolled_in_multiple_stages(self):
        syllabus = {
            **TEST_SYLLABUS,
            "Stage 2": {"Practical": {"Sailing": ["Can gybe"]}},
        }
        client = create_app(syllabus).test_client()
        client.post("/sailors", data={"name": "Alex", "stage": "Stage 1"})
        response = client.post(
            "/sailors",
            data={"name": "Alex", "stage": "Stage 2"},
            follow_redirects=True,
        )

        self.assertIn(b"Alex", response.data)
        self.assertIn(b"Can gybe", response.data)


if __name__ == "__main__":
    unittest.main()
