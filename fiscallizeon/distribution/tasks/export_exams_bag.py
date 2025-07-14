import os

from celery import states, chord, group

from django.utils import timezone

from fiscallizeon.celery import app
from fiscallizeon.exams.models import ClientCustomPage
from fiscallizeon.distribution.models import RoomDistribution
from fiscallizeon.clients.models import SchoolCoordination, Unity
from fiscallizeon.distribution.tasks.group_files import group_files
from fiscallizeon.applications.randomization import randomize_application
from fiscallizeon.applications.models import ApplicationStudent, ApplicationRandomizationVersion
from fiscallizeon.omr.tasks.export_application_student_answer_sheet import export_application_student_answer_sheet
from fiscallizeon.omr.tasks.export_application_student_discursive_sheet import export_application_student_discursive_sheet
from fiscallizeon.omr.tasks.export_application_student_essay_sheet import export_application_student_essay_sheet
from fiscallizeon.omr.tasks.export_application_draft_essay_sheet import export_application_draft_essay_sheet
from fiscallizeon.omr.mockup_utils import print_mockup_answer_sheet, print_mockup_discursive_sheet, print_mockup_exam, print_mockup_essay_sheet
from fiscallizeon.distribution.tasks.export_room_attendance_list import export_room_attendance_list
from fiscallizeon.distribution.tasks.export_unity_yard_list import export_unity_yard_list
from fiscallizeon.applications.tasks.export_exam_application_student import export_exam_application_student
from fiscallizeon.exams.tasks import export_custom_page_application_student, export_custom_page_school_classes


def print_mockups(
        application, target_directory, sheet_model, include_discursives, discursive_params, include_exams, 
        exam_params, application_randomization_version=None):
    
    application.exam.clear_questions_numbers_cache()
    
    print_mockup_answer_sheet(application, target_directory, sheet_model, application_randomization_version)    
    if include_discursives and application.exam.has_discursive_questions:
        print_mockup_discursive_sheet(application, target_directory, discursive_params, application_randomization_version)

        if application.exam.has_essay_questions:
            print_mockup_essay_sheet(application, target_directory, application_randomization_version=application_randomization_version)
            print_mockup_essay_sheet(application, target_directory, is_draft=True)

    if include_exams:
        if not exam_params.get('use_custom_params', False):
            exam_params = application.exam.get_filters_to_print()
        print_mockup_exam(application, target_directory, exam_params, application_randomization_version)


