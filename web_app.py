from datetime import datetime
import secrets
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, url_for

from scapp import Course, syllabus_data
from database import (
    init_db,
    add_sailor_to_course,
    get_sailors_for_course,
    update_criterion,
    add_note,
)


def create_app(syllabus=None, database_path=None):
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(32)

    syllabus = syllabus_data if syllabus is None else syllabus

    if database_path is None:
        database_path = Path(app.instance_path) / "scapp.sqlite3"

    init_db(database_path, syllabus)

    courses = {name: Course(name, syllabus) for name in syllabus}

    def get_course(stage_name):
        course = courses.get(stage_name)
        if course is None:
            abort(404)
        return course

    def get_sailor(course_name, sailor_name):
        sailors = get_sailors_for_course(database_path, course_name)

        for sailor in sailors:
            if sailor["name"].casefold() == sailor_name.casefold():
                return sailor

        abort(404)

    @app.get("/")
    def index():
        stage_name = request.args.get("stage", next(iter(courses)))
        course = get_course(stage_name)
        selected_name = request.args.get("sailor")

        sailors = get_sailors_for_course(database_path, stage_name)

        selected_sailor = None

        if selected_name is not None:
            selected_sailor = next(
                (
                    sailor
                    for sailor in sailors
                    if sailor["name"].casefold() == selected_name.casefold()
                ),
                None,
            )

        progress = {}

        for sailor in sailors:
            ticks = sailor["progress"]
            complete = sum(ticks.values())
            total = len(ticks)

            progress[sailor["name"]] = {
                "complete": complete,
                "total": total,
                "percent": round(complete / total * 100) if total else 0,
            }

        return render_template(
            "index.html",
            courses=courses,
            course=course,
            sailors=sailors,
            selected_sailor=selected_sailor,
            progress=progress,
        )

    @app.post("/sailors")
    def add_sailor():
        stage_name = request.form.get("stage", "")
        course = get_course(stage_name)
        name = request.form.get("name", "").strip()

        if not name:
            flash("Enter a sailor's name.", "error")
            return redirect(url_for("index", stage=stage_name))

        criteria = [
            criterion
            for categories in course.syllabus.get(stage_name, {}).values()
            for criteria_list in categories.values()
            for criterion in criteria_list
        ]

        existing_sailors = get_sailors_for_course(database_path, stage_name)

        already_enrolled = any(
            sailor["name"].casefold() == name.casefold() for sailor in existing_sailors
        )

        if already_enrolled:
            flash(f"{name} is already in this course.", "error")
        else:
            add_sailor_to_course(database_path, name, stage_name, criteria)
            flash(f"Added {name} to {stage_name}.", "success")

        return redirect(url_for("index", stage=stage_name, sailor=name))

    @app.post("/sailors/<sailor_name>/criteria")
    def update_sailor_criterion(sailor_name):
        stage_name = request.form.get("stage", "")
        course = get_course(stage_name)
        sailor = get_sailor(stage_name, sailor_name)

        criterion = request.form.get("criterion", "")

        if criterion not in sailor["progress"]:
            abort(400, description="Unknown criterion.")

        completed = request.form.get("completed") == "on"

        updated = update_criterion(
            database_path, sailor["name"], stage_name, criterion, completed
        )

        if not updated:
            abort(404)

        updated_sailor = get_sailor(stage_name, sailor_name)
        ticks = updated_sailor["progress"]

        if completed and ticks and all(ticks.values()):
            flash(f"{sailor['name']} has completed {stage_name}!", "success")
        else:
            flash("Progress updated.", "success")

        return redirect(url_for("index", stage=stage_name, sailor=sailor["name"]))

    @app.post("/sailors/<sailor_name>/notes")
    def add_sailor_note(sailor_name):
        stage_name = request.form.get("stage", "")
        get_course(stage_name)

        sailor = get_sailor(stage_name, sailor_name)
        note = request.form.get("note", "").strip()

        if not note:
            flash("Write a note before saving.", "error")
        elif len(note) > 2000:
            flash("Notes must be 2,000 characters or fewer.", "error")
        else:
            created_at = datetime.now().astimezone().isoformat(timespec="minutes")

            add_note(database_path, sailor["name"], note, created_at)

            flash("Note added.", "success")

        return redirect(url_for("index", stage=stage_name, sailor=sailor["name"]))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
