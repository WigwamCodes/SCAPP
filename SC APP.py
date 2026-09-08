import json as js

syllabus_data = js.load(open("syllabus.json"))

class User:
    def __init__(self, name):
        self.name = name
        self.courses = []  # courses the user is assigned to
        self.feedback = [] 

    def __str__(self):
        return self.name

    def leave_feedback(self, person, note):
        person.feedback.append(f"[{self.name}]: {note}")

class Office(User):
    def __init__(self, name):
        super().__init__(name) 
        
        self.users = [] # users the office is managing
        self.Certificates = [] # certificates the office has in stock
        #work on certificate pending and issued
    def CreateCourse(self, name):
        return Course(name)

    def issue_certificate(self, sailor, name):
        cert = f"Certificate '{name}' - {sailor.name} - DATE HERE"
        sailor.certificates.append(cert)
        return f" Issued {cert}"
    
class SI(User):
    def __init__(self, name):
        super().__init__(name)


        
class DI(User):
    def __init__(self, name):
        super().__init__(name)

class Sailor(User):
    def __init__(self, name):
        super().__init__(name)
        self.progress = {} # progress in course incase uncompleted at finish
        self.courses = [] # courses the sailor is enrolled in
        self.certificates = [] # certificates earned by the sailor/ Stages completed
        self.medical = [] # medical information for the sailor

    def initialise_stage(self, stage_name, syllabus):
        if stage_name not in self.progress:
            self.progress[stage_name] = {}

        if stage_name in syllabus:
            for section,categories in syllabus[stage_name].items():
                for category, criteria_list in categories.items():
                    for criterion in criteria_list:
                        if criterion not in self.progress[stage_name]:
                            self.progress[stage_name][criterion] = False

    def is_stage_completed(self, stage_name):
        if stage_name not in self.progress:
            return False
        stage_ticks = self.progress[stage_name]
        return len(stage_ticks) > 0 and all(stage_ticks.values())

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
        self.sailors.append(sailor)
        sailor.initialise_stage(self.name, self.syllabus)
        sailor.courses.append(self)
        return f"Sailor {sailor.name} added to course {self.name}"
    
    def add_SI(self, SI):
        self.SIs.append(SI)
        SI.courses.append(self)
        return f"SI {SI.name} added to course {self.name}"
    
    def add_DI(self, DI):
        self.DIs.append(DI)
        DI.courses.append(self)
        return f"DI {DI.name} added to course {self.name}"

    def get_course_info(self):
        return {
            "name": self.name,
            "sailors": [sailor.name for sailor in self.sailors],
            "SIs": [SI.name for SI in self.SIs],
            "DIs": [DI.name for DI in self.DIs],
            "criteria": self.criteria
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
                print(f"\n📢 [OFFICE NOTIFICATION] {sailor.name} has completed ALL criteria for {self.name}!\n")
        else:
            print(f"⚠️ Criterion '{criterion}' not found in {self.name}.")
        

    def print_sailor_progress(self, sailor):
        if self.name not in sailor.progress:
            print(f"{sailor.name} is not enrolled in {self.name}.")
            return

        print(f"\n==========================================")
        print(f" PROGRESS REPORT: {sailor.name} ({self.name})")
        print(f"==========================================")

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
        print(f"\n------------------------------------------")
        print(f" Total Progress: {achieved}/{total} ({pct:.0f}%)")
        print(f"------------------------------------------\n")



    def set_lead_instructor(self, lead_instructor):
        self.lead_instructor = lead_instructor
        return f"Lead instructor {lead_instructor.name} set for course {self.name}"

    def build_ticklist(self):
        # Gather all criteria to determine appropriate column width
        all_criteria = []
        for section, categories in self.syllabus[self.name].items():
            for category, criteria_list in categories.items():
                all_criteria.extend(criteria_list)

        if all_criteria:
            max_len = max(len(c) for c in all_criteria)
        else:
            max_len = 25

        # If the longest criterion is >250 chars, render it across two lines
        two_line_mode = max_len > 100

        # Column width: use longest criterion (or half when two-line mode)
        if two_line_mode:
            col_width = max(25, (max_len + 1) // 2)
        else:
            col_width = max(25, max_len)

        width = col_width + len(self.sailors) * 12
        print(f"\n{self.name} Ticklist")
        print("=" * width)

        # Header
        print(f"{'Criteria':<{col_width}}", end="")
        for sailor in self.sailors:
            print(f"{sailor.name:^12}", end="")
        print(f"\n{'-' * width}")

        # Loop through the 3 levels of JSON syllabus
        for section, categories in self.syllabus[self.name].items():
            for category, criteria_list in categories.items():
                for criterion in criteria_list:
                    if not two_line_mode or len(criterion) <= col_width:
                        # Single-line display
                        print(f"{criterion:<{col_width}}", end="")

                        for sailor in self.sailors:
                            completed = sailor.progress.get(self.name, {}).get(criterion, False)
                            mark = "✓" if completed else "○"
                            print(f"{mark:^12}", end="")
                        print()
                    else:
                        # Two-line display: split on last space within col_width to avoid mid-word breaks
                        split_pos = criterion.rfind(' ', 0, col_width)
                        if split_pos == -1:
                            split_pos = col_width
                        part1 = criterion[:split_pos]
                        part2 = criterion[split_pos:].lstrip()

                        # If remainder is still too long, truncate with ellipsis
                        if len(part2) > col_width:
                            part2 = part2[:max(0, col_width - 3)] + '...'

                        # First line with marks
                        print(f"{part1:<{col_width}}", end="")
                        for sailor in self.sailors:
                            completed = sailor.progress.get(self.name, {}).get(criterion, False)
                            mark = "✓" if completed else "○"
                            print(f"{mark:^12}", end="")
                        print()

                        # Second line with the remainder of the text and blank mark columns
                        print(f"{part2:<{col_width}}", end="")
                        for _ in self.sailors:
                            print(f"{'':^12}", end="")
                        print()

        print("-" * width)


if __name__ == "__main__":
    ollie = Sailor("Ollie")
    ollie2 = Sailor("Ollie2")
    course = Course("Stage 1", syllabus_data)
    course.add_sailor(ollie)
    course.add_sailor(ollie2)

    # 1. Tick a criterion
    course.update_criterion(ollie, "Can assist with rigging the boat", True)

    # 2. Untick it (e.g. marked by mistake)
    course.update_criterion(ollie2, "Can assist with rigging the boat", False)

    # View progress
    course.print_sailor_progress(ollie)
    course.build_ticklist()

"""
Office creates course
assigns SIs and DIs
Then add sailors
adds the criteria
then build the course
Lead instructor updates sailors progress
any instructor can add feedback to sailors
SI gives feedback to DI
When sailor completes all criteria office is noified
certificate is prepared and issued to sailor and their record is updated
"""