@app.task(bind=True)
def export_exams_bag(
                    self, room_distribution_pk, include_exams=False, sheet_model=None, blank_pages=False, 
                    export_version=0, include_discursives=False, exam_params={}, discursive_params={}, custom_pages_pks=[]):
    self.update_state(state=states.STARTED)

    room_distribution = RoomDistribution.objects.get(pk=room_distribution_pk)
    distribution_path = os.path.join('ensalamentos', 'tmp', str(room_distribution.pk), str(export_version))

    custom_pages = ClientCustomPage.objects.filter(
        pk__in=custom_pages_pks
    ).order_by('id')
    
    custom_pages_objective = [str(custom_page.id) for custom_page in custom_pages.filter(location__in=[ClientCustomPage.OBJECTIVE_ANSWER_SHEET])]
    custom_pages_discursive = [str(custom_page.id) for custom_page in custom_pages.filter(location__in=[ClientCustomPage.DISCURSIVE_ANSWER_SHEET])]
    custom_pages_student_exam = [str(custom_page.id) for custom_page in custom_pages.filter(location__in=[ClientCustomPage.STUDENT_EXAM])]
    custom_pages_after_student_exam = [str(custom_page.id) for custom_page in custom_pages.filter(location__in=[ClientCustomPage.AFTER_STUDENT_EXAM])]
    custom_pages_school_classes = [str(custom_page.id) for custom_page in custom_pages.filter(location__in=[ClientCustomPage.SIGNATURE_SHEET])]

    assets_tasks = []
    for application in room_distribution.application_set.all():
        if application.exam.is_randomized and include_exams:
            application_students_list = randomize_application(application)
            application_randomization_versions = ApplicationRandomizationVersion.objects.get_last_versions(
                application=application
            )
            for application_randomization_version in application_randomization_versions:
                print_mockups(
                    application, distribution_path, sheet_model, 
                    include_discursives, discursive_params, 
                    include_exams, exam_params, application_randomization_version)
        else:
            application_students_list = list(application.applicationstudent_set.all().values('pk'))
            print_mockups(application, distribution_path, sheet_model, include_discursives, discursive_params, include_exams, exam_params)


        for student in application_students_list:
            application_student = ApplicationStudent.objects.get(pk=student['pk'])

            if application_student.application.exam.has_choice_questions:
                assets_tasks.append(
                    export_application_student_answer_sheet.s(
                        student['pk'], distribution_path, sheet_model, blank_pages, student.get('application_randomization_version', 0)
                    )
                )

                if custom_pages_objective:
                    assets_tasks.append(
                        export_custom_page_application_student.s(
                            student['pk'], distribution_path, blank_pages, custom_pages_objective
                        )
                    )
                
            if include_discursives and application_student.application.exam.has_discursive_questions:
                exam_has_discursive_without_essay = application.exam.get_discursive_questions().filter(
                    is_essay=False
                )

                if exam_has_discursive_without_essay:
                    assets_tasks.append(
                        export_application_student_discursive_sheet.s(
                            student['pk'], distribution_path, blank_pages, student.get('application_randomization_version', None)
                        )
                    )

                if application_student.application.exam.has_essay_questions:
                    assets_tasks.append(
                        export_application_student_essay_sheet.s(
                            student['pk'], distribution_path, blank_pages, student.get('application_randomization_version', None)
                        )
                    )

                if custom_pages_discursive:
                    assets_tasks.append(
                        export_custom_page_application_student.s(
                            student['pk'], distribution_path, blank_pages, custom_pages_discursive
                        )
                    )

            if include_exams:
                assets_tasks.append(
                    export_exam_application_student.s(
                        student['pk'], distribution_path, exam_params, blank_pages, student.get('application_randomization_version', 0)
                    )
                )

                if custom_pages_student_exam:
                    assets_tasks.append(
                        export_custom_page_application_student.s(
                            student['pk'], distribution_path, blank_pages, custom_pages_student_exam
                        )
                    )

                if custom_pages_after_student_exam:
                    assets_tasks.append(
                        export_custom_page_application_student.s(
                            student['pk'], distribution_path, blank_pages, custom_pages_after_student_exam
                        )
                    )

        rooms = room_distribution.get_rooms()
        for room in rooms:
            assets_tasks.append(
                export_room_attendance_list.s(
                    room_distribution_pk, room.pk, distribution_path, blank_pages
                )
            )

            if custom_pages_school_classes:
                assets_tasks.append(
                    export_custom_page_school_classes.s(
                        room.pk, distribution_path, blank_pages, custom_pages_school_classes
                    )
                )

        if include_discursives and application.exam.has_essay_questions:
            assets_tasks.append(
                export_application_draft_essay_sheet.s(
                    application.pk, distribution_path, blank_pages
                )
            )

        school_coordinations = SchoolCoordination.objects.filter(
            rooms__room_distribution__distribution=room_distribution
        ).distinct()

        # unities = Unity.objects.filter(coordinations__in=school_coordinations).distinct()

        # for unity in unities:
        #     assets_tasks.append(
        #         export_unity_yard_list.s(
        #             room_distribution_pk, unity.pk, distribution_path, blank_pages
        #         )
        #     )

        application.last_answer_sheet_generation = timezone.localtime(timezone.now())
        application.sheet_exporting_count += 1
        application.save()

    try:
        result = chord(
            assets_tasks
        )(
            group_files.si(room_distribution_pk, export_version, include_exams, include_discursives, custom_pages_pks)
        )

        self.update_state(state=states.SUCCESS)
        return result

    except Exception as e:
        self.update_state(state=states.FAILURE)
        print(e)