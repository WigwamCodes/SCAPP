from datetime import datetime
import secrets
from flask import Flask, abort, flash, redirect, render_template, request, url_for
from scapp import Course, Sailor, syllabus_data


def create_app(syllabus=None):
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(32)
    syllabus = syllabus_data if syllabus is None else syllabus
    courses = {name: Course(name, syllabus) for name in syllabus}
    sailors_by_name = {}

    def get_course(stage_name):
        course = courses.get(stage_name)
        if course is None:
            abort(404)
        return course

    def get_sailor(course, sailor_name):
        for sailor in course.sailors:
            if sailor.name == sailor_name:
                return sailor
        abort(404)

    @app.get("/")
    def index():
        stage_name = request.args.get("stage", next(iter(courses)))
        course = get_course(stage_name)
        selected_name = request.args.get("sailor")
        selected_sailor = None
        if selected_name is not None:
            selected_sailor = get_sailor(course, selected_name)

        sailors = sorted(course.sailors, key=lambda sailor: sailor.name.casefold())
        progress = {}
        for sailor in sailors:
            ticks = sailor.progress.get(stage_name, {})
            complete = sum(ticks.values())
            total = len(ticks)
            progress[sailor.name] = {
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

        sailor_key = name.casefold()
        sailor = sailors_by_name.get(sailor_key)
        if sailor is None:
            sailor = Sailor(name)
            sailors_by_name[sailor_key] = sailor

        if sailor in course.sailors:
            flash(f"{sailor.name} is already in this course.", "error")
        else:
            course.add_sailor(sailor)
            flash(f"Added {sailor.name} to {stage_name}.", "success")
        return redirect(url_for("index", stage=stage_name, sailor=sailor.name))

    @app.post("/sailors/<sailor_name>/criteria")
    def update_criterion(sailor_name):
        stage_name = request.form.get("stage", "")
        course = get_course(stage_name)
        sailor = get_sailor(course, sailor_name)
        criterion = request.form.get("criterion", "")
        if criterion not in sailor.progress.get(stage_name, {}):
            abort(400, description="Unknown criterion.")

        completed = request.form.get("completed") == "on"
        course.update_criterion(sailor, criterion, completed)
        if completed and sailor.is_stage_completed(stage_name):
            flash(f"{sailor.name} has completed {stage_name}!", "success")
        else:
            flash("Progress updated.", "success")
        return redirect(url_for("index", stage=stage_name, sailor=sailor.name))

    @app.post("/sailors/<sailor_name>/notes")
    def add_note(sailor_name):
        stage_name = request.form.get("stage", "")
        course = get_course(stage_name)
        sailor = get_sailor(course, sailor_name)
        note = request.form.get("note", "").strip()
        if not note:
            flash("Write a note before saving.", "error")
        elif len(note) > 2000:
            flash("Notes must be 2,000 characters or fewer.", "error")
        else:
            created_at = datetime.now().astimezone().isoformat(timespec="minutes")
            sailor.add_note(note, created_at)
            flash("Note added.", "success")
        return redirect(url_for("index", stage=stage_name, sailor=sailor.name))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
