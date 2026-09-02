class User:
    def __init__(self, name):
        self.name = name

class Office(User):
    def __init__(self, name):
        super().__init__(name)
        self.courses = [] # courses the office is managing
        self.users = [] # users the office is managing
        self.Certificates = [] # certificates the office has in stock
        #work on certificate pending and issued
    def CreateCourse(self, name):
        return Course(name)
    
class SI(User):
    def __init__(self, name):
        super().__init__(name)
        self.courses = [] # courses the SI is assigned to
class DI(User):
    def __init__(self, name):
        super().__init__(name)
        self.courses = [] # courses the DI is assigned to
        self.feedback = [] # feedback from SIs 

class Sailor():
    def __init__(self, name):
        self.name = name # name
        self.progress = {} # progress in course incase uncompleted at finish
        self.courses = [] # courses the sailor is enrolled in
        self.feedback = [] # feedback from SIs and DIs
        self.certificates = [] # certificates earned by the sailor/ Stages completed
        self.medical = [] # medical information for the sailor

class Course:
    def __init__(self, name):
        self.name = name
        self.lead_instructor = None
        self.dates = []
        self.sailors = []
        self.SIs = []
        self.DIs = []
        self.criteria = []
        self.progress = []

    def add_sailor(self, sailor):
        self.sailors.append(sailor)
        sailor.courses.append(self)
        return f"Sailor {sailor} added to course {self.name}"
    
    def add_SI(self, SI):
        self.SIs.append(SI)
        SI.courses.append(self)
        return f"SI {SI} added to course {self.name}"
    
    def add_DI(self, DI):
        self.DIs.append(DI)
        DI.courses.append(self)
        return f"DI {DI} added to course {self.name}"

    def add_criteria(self, criteria):
        self.criteria.append(criteria)
        return f"Criteria {criteria} added to course {self.name}"

    def get_course_info(self):
        return {
            "name": self.name,
            "sailors": [sailor.name for sailor in self.sailors],
            "SIs": [SI.name for SI in self.SIs],
            "DIs": [DI.name for DI in self.DIs],
            "criteria": self.criteria
        }

    def update_criteria(self, sailor, criterion, achieved):
        for entry in self.progress:
            if entry["sailor"] == sailor:
                if criterion in entry["criteria"]:
                    entry["criteria"][criterion] = achieved
                    return f"Criteria {criterion} for sailor {sailor} updated to {achieved}"
                else:
                    return f"Criterion {criterion} not found for sailor {sailor}"
        return f"Sailor {sailor} not found in course"

    def build_course(self):
        for sailor in self.sailors:
            self.progress.append({
                "sailor": sailor,
                "criteria":{ 
                    criterion: False 
                    for criterion in self.criteria
                            }
                })

    def show_sailor_progress(self, sailor):
        for entry in self.progress:
            if entry["sailor"] == sailor:
                
                criteria = entry["criteria"]
                achieved = sum(criteria.values())
                total = len(criteria)

                print(f"\n{sailor.name} - {self.name}")
                print("-" * 30)

                for criterion, completed in criteria.items():
                    if completed:
                        print(f"✓ {criterion}")
                    else:
                        print(f"○ {criterion}")

                print("-" * 30)
                print(f"Progress: {achieved}/{total} ({achieved / total * 100:.0f}%)")
                return

        print(f"Sailor {sailor} not found")

    def build_ticklist(self):
        print(self.name)
        print("=" * (25 + len(self.sailors) * 10))
        print(f"{"Criteria":<25}", end="")
        for sailor in self.sailors:
            print(f"{sailor.name:^10}", end="")

        print()
        print("-" * (25 + len(self.sailors) * 10))
        for criterion in self.criteria:
            print(f"{criterion:<25}", end="")

            for sailor in self.sailors:

                for progress in self.progress:
                    if progress["sailor"] == sailor:
                        completed = progress["criteria"][criterion]

                        if completed:
                            # print tick
                            print(f"{'✓':^10}", end="")
                        else:
                            # print circle
                            print(f"{'○':^10}", end="") 

            print()
        print("-" * (25 + len(self.sailors) * 10))
        print(f"{"Progress":<25}", end="")
        for sailor in self.sailors:
            for progress in self.progress:
                if progress["sailor"] == sailor:
                    achieved = sum(progress["criteria"].values())
                    total = len(progress["criteria"])
                    percentage = f"{achieved / total * 100:.0f}%"
                    print(percentage.center(10), end="")

    def set_lead_instructor(self, lead_instructor):
        self.lead_instructor = lead_instructor
        return f"Lead instructor {lead_instructor.name} set for course {self.name}"


ollie = Sailor("Ollie")
ollie2 = Sailor("Ollie2")
ben = Sailor("Ben")
stage1 = Course("Stage 1")
stage1.add_sailor(ollie)
stage1.add_sailor(ollie2)
stage1.add_sailor(ben)
will = SI("Will")
stage1.add_SI(will)
john = DI("John")
stage1.set_lead_instructor(will)
stage1.add_DI(john)
stage1.add_criteria("Criteria 1")
stage1.add_criteria("Criteria 2")
stage1.add_criteria("Criteria 3")
stage1.get_course_info()
stage1.build_course()
stage1.update_criteria(ollie, "Criteria 2", True)
stage1.update_criteria(ben, "Criteria 3", True)
stage1.update_criteria(ollie, "Criteria 1", True)
#stage1.show_sailor_progress(ollie)
stage1.build_ticklist()

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