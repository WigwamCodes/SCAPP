from scapp import Course, Sailor, syllabus_data


def main():
    ollie = Sailor("Ollie")
    ollie2 = Sailor("Ollie2")
    course = Course("Stage 1", syllabus_data)
    course.add_sailor(ollie)
    course.add_sailor(ollie2)

    course.update_criterion(ollie, "Can assist with rigging the boat", True)
    course.update_criterion(ollie2, "Can assist with rigging the boat", False)
    course.print_sailor_progress(ollie)
    course.build_ticklist()


if __name__ == "__main__":
    main()
