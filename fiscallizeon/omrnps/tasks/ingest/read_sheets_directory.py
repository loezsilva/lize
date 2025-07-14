from celery import states

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from fiscallizeon.celery import app
from fiscallizeon.omr.functions.main import process_file
from fiscallizeon.omrnps.models import OMRNPSUpload, OMRNPSCategory, OMRNPSPage, ClassApplication, TeacherAnswer, \
    TeacherOrder, NPSApplicationAxis, UnityAnswer, OMRNPSError


def create_answers(answer):
    questions_count = 0
    teachers_order = TeacherOrder.objects.using('default').filter(class_application=answer['class_application'])
    application_axis = NPSApplicationAxis.objects.using('default').filter(nps_application=answer['class_application'].nps_application)

    unity_checked_option = answer.get('u1', '')

    if len(unity_checked_option) == 1:
        try:
            unity_grade = int(unity_checked_option)

            if 0 <= unity_grade <= 10:
                UnityAnswer.objects.create(
                    class_application=answer['class_application'],
                    grade=unity_grade + 1,
                    omr_nps_page=answer['omr_nps_page'],
                )
        except Exception as e:
            answer['class_application'].nps_application.append_processing_log(
                f'Erro na leitura de nota de unidade - Pagina {answer["page_number"]}: {e}'
            )

    for teacher_index, teacher_order in enumerate(teachers_order):
        for axis_index, axis in enumerate(application_axis, 1):
            question_index = axis_index + teacher_index * 5
            checked_option = answer.get(f'q{question_index}', '')

            if not checked_option:
                continue

            if len(checked_option) == 1:
                try:
                    answer_index = 'ABCDE'.index(checked_option)
                    TeacherAnswer.objects.create(
                        teacher=teacher_order,
                        nps_application_axis=axis,
                        grade=answer_index + 1,
                        omr_nps_page=answer['omr_nps_page'],
                    )
                    questions_count += 1
                except Exception as e:
                    print("ERRO:", e)
                    continue

    return questions_count

@app.task(bind=True)
def read_sheets_directory(self, args):
    nps_upload_id, uploads_data = args

    omr_nps_upload = OMRNPSUpload.objects.using('default').get(pk=nps_upload_id)
    
    for i, sheet in enumerate(uploads_data, 1):
        nps_omr_category = OMRNPSCategory.objects.get(sequential=sheet['sequential'])
        page_number = sheet.get('page_number', 0)
        class_application_pk = sheet['object_id']

        class_application = ClassApplication.objects.filter(
            pk=class_application_pk
        ).order_by('created_at').first()

        if class_application:
            try:
                omr_nps_page = OMRNPSPage.objects.create(
                    upload=omr_nps_upload,
                    class_application=class_application,
                    scan_image=UploadedFile(
                        file=open(sheet['file_path'], 'rb')
                    ),
                )

                omr_marker = nps_omr_category.get_omr_marker_path()
                json_obj = nps_omr_category.get_template_json(class_application.nps_application)
                answer = process_file(sheet['file_path'], json_obj, omr_marker)

                answer['class_application'] = class_application
                answer['page_number'] = sheet['page_number']
                answer['omr_nps_page'] = omr_nps_page
                answers_count = create_answers(answer)

                omr_nps_page.successful_answers_count = answers_count
                omr_nps_page.save()

                if error_id := sheet.get('omr_nps_error', None):
                    OMRNPSError.objects.filter(pk=error_id).update(is_solved=True)
                
                if settings.DEBUG:
                    print(f'Answer | ClassApplication {class_application_pk}:')
                    print(answer)
            except Exception as e:
                omr_nps_upload.append_processing_log(f'Erro na leitura da página {page_number} - {e}')
                continue

            self.update_state(state=states.STARTED, meta={'done': i, 'total': omr_nps_upload.total_pages})

        else:
            OMRNPSError.objects.create(
                upload=omr_nps_upload,
                error_image=UploadedFile(
                    file=open(sheet['file_path'], 'rb')
                ),
                category=OMRNPSError.CLASS_NOT_FOUND,
                page_number=i,
            )
            continue

    self.update_state(state=states.SUCCESS, meta={'done': omr_nps_upload.total_pages, 'total': omr_nps_upload.total_pages})
    return nps_upload_id
