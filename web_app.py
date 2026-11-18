import secrets
import argparse
import json
from datetime import date, datetime
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

from database import (
    add_note,
    add_sailor_award,
    add_course_sessions,
    add_instructor_to_course,
    add_sailor_to_course,
    complete_course_session,
    create_course_setup,
    delete_course,
    delete_sailor,
    get_office_sessions,
    get_pending_certificates,
    get_pending_stage_certificates_for_course,
    get_course_by_id,
    get_course_ids_for_instructor,
    get_course_ids_for_sailor,
    get_courses,
    get_instructors,
    get_instructors_for_course,
    get_sessions_for_course,
    get_sailors,
    get_sailors_for_course,
    get_sailor_profile,
    instructor_can_access_course,
    instructor_can_view_sailor,
    issue_certificate,
    init_db,
    sailor_can_access_course,
    save_course_session,
    save_certificate_feedback,
    set_course_archived,
    sync_stage_certificate_requests,
    update_criteria,
)
from scapp import syllabus_data


def create_app(syllabus=None, database_path=None):
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(32)

    syllabus = syllabus_data if syllabus is None else syllabus

    if database_path is None:
        database_path = Path(app.instance_path) / "scapp.sqlite3"

    init_db(database_path, syllabus)

    for saved_course in get_courses(database_path):
        try:
            stage_data = json.loads(saved_course["syllabus_snapshot"] or "null")
        except (TypeError, json.JSONDecodeError):
            stage_data = None
        stage_data = stage_data or syllabus.get(saved_course["stage"])
        if stage_data is not None:
            stage_criteria = [
                criterion
                for categories in stage_data.values()
                for criteria_list in categories.values()
                for criterion in criteria_list
            ]
            sync_stage_certificate_requests(
                database_path,
                saved_course["id"],
                saved_course["stage"],
                stage_criteria,
                datetime.now().astimezone().isoformat(timespec="minutes"),
            )

    def active_view():
        return session.get("view", "office"), session.get("actor_id")

    def require_office():
        if active_view()[0] != "office":
            abort(403, description="This action is available in the office view.")

    def require_assigned_instructor(course_id):
        view, actor_id = active_view()
        if view != "instructor" or actor_id is None or not instructor_can_access_course(
            database_path, actor_id, course_id
        ):
            abort(403, description="Only an instructor assigned to this course can update it.")

    @app.context_processor
    def add_view_context():
        view, actor_id = active_view()
        return {
            "current_view": view,
            "current_actor_id": actor_id,
            "view_instructors": get_instructors(database_path),
            "view_pupils": get_sailors(database_path),
        }

    def get_course(course_id):
        course = get_course_by_id(database_path, course_id)
        if course is None:
            abort(404)
        try:
            course["syllabus"] = json.loads(course["syllabus_snapshot"] or "null")
        except (TypeError, json.JSONDecodeError):
            course["syllabus"] = None
        return course

    def get_syllabus_for_course(course):
        stage_syllabus = course.get("syllabus") or syllabus.get(course["stage"])
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

    def refresh_stage_certificates(course):
        stage_syllabus = course.get("syllabus") or syllabus.get(course["stage"])
        if stage_syllabus is None:
            return
        sync_stage_certificate_requests(
            database_path,
            course["id"],
            course["stage"],
            [criterion for categories in stage_syllabus.values()
             for criteria_list in categories.values() for criterion in criteria_list],
            datetime.now().astimezone().isoformat(timespec="minutes"),
        )

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
                "all_complete": bool(total) and complete == total,
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
        view, actor_id = active_view()
        courses = get_courses(database_path)
        if view == "instructor" and actor_id is not None:
            course_ids = get_course_ids_for_instructor(database_path, actor_id)
            courses = [course for course in courses if course["id"] in course_ids]
        elif view == "pupil" and actor_id is not None:
            course_ids = get_course_ids_for_sailor(database_path, actor_id)
            courses = [course for course in courses if course["id"] in course_ids]
        for course in courses:
            sailors = get_sailors_for_course(database_path, course["id"])
            if view == "pupil":
                sailors = [sailor for sailor in sailors if sailor["id"] == actor_id]
            try:
                course_syllabus = json.loads(course.get("syllabus_snapshot") or "null")
            except (TypeError, json.JSONDecodeError):
                course_syllabus = None
            course_syllabus = course_syllabus or syllabus.get(course["stage"])
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

        return render_template(
            "index.html", courses=courses, stages=syllabus,
            current_view=view,
            pupil_awards=(
                get_sailor_profile(database_path, actor_id)
                if view == "pupil" and actor_id is not None
                else None
            ),
        )

    @app.post("/view")
    def change_view():
        selected = request.form.get("view", "")
        if selected == "office":
            session["view"] = "office"
            session.pop("actor_id", None)
        else:
            try:
                view, actor_id_text = selected.split(":", 1)
                actor_id = int(actor_id_text)
            except (ValueError, TypeError):
                abort(400, description="Choose a valid view.")
            if view == "instructor" and any(
                item["id"] == actor_id for item in get_instructors(database_path)
            ):
                session["view"] = view
                session["actor_id"] = actor_id
            elif view == "pupil" and any(
                item["id"] == actor_id for item in get_sailors(database_path)
            ):
                session["view"] = view
                session["actor_id"] = actor_id
            else:
                abort(400, description="Choose an existing instructor or pupil.")
        return redirect(url_for("index"))

    @app.get("/office/sessions")
    def office_sessions():
        require_office()
        return render_template("office_sessions.html", sessions=get_office_sessions(database_path))

    @app.get("/office/archived-courses")
    def office_archived_courses():
        require_office()
        archived = [course for course in get_courses(database_path, include_archived=True)
                    if course.get("archived_at")]
        return render_template("office_archived_courses.html", courses=archived)

    @app.post("/office/courses/<int:course_id>/restore")
    def restore_course(course_id):
        require_office()
        course = next((item for item in get_courses(database_path, include_archived=True)
                       if item["id"] == course_id and item.get("archived_at")), None)
        if course is None:
            abort(404)
        set_course_archived(database_path, course_id)
        flash(f"Restored {course['name']} to active courses.", "success")
        return redirect(url_for("office_archived_courses"))

    @app.post("/courses/<int:course_id>/archive")
    def archive_course(course_id):
        require_office()
        course = get_course(course_id)
        set_course_archived(database_path, course_id, datetime.now().astimezone().isoformat(timespec="minutes"))
        flash(f"Archived {course['name']}.", "success")
        return redirect(url_for("index"))

    @app.get("/my-awards")
    def my_awards():
        view, actor_id = active_view()
        if view != "pupil" or actor_id is None:
            abort(403, description="The awards area is available in a pupil view.")
        profile = get_sailor_profile(database_path, actor_id)
        if profile is None:
            abort(404)
        return render_template("my_awards.html", profile=profile)

    @app.get("/office/pupils")
    def office_pupils():
        require_office()
        pupils = [
            get_sailor_profile(database_path, pupil["id"])
            for pupil in get_sailors(database_path)
        ]
        return render_template("office_pupils.html", pupils=pupils)

    @app.post("/office/pupils/<int:sailor_id>/delete")
    def delete_office_pupil(sailor_id):
        require_office()
        profile = get_sailor_profile(database_path, sailor_id)
        if profile is None:
            abort(404)
        if request.form.get("confirm") != "delete":
            abort(400, description="Confirm pupil deletion to continue.")
        delete_sailor(database_path, sailor_id)
        flash(f"Deleted {profile['name']} and their course records, notes, and certificates.", "success")
        return redirect(url_for("office_pupils"))

    @app.post("/office/pupils/<int:sailor_id>/awards")
    def add_office_pupil_award(sailor_id):
        require_office()
        profile = get_sailor_profile(database_path, sailor_id)
        if profile is None:
            abort(404)
        name = request.form.get("name", "").strip()
        if not name or len(name) > 100:
            flash("Enter an accolade name of 1 to 100 characters.", "error")
            return redirect(url_for("sailor_profile", sailor_id=sailor_id))
        add_sailor_award(
            database_path,
            sailor_id,
            name,
            datetime.now().astimezone().date().isoformat(),
        )
        flash(f"Added {name} to {profile['name']}'s awards.", "success")
        return redirect(url_for("sailor_profile", sailor_id=sailor_id))

    @app.get("/office/certificates")
    def office_certificates():
        require_office()
        return render_template(
            "office_certificates.html",
            certificates=get_pending_certificates(database_path),
        )

    @app.post("/office/certificates/<int:certificate_id>/issue")
    def issue_pending_certificate(certificate_id):
        require_office()
        if issue_certificate(
            database_path, certificate_id,
            datetime.now().astimezone().date().isoformat(),
        ):
            flash("Certificate issued and qualification added to the pupil profile.", "success")
        else:
            flash("This award cannot be issued until its instructor comment is saved.", "error")
        return redirect(url_for("office_certificates"))

    @app.post("/courses/<int:course_id>/awards/<int:certificate_id>/feedback")
    def save_award_feedback(course_id, certificate_id):
        require_assigned_instructor(course_id)
        course = get_course(course_id)
        award = next((item for item in get_pending_stage_certificates_for_course(database_path, course_id)
                      if item["id"] == certificate_id), None)
        if award is None:
            abort(404)
        mode = request.form.get("feedback_mode", "guided")
        if mode not in {"guided", "personal"}:
            abort(400, description="Choose guided or personal feedback.")
        best = request.form.get("best_element", "").strip()
        attribute = request.form.get("good_attribute", "").strip()
        tip = request.form.get("top_tip", "").strip()
        practice = request.form.get("practice", "").strip()
        personal = request.form.get("personal_message", "").strip()
        if mode == "guided":
            if any(not value for value in (best, attribute, tip, practice)):
                flash("Choose an option or add your own text for each guided prompt.", "error")
                return redirect(url_for("course_detail", course_id=course_id, _anchor="award-feedback"))
            custom_values = {
                "best_element": "best_element_custom", "good_attribute": "good_attribute_custom",
                "top_tip": "top_tip_custom", "practice": "practice_custom",
            }
            selected = {"best_element": best, "good_attribute": attribute,
                        "top_tip": tip, "practice": practice}
            for field, custom_field in custom_values.items():
                if selected[field] == "Other":
                    selected[field] = request.form.get(custom_field, "").strip()
            best, attribute, tip, practice = (selected[field] for field in custom_values)
            if any(not value for value in (best, attribute, tip, practice)):
                flash("Add text for each prompt marked Other.", "error")
                return redirect(url_for("course_detail", course_id=course_id, _anchor="award-feedback"))
            comment = (f"You should be proud of your {best}. Your {attribute} really helped you on the water. "
                       f"Your next tip is to {tip}. Between sessions, practise {practice}.")
        else:
            comment = request.form.get("personal_comment", "").strip()
            if not comment:
                flash("Write a personal message for the pupil before saving.", "error")
                return redirect(url_for("course_detail", course_id=course_id, _anchor="award-feedback"))
            best = attribute = tip = practice = ""
        if len(comment) > 2500 or len(personal) > 1000:
            flash("Award comments must be 2,500 characters or fewer.", "error")
            return redirect(url_for("course_detail", course_id=course_id, _anchor="award-feedback"))
        if not save_certificate_feedback(database_path, course_id, certificate_id, mode,
                                         comment, best, attribute, tip, practice, personal):
            abort(404)
        flash(f"Saved the {course['stage']} award comment for {award['sailor_name']}.", "success")
        return redirect(url_for("course_detail", course_id=course_id, _anchor="award-feedback"))

    @app.get("/pupils/<int:sailor_id>")
    def sailor_profile(sailor_id):
        view, actor_id = active_view()
        if view == "pupil":
            abort(403, description="Pupil profiles are available to office staff and instructors.")
        profile = get_sailor_profile(database_path, sailor_id)
        if profile is None:
            abort(404)

        available_courses = profile["courses"]
        selected_course_id = request.args.get("course_id", type=int)
        if view == "instructor":
            if actor_id is None or not instructor_can_view_sailor(database_path, actor_id, sailor_id):
                abort(403, description="This instructor is not assigned to any of this pupil's courses.")
            available_courses = [
                course
                for course in available_courses
                if instructor_can_access_course(database_path, actor_id, course["id"])
            ]
            if selected_course_id is None and available_courses:
                selected_course_id = available_courses[0]["id"]
            if selected_course_id not in {course["id"] for course in available_courses}:
                abort(403, description="Choose one of your assigned courses for this pupil.")

        return render_template(
            "sailor_profile.html",
            profile=profile,
            available_courses=available_courses,
            selected_course_id=selected_course_id,
        )

    @app.post("/courses")
    def add_course():
        require_office()
        stage = request.form.get("stage", "")
        name = request.form.get("name", "").strip()
        try:
            session_count = int(request.form.get("session_count", "0"))
        except ValueError:
            session_count = 0

        if stage not in syllabus:
            abort(400, description="Choose a valid syllabus stage.")
        if not name or len(name) > 100:
            flash("Enter a course name of 1 to 100 characters.", "error")
            return redirect(url_for("index"))
        if not 1 <= session_count <= 30:
            flash("Choose between 1 and 30 sessions.", "error")
            return redirect(url_for("index"))

        instructor_names = []
        instructors_by_id = {str(item["id"]): item["name"] for item in get_instructors(database_path)}
        selected_instructor_ids = request.form.getlist("instructor_ids")
        if any(instructor_id not in instructors_by_id for instructor_id in selected_instructor_ids):
            abort(400, description="Choose instructors from the list.")
        instructor_names.extend(instructors_by_id[instructor_id] for instructor_id in selected_instructor_ids)
        instructor_names.extend(
            line.strip()
            for line in request.form.get("new_instructors", "").splitlines()
            if line.strip()
        )
        instructor_names = list({item.casefold(): item for item in instructor_names}.values())
        if not instructor_names:
            flash("Assign at least one instructor to the course.", "error")
            return redirect(url_for("index"))
        if any(len(instructor_name) > 100 for instructor_name in instructor_names):
            flash("Instructor names must be 100 characters or fewer.", "error")
            return redirect(url_for("index"))

        try:
            pupil_ids = {int(value) for value in request.form.getlist("pupil_ids")}
        except ValueError:
            abort(400, description="Choose pupils from the list.")
        new_pupil_names = [
            line.strip()
            for line in request.form.get("new_pupils", "").splitlines()
            if line.strip()
        ]
        if any(not 1 <= len(pupil_name) <= 100 for pupil_name in new_pupil_names):
            flash("Pupil names must be between 1 and 100 characters.", "error")
            return redirect(url_for("index"))

        session_dates = request.form.getlist("session_dates")[:session_count]
        session_dates.extend([""] * (session_count - len(session_dates)))
        try:
            for session_date in session_dates:
                if session_date:
                    date.fromisoformat(session_date)
        except ValueError:
            flash("Enter valid dates for each session.", "error")
            return redirect(url_for("index"))

        course_criteria = [
            criterion
            for categories in syllabus[stage].values()
            for criteria_list in categories.values()
            for criterion in criteria_list
        ]
        try:
            course_id = create_course_setup(
                database_path,
                name,
                stage,
                course_criteria,
                instructor_names,
                pupil_ids,
                new_pupil_names,
                session_dates,
                syllabus[stage],
            )
        except ValueError as error:
            abort(400, description=str(error))
        if course_id is None:
            flash("A course with that name already exists.", "error")
            return redirect(url_for("index"))

        flash(f"Created {name} with {session_count} sessions based on {stage}.", "success")
        return course_redirect(course_id)

    @app.post("/courses/<int:course_id>/delete")
    def remove_course(course_id):
        require_office()
        course = get_course(course_id)
        if request.form.get("confirm") != "delete":
            abort(400, description="Confirm course deletion to continue.")
        delete_course(database_path, course_id)
        flash(f"Deleted {course['name']} and its course progress.", "success")
        return redirect(url_for("index"))

    @app.get("/courses/<int:course_id>")
    def course_detail(course_id):
        course = get_course(course_id)
        view, actor_id = active_view()
        if view == "instructor" and (
            actor_id is None
            or not instructor_can_access_course(database_path, actor_id, course_id)
        ):
            abort(403, description="This instructor is not assigned to this course.")
        sailors = get_sailors_for_course(database_path, course_id)
        if view == "pupil" and (
            actor_id is None or not sailor_can_access_course(database_path, actor_id, course_id)
        ):
            abort(403, description="Pupils can only view their own enrolled courses.")
        course_syllabus = get_syllabus_for_course(course) if (course.get("syllabus") or course["stage"] in syllabus) else None
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
        if course_syllabus is not None:
            grid_sections = [
                {
                    "name": section_name,
                    "categories": [
                        {"name": category_name, "criteria": criteria_list}
                        for category_name, criteria_list in categories.items()
                    ],
                }
                for section_name, categories in course_syllabus.items()
            ]
        else:
            grid_sections = (
                [
                    {
                        "name": "Saved progress",
                        "categories": [{"name": "Saved criteria", "criteria": criteria}],
                    }
                ]
                if criteria
                else []
            )

        progress = get_progress(sailors, criteria)
        criterion_complete = {
            criterion: bool(sailors)
            and all(sailor["progress"].get(criterion, False) for sailor in sailors)
            for criterion in criteria
        }
        selected_id = actor_id if view == "pupil" else request.args.get("sailor_id", type=int)
        selected_sailor = next(
            (sailor for sailor in sailors if sailor["id"] == selected_id), None
        )
        display_sailors = (
            [selected_sailor]
            if view == "pupil" and selected_sailor is not None
            else ([] if view == "pupil" else sailors)
        )

        return render_template(
            "course.html",
            course=course,
            syllabus=course_syllabus,
            grid_sections=grid_sections,
            syllabus_available=course_syllabus is not None,
            sailors=sailors,
            display_sailors=display_sailors,
            current_view=view,
            course_instructors=get_instructors_for_course(database_path, course_id),
            course_sessions=get_sessions_for_course(database_path, course_id),
            pending_award_comments=get_pending_stage_certificates_for_course(database_path, course_id),
            selected_sailor=selected_sailor,
            progress=progress,
            criteria=criteria,
            criterion_complete=criterion_complete,
        )

    @app.get("/courses/<int:course_id>/sessions")
    def session_planner(course_id):
        require_assigned_instructor(course_id)
        course = get_course(course_id)
        course_syllabus = get_syllabus_for_course(course) if (course.get("syllabus") or course["stage"] in syllabus) else None
        sections = []
        if course_syllabus is not None:
            sections = [
                {
                    "name": section_name,
                    "categories": [
                        {"name": category_name, "criteria": criteria_list}
                        for category_name, criteria_list in categories.items()
                    ],
                }
                for section_name, categories in course_syllabus.items()
            ]
        return render_template(
            "sessions.html",
            course=course,
            sessions=get_sessions_for_course(database_path, course_id),
            sections=sections,
            syllabus_available=course_syllabus is not None,
        )

    @app.post("/courses/<int:course_id>/sessions/<int:session_id>")
    def save_session(course_id, session_id):
        require_assigned_instructor(course_id)
        course = get_course(course_id)
        get_course_session = next(
            (
                item
                for item in get_sessions_for_course(database_path, course_id)
                if item["id"] == session_id
            ),
            None,
        )
        if get_course_session is None:
            abort(404)
        course_syllabus = course.get("syllabus") or syllabus.get(course["stage"])
        if course_syllabus is None:
            abort(409, description="Restore this course's syllabus stage before editing its session plan.")

        action = request.form.get("action", "save")
        if action not in {"save", "mark_done", "complete"}:
            abort(400, description="Choose a valid session action.")

        session_date = request.form.get("session_date", "").strip()
        plan = request.form.get("plan", "").strip()
        feedback = request.form.get("feedback", "").strip()
        improvements = request.form.get("improvements", "").strip()
        if session_date:
            try:
                date.fromisoformat(session_date)
            except ValueError:
                flash("Enter a valid session date.", "error")
                return redirect(url_for("session_planner", course_id=course_id))
        if len(plan) > 10000:
            flash("Session plans must be 10,000 characters or fewer.", "error")
            return redirect(url_for("session_planner", course_id=course_id))
        if len(feedback) > 5000 or len(improvements) > 5000:
            flash("Feedback fields must be 5,000 characters or fewer.", "error")
            return redirect(url_for("session_planner", course_id=course_id))

        valid_criteria = {
            criterion
            for categories in course_syllabus.values()
            for criteria_list in categories.values()
            for criterion in criteria_list
        }
        criteria = (
            get_course_session["criteria"]
            if get_course_session["is_done"]
            else list(dict.fromkeys(request.form.getlist("criteria")))
        )
        if any(criterion not in valid_criteria for criterion in criteria):
            abort(400, description="Choose criteria from this course's syllabus.")

        session_label = f"Session {get_course_session['session_number']}"
        if action == "mark_done" and not criteria:
            flash("Choose at least one planned criterion before marking the session as done.", "error")
            return redirect(url_for("session_planner", course_id=course_id, _anchor=f"session-{session_id}"))
        if action == "complete":
            if not get_course_session["is_done"]:
                abort(400, description="Mark the session as run before completing it.")
            save_course_session(
                database_path, course_id, session_id, session_date, plan, criteria,
                feedback, improvements, True,
            )
            if request.form.get("all_pupils_completed") != "on":
                flash("Confirm that every pupil achieved the planned criteria before completing this session.", "error")
                return redirect(url_for("session_planner", course_id=course_id, _anchor=f"session-{session_id}"))
            if not feedback or not improvements:
                flash("Complete both the feedback and ways to improve fields first.", "error")
                return redirect(url_for("session_planner", course_id=course_id, _anchor=f"session-{session_id}"))
            if not criteria:
                flash("Choose at least one planned criterion before completing this session.", "error")
                return redirect(url_for("session_planner", course_id=course_id, _anchor=f"session-{session_id}"))
            if not get_sailors_for_course(database_path, course_id):
                flash("Enrol pupils before completing a session against their progress.", "error")
                return redirect(url_for("session_planner", course_id=course_id, _anchor=f"session-{session_id}"))
            complete_course_session(
                database_path, course_id, session_id, session_date, plan,
                feedback, improvements, criteria,
            )
            refresh_stage_certificates(course)
            flash(f"{session_label} completed; planned criteria were marked for all pupils.", "success")
        else:
            is_done = bool(get_course_session["is_done"]) or action == "mark_done"
            save_course_session(
                database_path, course_id, session_id, session_date, plan, criteria,
                feedback, improvements, is_done,
            )
            if action == "mark_done":
                flash(f"{session_label} marked as run. Add the feedback and improvement notes.", "success")
            else:
                flash(f"{session_label} plan saved.", "success")
        return redirect(
            url_for("session_planner", course_id=course_id, _anchor=f"session-{session_id}")
        )

    @app.post("/courses/<int:course_id>/sessions/add")
    def create_more_sessions(course_id):
        require_office()
        get_course(course_id)
        try:
            count = int(request.form.get("session_count", "0"))
        except ValueError:
            count = 0
        if not 1 <= count <= 30:
            flash("Choose between 1 and 30 sessions to add.", "error")
            return course_redirect(course_id)
        add_course_sessions(database_path, course_id, count)
        flash(f"Added {count} session slots.", "success")
        return course_redirect(course_id)

    @app.post("/courses/<int:course_id>/sailors")
    def add_sailor(course_id):
        require_office()
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

    @app.post("/courses/<int:course_id>/instructors")
    def assign_instructor(course_id):
        require_office()
        course = get_course(course_id)
        name = request.form.get("name", "").strip()
        if not name or len(name) > 100:
            flash("Enter an instructor name of 1 to 100 characters.", "error")
            return course_redirect(course_id)
        instructor = add_instructor_to_course(database_path, name, course_id)
        if instructor["added"]:
            flash(f"Assigned {instructor['name']} to {course['name']}.", "success")
        else:
            flash(f"{instructor['name']} is already assigned to {course['name']}.", "error")
        return course_redirect(course_id)

    @app.post("/courses/<int:course_id>/sailors/<int:sailor_id>/delete")
    def remove_sailor(course_id, sailor_id):
        require_office()
        course = get_course(course_id)
        sailor = get_sailor(course_id, sailor_id)
        if request.form.get("confirm") != "delete":
            abort(400, description="Confirm sailor deletion to continue.")
        delete_sailor(database_path, sailor_id)
        flash(
            f"Deleted {sailor['name']} and their records from all courses, including notes.",
            "success",
        )
        return course_redirect(course_id)

    @app.post("/courses/<int:course_id>/sailors/<int:sailor_id>/criteria")
    def update_sailor_criterion(course_id, sailor_id):
        require_assigned_instructor(course_id)
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
        refresh_stage_certificates(course)

        flash("Progress updated.", "success")
        return redirect(
            url_for(
                "course_detail",
                course_id=course_id,
                sailor_id=sailor["id"],
                _anchor=f"criterion-{get_criteria(course).index(criterion)}",
            )
        )

    @app.post("/courses/<int:course_id>/sailors/<int:sailor_id>/progress")
    def update_sailor_progress(course_id, sailor_id):
        require_assigned_instructor(course_id)
        course = get_course(course_id)
        get_syllabus_for_course(course)
        sailor = get_sailor(course_id, sailor_id)
        criteria = get_criteria(course)
        completed = request.form.get("completed") == "1"
        updated = update_criteria(
            database_path, course_id, criteria, completed, sailor_id
        )

        if updated:
            refresh_stage_certificates(course)
            state = "completed" if completed else "cleared"
            flash(f"All criteria {state} for {sailor['name']}.", "success")
        else:
            flash(f"There are no criteria to update for {sailor['name']}.", "error")

        return course_redirect(course_id, sailor["id"])

    @app.post("/courses/<int:course_id>/criteria")
    def update_criterion_for_course(course_id):
        require_assigned_instructor(course_id)
        course = get_course(course_id)
        get_syllabus_for_course(course)
        criterion = request.form.get("criterion", "")
        if criterion not in get_criteria(course):
            abort(400, description="Unknown criterion.")

        completed = request.form.get("completed") == "1"
        updated = update_criteria(database_path, course_id, [criterion], completed)
        if updated:
            refresh_stage_certificates(course)
            state = "completed" if completed else "cleared"
            flash(f"Criterion {state} for all sailors in {course['name']}.", "success")
        else:
            flash("There are no enrolled sailors to update.", "error")
        selected_id = request.form.get("sailor_id", type=int)
        if selected_id is not None:
            get_sailor(course_id, selected_id)
        return course_redirect(course_id, selected_id)

    @app.post("/courses/<int:course_id>/categories")
    def update_category_for_course(course_id):
        require_assigned_instructor(course_id)
        course = get_course(course_id)
        get_syllabus_for_course(course)
        section_name = request.form.get("section", "")
        category_name = request.form.get("category", "")
        course_syllabus = get_syllabus_for_course(course)
        categories = course_syllabus.get(section_name, {})
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
        if updated:
            refresh_stage_certificates(course)
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
        view, actor_id = active_view()
        if view == "instructor":
            require_assigned_instructor(course_id)
        elif view != "office":
            abort(403)
        get_course(course_id)
        sailor = get_sailor(course_id, sailor_id)
        note = request.form.get("note", "").strip()

        if not note:
            flash("Write a note before saving.", "error")
        elif len(note) > 2000:
            flash("Notes must be 2,000 characters or fewer.", "error")
        else:
            created_at = datetime.now().astimezone().isoformat(timespec="minutes")
            add_note(
                database_path, sailor["name"], note, created_at,
                course_id=course_id,
                instructor_id=actor_id if view == "instructor" else None,
            )
            flash("Note added.", "success")

        return redirect(
            url_for("sailor_profile", sailor_id=sailor["id"], course_id=course_id)
        )

    return app


