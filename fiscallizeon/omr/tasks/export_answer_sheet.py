import os

from celery import chord, states

from fiscallizeon.applications.models import Application, ApplicationRandomizationVersion
from fiscallizeon.omr.tasks.export_application_student_answer_sheet import export_application_student_answer_sheet
from fiscallizeon.omr.tasks.export_application_student_discursive_sheet import export_application_student_discursive_sheet
from fiscallizeon.omr.tasks.export_application_student_essay_sheet import export_application_student_essay_sheet
from fiscallizeon.omr.tasks.export_application_draft_essay_sheet import export_application_draft_essay_sheet
from fiscallizeon.applications.tasks.export_exam_application_student import export_exam_application_student
from fiscallizeon.omr.tasks.export_school_class_attendance_list import export_school_class_attendance_list
from fiscallizeon.omr.tasks.group_answer_sheet_files import group_answer_sheet_files
from fiscallizeon.omr.mockup_utils import print_mockup_answer_sheet, print_mockup_discursive_sheet, print_mockup_exam, print_mockup_essay_sheet
from fiscallizeon.applications.randomization import randomize_application
from fiscallizeon.exams.tasks import export_custom_page_application_student, export_custom_page_school_classes
from fiscallizeon.exams.models import ClientCustomPage
from fiscallizeon.celery import app
from fiscallizeon.applications.models import Application
from fiscallizeon.questions.models import Question


@app.task
def error_handle(request, *args, **kwargs):
    application = Application.objects.filter(pk=request.args[0])
    application.update(sheet_exporting_status=Application.ERROR)

    app.backend.store_result(
        task_id=f'EXPORT_SHEETS_{request.args[0]}_{request.args[1]}',
        result=None,
        state=states.FAILURE,
    )

    app.backend.store_result(
        task_id=f'GROUP_FILES_APPLICATION_{request.args[0]}_{request.args[1]}',
        result=None,
        state=states.FAILURE,
    )

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
        print_mockup_exam(application, target_directory, exam_params, application_randomization_version)

    
@app.task(bind=True)
def export_answer_sheet(
        self, application_pk, sheet_model=None, export_version=0, blank_pages=False,
        include_exams=False, include_discursives=False, exam_params={}, discursive_params={}, custom_pages_pks=[]):

    self.update_state(state='PROGRESS')

    application = Application.objects.using('default').get(pk=application_pk)
    assets_tasks = []
    target_directory = os.path.join(
        'omr', 'exports', application_pk, str(export_version)
    )

    if application.exam.is_randomized and include_exams:
        application_students_list = randomize_application(application)

        application_randomization_versions = ApplicationRandomizationVersion.objects.get_last_versions(
            application=application
        )
        for application_randomization_version in application_randomization_versions:
            print_mockups(application, target_directory, sheet_model, include_discursives, 
                          discursive_params, include_exams, exam_params, 
                          application_randomization_version)
    else:
        application_students_list = list(application.applicationstudent_set.all().order_by("student__name").values('pk'))
        print_mockups(application, target_directory, sheet_model, include_discursives, 
                      discursive_params, include_exams, exam_params)
    
    custom_pages = ClientCustomPage.objects.filter(
        pk__in=custom_pages_pks
    ).order_by('id')
    
    custom_pages_objective = [str(custom_page.id) for custom_page in custom_pages.filter(location__in=[ClientCustomPage.OBJECTIVE_ANSWER_SHEET])]
    custom_pages_discursive = [str(custom_page.id) for custom_page in custom_pages.filter(location__in=[ClientCustomPage.DISCURSIVE_ANSWER_SHEET])]
    custom_pages_student_exam = [str(custom_page.id) for custom_page in custom_pages.filter(location__in=[ClientCustomPage.STUDENT_EXAM])]
    custom_pages_after_student_exam = [str(custom_page.id) for custom_page in custom_pages.filter(location__in=[ClientCustomPage.AFTER_STUDENT_EXAM])]
    custom_pages_school_classes = [str(custom_page.id) for custom_page in custom_pages.filter(location__in=[ClientCustomPage.SIGNATURE_SHEET])]

    for application_student in application_students_list:
        if sheet_model and (application.exam.has_choice_questions or application.exam.has_sum_questions):
            assets_tasks.append(
                export_application_student_answer_sheet.s(
                        application_student['pk'], target_directory, sheet_model, blank_pages, application_student.get('application_randomization_version', None)
                    )
            )

            if custom_pages_objective:
                assets_tasks.append(
                    export_custom_page_application_student.s(
                        application_student['pk'], target_directory, blank_pages, custom_pages_objective
                    )
                )

        exam_has_discursive_without_essay = application.exam.get_discursive_questions().filter(
            is_essay=False
        )

        if include_discursives and application.exam.has_discursive_questions:
            if exam_has_discursive_without_essay:
                assets_tasks.append(
                    export_application_student_discursive_sheet.s(
                        application_student['pk'], target_directory, blank_pages, application_student.get('application_randomization_version', None)
                    )
                )

            if application.exam.has_essay_questions:
                assets_tasks.append(
                    export_application_student_essay_sheet.s(
                        application_student['pk'], target_directory, blank_pages, application_student.get('application_randomization_version', None)
                    )
                )

            if custom_pages_discursive:
                assets_tasks.append(
                    export_custom_page_application_student.s(
                        application_student['pk'], target_directory, blank_pages, custom_pages_discursive
                    )
                )
                
        if include_exams:
            assets_tasks.append(
                export_exam_application_student.s(
                    application_student['pk'], target_directory, exam_params, blank_pages, application_student.get('application_randomization_version', None)
                )
            )
            if custom_pages_student_exam:
                assets_tasks.append(
                    export_custom_page_application_student.s(
                        application_student['pk'], target_directory, blank_pages, custom_pages_student_exam
                    )
                )

            if custom_pages_after_student_exam:
                assets_tasks.append(
                    export_custom_page_application_student.s(
                        application_student['pk'], target_directory, blank_pages, custom_pages_after_student_exam
                    )
                )

    school_classes = application.get_related_classes()
    
    for school_class in school_classes:
        assets_tasks.append(
            export_school_class_attendance_list.s(
                application_pk, school_class.pk, target_directory, blank_pages
            )
        )
        if custom_pages_school_classes:
            assets_tasks.append(
                export_custom_page_school_classes.s(
                    school_class.pk, target_directory, blank_pages, custom_pages_school_classes, application_pk
                )
            )

    if include_discursives and application.exam.has_essay_questions:
        assets_tasks.append(
            export_application_draft_essay_sheet.s(
                application.pk, target_directory, blank_pages
            )
        )

    result = chord(
        assets_tasks
    )(
        group_answer_sheet_files.si(
            application_pk, export_version, include_exams, include_discursives, custom_pages_pks, sheet_model, blank_pages
        ).set(
            task_id=f'GROUP_FILES_APPLICATION_{application.pk}_{export_version}'
        ).on_error(
            error_handle.s()
        )
    )

    return result