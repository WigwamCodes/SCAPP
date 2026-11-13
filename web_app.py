from datetime import datetime
import secrets
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, url_for

from scapp import syllabus_data
from database import (
    add_note,
    add_sailor_to_course,
    create_course,
    get_course_by_id,
    get_courses,
    get_sailors_for_course,
    init_db,
    update_criteria,
)


def create_app(syllabus=None, database_path=None):
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(32)

    syllabus = syllabus_data if syllabus is None else syllabus

    if database_path is None:
        database_path = Path(app.instance_path) / "scapp.sqlite3"

    init_db(database_path, syllabus)

    def get_course(course_id):
        course = get_course_by_id(database_path, course_id)
        if course is None:
            abort(404)
        return course

    def get_syllabus_for_course(course):
        stage_syllabus = syllabus.get(course["stage"])
        if stage_syllabus is None:
            abort(
                409,
                description=(
                    f"{course['stage']} is no longer available in syllabus.json."
                ),
            )
        return stage_syllabus

    def get_sailor(course_id, sailor_id):
        sailors = get_sailors_for_course(database_path, course_id)
        sailor = next((item for item in sailors if item["id"] == sailor_id), None)
        if sailor is None:
            abort(404)
        return sailor

    def get_criteria(course):
        return [
            criterion
            for categories in get_syllabus_for_course(course).values()
            for criteria_list in categories.values()
            for criterion in criteria_list
        ]

    def get_progress(sailors, criteria):
        progress = {}
        for sailor in sailors:
            ticks = sailor["progress"]
            complete = sum(bool(ticks.get(criterion, False)) for criterion in criteria)
            total = len(criteria)
            progress[sailor["id"]] = {
                "complete": complete,
                "total": total,
                "percent": round(complete / total * 100) if total else 0,
            }
        return progress

    def course_redirect(course_id, sailor_id=None):
        return redirect(
            url_for("course_detail", course_id=course_id, sailor_id=sailor_id)
        )

    @app.errorhandler(404)
    def page_not_found(_error):
        return render_template("404.html"), 404

    @app.get("/")
    def index():
        courses = get_courses(database_path)
        for course in courses:
            sailors = get_sailors_for_course(database_path, course["id"])
            course_syllabus = syllabus.get(course["stage"])
            criteria = (
                [
                    criterion
                    for categories in course_syllabus.values()
                    for criteria_list in categories.values()
                    for criterion in criteria_list
                ]
                if course_syllabus is not None
                else list(
                    dict.fromkeys(
                        criterion
                        for sailor in sailors
                        for criterion in sailor["progress"]
                    )
                )
            )
            total = len(criteria) * len(sailors)
            complete = sum(
                bool(sailor["progress"].get(criterion, False))
                for sailor in sailors
                for criterion in criteria
            )
            course["sailor_count"] = len(sailors)
            course["completed_criteria"] = complete
            course["total_criteria"] = total
            course["percent"] = round(complete / total * 100) if total else 0
            course["syllabus_available"] = course_syllabus is not None

        return render_template("index.html", courses=courses, stages=syllabus)

    @app.post("/courses")
    def add_course():
        stage = request.form.get("stage", "")
        name = request.form.get("name", "").strip()

        if stage not in syllabus:
            abort(400, description="Choose a valid syllabus stage.")
        if not name or len(name) > 100:
            flash("Enter a course name of 1 to 100 characters.", "error")
            return redirect(url_for("index"))

        course_id = create_course(database_path, name, stage)
        if course_id is None:
            flash("A course with that name already exists.", "error")
            return redirect(url_for("index"))

        flash(f"Created {name} based on {stage}.", "success")
        return course_redirect(course_id)

    @app.get("/courses/<int:course_id>")
    def course_detail(course_id):
        course = get_course(course_id)
        sailors = get_sailors_for_course(database_path, course_id)
        course_syllabus = syllabus.get(course["stage"])
        criteria = (
            get_criteria(course)
            if course_syllabus is not None
            else list(
                dict.fromkeys(
                    criterion
                    for sailor in sailors
                    for criterion in sailor["progress"]
                )
            )
        )
        progress = get_progress(sailors, criteria)
        selected_id = request.args.get("sailor_id", type=int)
        selected_sailor = next(
            (sailor for sailor in sailors if sailor["id"] == selected_id), None
        )

        return render_template(
            "course.html",
            course=course,
            syllabus=course_syllabus,
            syllabus_available=course_syllabus is not None,
            sailors=sailors,
            selected_sailor=selected_sailor,
            progress=progress,
            criteria=criteria,
        )

    @app.post("/courses/<int:course_id>/sailors")
    def add_sailor(course_id):
        course = get_course(course_id)
        get_syllabus_for_course(course)
        name = request.form.get("name", "").strip()

        if not name or len(name) > 100:
            flash("Enter a sailor's name of 1 to 100 characters.", "error")
            return course_redirect(course_id)

        existing_sailors = get_sailors_for_course(database_path, course_id)
        if any(sailor["name"].casefold() == name.casefold() for sailor in existing_sailors):
            flash(f"{name} is already in this course.", "error")
            return course_redirect(course_id)

        add_sailor_to_course(database_path, name, course_id, get_criteria(course))
        sailor = next(
            sailor
            for sailor in get_sailors_for_course(database_path, course_id)
            if sailor["name"].casefold() == name.casefold()
        )
        flash(f"Added {name} to {course['name']}.", "success")
        return course_redirect(course_id, sailor["id"])

    @app.post("/courses/<int:course_id>/sailors/<int:sailor_id>/criteria")
    def update_sailor_criterion(course_id, sailor_id):
        course = get_course(course_id)
        get_syllabus_for_course(course)
        sailor = get_sailor(course_id, sailor_id)
        criterion = request.form.get("criterion", "")
        if criterion not in get_criteria(course):
            abort(400, description="Unknown criterion.")

        completed = request.form.get("completed") == "on"
        updated = update_criteria(
            database_path, course_id, [criterion], completed, sailor_id
        )
        if not updated:
            abort(404)

        flash("Progress updated.", "success")
        return course_redirect(course_id, sailor["id"])

    @app.post("/courses/<int:course_id>/criteria")
    def update_criterion_for_course(course_id):
        course = get_course(course_id)
        get_syllabus_for_course(course)
        criterion = request.form.get("criterion", "")
        if criterion not in get_criteria(course):
            abort(400, description="Unknown criterion.")

        completed = request.form.get("completed") == "1"
        updated = update_criteria(database_path, course_id, [criterion], completed)
        if updated:
            state = "completed" if completed else "cleared"
            flash(f"Criterion {state} for all sailors in {course['name']}.", "success")
        else:
            flash("There are no enrolled sailors to update.", "error")
        return course_redirect(course_id)

    @app.post("/courses/<int:course_id>/categories")
    def update_category_for_course(course_id):
        course = get_course(course_id)
        get_syllabus_for_course(course)
        section_name = request.form.get("section", "")
        category_name = request.form.get("category", "")
        categories = syllabus[course["stage"]].get(section_name, {})
        criteria = categories.get(category_name)
        if criteria is None:
            abort(400, description="Unknown syllabus category.")

        sailor_id = request.form.get("sailor_id", type=int)
        if sailor_id is not None:
            sailor = get_sailor(course_id, sailor_id)
        else:
            sailor = None

        completed = request.form.get("completed") == "1"
        updated = update_criteria(
            database_path, course_id, criteria, completed, sailor_id
        )
        target = sailor["name"] if sailor is not None else "all sailors"
        if updated:
            state = "completed" if completed else "cleared"
            flash(
                f"{category_name} {state} for {target} in {course['name']}.",
                "success",
            )
        else:
            flash("There are no matching progress records to update.", "error")
        return course_redirect(course_id, sailor_id)

    @app.post("/courses/<int:course_id>/sailors/<int:sailor_id>/notes")
    def add_sailor_note(course_id, sailor_id):
        get_course(course_id)
        sailor = get_sailor(course_id, sailor_id)
        note = request.form.get("note", "").strip()

        if not note:
            flash("Write a note before saving.", "error")
        elif len(note) > 2000:
            flash("Notes must be 2,000 characters or fewer.", "error")
        else:
            created_at = datetime.now().astimezone().isoformat(timespec="minutes")
            add_note(database_path, sailor["name"], note, created_at)
            flash("Note added.", "success")

        return course_redirect(course_id, sailor["id"])

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
