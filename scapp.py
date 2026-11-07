import json
from pathlib import Path


def load_syllabus():
    syllabus_path = Path(__file__).with_name("syllabus.json")
    with syllabus_path.open(encoding="utf-8") as syllabus_file:
        return json.load(syllabus_file)


syllabus_data = load_syllabus()


class User:
    def __init__(self, name):
        self.name = name
        self.courses = []
        self.feedback = []

    def __str__(self):
        return self.name

    def leave_feedback(self, person, note):
        person.feedback.append(f"[{self.name}]: {note}")


class Office(User):
    def __init__(self, name):
        super().__init__(name)
        self.users = []
        self.Certificates = []

    def CreateCourse(self, name, syllabus=None):
        return Course(name, syllabus_data if syllabus is None else syllabus)

    def issue_certificate(self, sailor, name):
        cert = f"Certificate '{name}' - {sailor.name} - DATE HERE"
        sailor.certificates.append(cert)
        return f" Issued {cert}"


class SI(User):
    pass


class DI(User):
    pass


class Sailor(User):
    def __init__(self, name):
        super().__init__(name)
        self.progress = {}
        self.courses = []
        self.certificates = []
        self.medical = []
        self.notes = []

    def initialise_stage(self, stage_name, syllabus):
        stage_progress = self.progress.setdefault(stage_name, {})
        for categories in syllabus.get(stage_name, {}).values():
            for criteria_list in categories.values():
                for criterion in criteria_list:
                    stage_progress.setdefault(criterion, False)

    def add_note(self, note, created_at):
        entry = {"text": note, "created_at": created_at}
        self.notes.append(entry)
        return entry

    def is_stage_completed(self, stage_name):
        stage_ticks = self.progress.get(stage_name, {})
        return bool(stage_ticks) and all(stage_ticks.values())


class Course:
    def __init__(self, name, syllabus):
        self.name = name
        self.syllabus = syllabus
        self.lead_instructor = None
        self.dates = []
        self.sailors = []
        self.SIs = []
        self.DIs = []
        self.progress = []

    def add_sailor(self, sailor):
        if sailor not in self.sailors:
            self.sailors.append(sailor)
        sailor.initialise_stage(self.name, self.syllabus)
        if self not in sailor.courses:
            sailor.courses.append(self)
        return f"Sailor {sailor.name} added to course {self.name}"

    def add_SI(self, SI):
        if SI not in self.SIs:
            self.SIs.append(SI)
        if self not in SI.courses:
            SI.courses.append(self)
        return f"SI {SI.name} added to course {self.name}"

    def add_DI(self, DI):
        if DI not in self.DIs:
            self.DIs.append(DI)
        if self not in DI.courses:
            DI.courses.append(self)
        return f"DI {DI.name} added to course {self.name}"

    def get_course_info(self):
        criteria = [
            criterion
            for categories in self.syllabus.get(self.name, {}).values()
            for criteria_list in categories.values()
            for criterion in criteria_list
        ]
        return {
            "name": self.name,
            "sailors": [sailor.name for sailor in self.sailors],
            "SIs": [instructor.name for instructor in self.SIs],
            "DIs": [instructor.name for instructor in self.DIs],
            "criteria": criteria,
        }

    def update_criterion(self, sailor, criterion, status: bool):
        if self.name not in sailor.progress:
            return f"Sailor {sailor.name} is not enrolled in course {self.name}"

        if criterion in sailor.progress[self.name]:
            sailor.progress[self.name][criterion] = status

            icon = "✓" if status else "○"
            action = "Ticked" if status else "Unticked"
            print(f"[{icon}] {action} for {sailor.name}: '{criterion}'")
            if status and sailor.is_stage_completed(self.name):
                print(
                    f"\n📢 [OFFICE NOTIFICATION] {sailor.name} has completed ALL criteria for {self.name}!\n"
                )
        else:
            print(f"⚠️ Criterion '{criterion}' not found in {self.name}.")

    def print_sailor_progress(self, sailor):
        if self.name not in sailor.progress:
            print(f"{sailor.name} is not enrolled in {self.name}.")
            return

        print("\n==========================================")
        print(f" PROGRESS REPORT: {sailor.name} ({self.name})")
        print("==========================================")

        stage_syllabus = self.syllabus.get(self.name, {})
        sailor_ticks = sailor.progress[self.name]

        for section_name, categories in stage_syllabus.items():
            print(f"\n══ {section_name.upper()} ══")
            for category_name, criteria_list in categories.items():
                print(f"  [{category_name}]")
                for criterion in criteria_list:
                    status = "✓" if sailor_ticks.get(criterion, False) else "○"
                    print(f"    {status} {criterion}")

        achieved = sum(sailor_ticks.values())
        total = len(sailor_ticks)
        pct = (achieved / total * 100) if total > 0 else 0
        print("\n------------------------------------------")
        print(f" Total Progress: {achieved}/{total} ({pct:.0f}%)")
        print("------------------------------------------\n")

    def set_lead_instructor(self, lead_instructor):
        self.lead_instructor = lead_instructor
        return f"Lead instructor {lead_instructor.name} set for course {self.name}"

    def build_ticklist(self):
        all_criteria = [
            criterion
            for categories in self.syllabus.get(self.name, {}).values()
            for criteria_list in categories.values()
            for criterion in criteria_list
        ]

        max_len = max((len(criterion) for criterion in all_criteria), default=25)
        two_line_mode = max_len > 100
        col_width = max(25, (max_len + 1) // 2 if two_line_mode else max_len)
        width = col_width + len(self.sailors) * 12
        print(f"\n{self.name} Ticklist")
        print("=" * width)

        print(f"{'Criteria':<{col_width}}", end="")
        for sailor in self.sailors:
            print(f"{sailor.name:^12}", end="")
        print(f"\n{'-' * width}")

        for criterion in all_criteria:
            if not two_line_mode or len(criterion) <= col_width:
                print(f"{criterion:<{col_width}}", end="")
                for sailor in self.sailors:
                    completed = sailor.progress.get(self.name, {}).get(
                        criterion, False
                    )
                    mark = "✓" if completed else "○"
                    print(f"{mark:^12}", end="")
                print()
                continue

            split_pos = criterion.rfind(" ", 0, col_width)
            if split_pos == -1:
                split_pos = col_width
            part1 = criterion[:split_pos]
            part2 = criterion[split_pos:].lstrip()
            if len(part2) > col_width:
                part2 = part2[: max(0, col_width - 3)] + "..."

            print(f"{part1:<{col_width}}", end="")
            for sailor in self.sailors:
                completed = sailor.progress.get(self.name, {}).get(
                    criterion, False
                )
                mark = "✓" if completed else "○"
                print(f"{mark:^12}", end="")
            print()
            print(f"{part2:<{col_width}}", end="")
            for _ in self.sailors:
                print(f"{'':^12}", end="")
            print()

        print("-" * width)