app = None if __name__ == "__main__" else create_app()


def seed_demo_database(database_path):
    """Create a small, repeatable showcase dataset in the isolated demo DB."""
    if get_courses(database_path, include_archived=True):
        return
    stage = next(iter(syllabus_data), None)
    if stage is None:
        return
    criteria = [criterion for categories in syllabus_data[stage].values()
                for skills in categories.values() for criterion in skills]
    completed_id = create_course_setup(
        database_path, "Demo · Completed course", stage, criteria,
        ["Alex Morgan", "Jamie Lee"], [], ["Taylor Reed", "Casey Quinn"], ["2026-06-06", "2026-06-13"], syllabus_data[stage],
    )
    active_id = create_course_setup(
        database_path, "Demo · In progress", stage, criteria,
        ["Alex Morgan"], [], ["Taylor Reed", "Jordan Blake"], ["2026-07-04", "2026-07-11", ""], syllabus_data[stage],
    )
    if not completed_id or not active_id:
        return
    update_criteria(database_path, completed_id, criteria, True)
    sync_stage_certificate_requests(
        database_path, completed_id, stage, criteria,
        datetime.now().astimezone().isoformat(timespec="minutes"),
    )
    # Issue the completed course certificate so the demo includes an earned award.
    from database import get_pending_certificates
    pending = [item for item in get_pending_certificates(database_path)
               if item["course_name"] == "Demo · Completed course"]
    for certificate in pending:
        save_certificate_feedback(
            database_path, completed_id, certificate["id"], "guided",
            "You should be proud of your boat handling. Your persistence really helped on the water. "
            "Your next tip is to plan tacks ahead. Between sessions, practise tying sailing knots.",
            "boat handling", "persistence", "plan tacks ahead", "tying sailing knots",
        )
        issue_certificate(database_path, certificate["id"], date.today().isoformat())
    completed_at = datetime.now().astimezone().isoformat(timespec="minutes")
    set_course_archived(database_path, completed_id, completed_at)
    active_pupils = get_sailors_for_course(database_path, active_id)
    if active_pupils:
        update_criteria(database_path, active_id, criteria, True, active_pupils[0]["id"])
        sync_stage_certificate_requests(
            database_path, active_id, stage, criteria, completed_at,
        )
    add_sailor_award(database_path, get_sailors(database_path)[0]["id"], "Demo Regatta Crew Award", date.today().isoformat())
    from database import get_sessions_for_course, save_course_session
    session_item = get_sessions_for_course(database_path, active_id)[0]
    selected = criteria[:min(3, len(criteria))]
    save_course_session(
        database_path, active_id, session_item["id"], "2026-07-04",
        "Rigging checks, boat handling warm-up, and short upwind practice.", selected,
        "The group made a confident start and communicated well on the water.",
        "Allow more time for individual tacking practice.", True,
    )
    instructors = get_instructors_for_course(database_path, active_id)
    add_note(database_path, "Taylor Reed", "Confident with boat preparation; keep practising close-hauled sailing.",
             datetime.now().astimezone().isoformat(timespec="minutes"), active_id,
             instructors[0]["id"] if instructors else None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Sailing Progress Tracker.")
    parser.add_argument("--demo", action="store_true", help="Use an isolated, seeded demo database.")
    parser.add_argument("--host", help="Bind address (use 0.0.0.0 for LAN access).")
    parser.add_argument("--port", type=int, help="Port to serve on.")
    args = parser.parse_args()
    if args.demo:
        demo_database = Path(__file__).resolve().parent / "instance" / "scapp-demo.sqlite3"
        demo_app = create_app(database_path=demo_database)
        seed_demo_database(demo_database)
        demo_app.run(host=args.host or "0.0.0.0", port=args.port or 5001, debug=False)
    else:
        app = create_app()
        app.run(host=args.host or "127.0.0.1", port=args.port or 5000, debug=False)
