import os
import re
import uuid
import zipfile
import shutil

from PyPDF2 import PdfReader
from pikepdf import Pdf, Page, Rectangle

from celery import states
from django.utils import timezone
from django.conf import settings

from fiscallizeon.celery import app
from fiscallizeon.clients.models import Unity, SchoolCoordination, Client
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.exams.models import ClientCustomPage
from fiscallizeon.distribution.utils import merge_urls, get_file
from fiscallizeon.omr.utils import download_spaces_image
from unidecode import unidecode
from django.template.defaultfilters import slugify

def safe_string(string):
    string = re.sub(r'[\s]+|/', '_', string) # Remove espaços
    string = re.sub(r'[^a-zA-Z0-9_]+', '', string)
    return string

def write_file_on_zip(zip_file, file, save_path):
    read_pdf = PdfReader(file)
    
    with open(file, 'rb') as f:
        zip_file.writestr(save_path, f.read())

    return len(read_pdf.pages)

def merge_a5_files(url1, url2=None, blank=False):
    output_pdf = Pdf.new()
    output_pdf.add_blank_page(page_size=(842, 595))
    destination_page = Page(output_pdf.pages[0])
    
    pdf1_path = download_spaces_image(url1)
    pdf1 = Pdf.open(pdf1_path)
    gabarito1 = Page(pdf1.pages[0])
    destination_page.add_overlay(gabarito1, Rectangle(0, 0, 421, 595))
    os.remove(pdf1_path)

    if url2:
        pdf2_path = download_spaces_image(url2)
        pdf2 = Pdf.open(pdf2_path)
        gabarito2 = Page(pdf2.pages[0])
        destination_page.add_overlay(gabarito2, Rectangle(422, 0, 843, 595))
        os.remove(pdf2_path)
    
    if blank:
        output_pdf.add_blank_page(page_size=(842, 595))

    destination_path = os.path.join('/tmp', str(uuid.uuid4())[:8])
    output_pdf.save(destination_path)
    return destination_path


@app.task(bind=True)
def group_answer_sheet_files(self, application_pk, export_version=0, include_exams=False, include_discursives=False, custom_pages_pks=[], sheet_model=False, blank_pages=False):
    print(f'Grouping files for application {application_pk}')
    self.update_state(state=states.STARTED)
    application = Application.objects.get(pk=application_pk)
    
    exam_name = safe_string(application.exam.name)[:64]
    
    custom_pages = ClientCustomPage.objects.filter(
        pk__in=custom_pages_pks
    ).order_by('id')
    
    custom_pages_objective = [str(custom_page.id) for custom_page in custom_pages.filter(location__in=[ClientCustomPage.OBJECTIVE_ANSWER_SHEET])]
    custom_pages_discursive = [str(custom_page.id) for custom_page in custom_pages.filter(location__in=[ClientCustomPage.DISCURSIVE_ANSWER_SHEET])]
    custom_pages_student_exam = [str(custom_page.id) for custom_page in custom_pages.filter(location__in=[ClientCustomPage.STUDENT_EXAM])]
    custom_pages_school_classes = [str(custom_page.id) for custom_page in custom_pages.filter(location__in=[ClientCustomPage.SIGNATURE_SHEET])]

    export_tmp_path = os.path.join(
        os.sep, 'tmp', 'answer_sheets', application_pk, str(export_version)
    )
    
    os.makedirs(export_tmp_path, exist_ok=True)

    application = Application.objects.get(pk=application_pk)
    school_classes = application.get_related_classes()

    school_coordinations = SchoolCoordination.objects.filter(
        school_classes__in=school_classes.values('pk')
    ).distinct()

    unities = Unity.objects.filter(
        coordinations__in=school_coordinations
    ).distinct()
    
    total_bag_pages = 0
    
    client = Client.objects.get(pk=unities.first().client.pk)

    zip_filename = str(uuid.uuid4())[:8]
    
    zip_path = os.path.join(export_tmp_path, f'{zip_filename}_{exam_name}.zip')
    
    with zipfile.ZipFile(zip_path, "a", zipfile.ZIP_DEFLATED, allowZip64=True) as zip_file:
        base_remote_path = os.path.join(
            'omr', 'exports', application_pk, str(export_version)
        )
        fs = PrivateMediaStorage()

        def get_file_url(file):
            return fs.url(os.path.join(base_remote_path, file))
        
        #Lista para evitar que o mesmo aluno apareça duas vezes no malote
        unique_students_pks = []
    
        for unity in unities:
            if client.omr_print_file_separation == Client.BAG_DEFAULT:
            
                print(f'Grouping files from {unity.name}')
                class_files = []
                unity_school_classes = SchoolClass.objects.filter(
                    coordination__unity=unity,
                    pk__in=school_classes.values('pk')
                )

                exam_has_choice_questions = application.exam.has_choice_questions
                exam_has_sum_questions = application.exam.has_sum_questions
                exam_has_discursive_questions = application.exam.has_discursive_questions
                exam_has_essay_questions = application.exam.has_essay_questions
                
                for school_class in unity_school_classes:
                    application_students = ApplicationStudent.objects.filter(
                        application=application
                    ).filter_by_school_class(
                        school_class
                    ).exclude(
                        pk__in=unique_students_pks
                    ).order_by('student__name')

                    if not application_students:
                        continue

                    unique_students_pks.extend(list(application_students.values_list('pk', flat=True)))

                    answer_paths, exams_paths = [], []
                    len_application_students = len(application_students)
                    for index, application_student in enumerate(application_students):
                        if exam_has_choice_questions or exam_has_sum_questions:
                            if custom_pages_objective:
                                if sheet_model != "reduced":
                                    answer_paths.append(f'custom_page_{"_".join(custom_pages_objective)}_{str(application_student.pk)}.pdf')
                                elif index % 2 == 0:
                                    answer_paths.append(f'custom_page_{"_".join(custom_pages_objective)}_{str(application_student.pk)}.pdf')
                                    
                                    if index < len_application_students - 1:
                                        application_student_2 = application_students[index + 1]
                                        answer_paths.append(f'custom_page_{"_".join(custom_pages_objective)}_{str(application_student_2.pk)}.pdf')

                            if sheet_model == "reduced": 
                                if index % 2 == 0:
                                    url1 = os.path.join(base_remote_path, f'answer_{application_student.pk}.pdf')

                                    url2 = None
                                    if index < len_application_students - 1:
                                        application_student_2 = application_students[index + 1]
                                        url2 = os.path.join(base_remote_path, f'answer_{application_student_2.pk}.pdf')
                                    
                                    merged_filepath = merge_a5_files(url1, url2, blank_pages)
                                    
                                    remote_filename = f'mergedanswer_{application_student.pk}.pdf'
                                    fs.save(
                                        os.path.join(base_remote_path, remote_filename),
                                        open(merged_filepath, 'rb')
                                    )
                                    
                                    answer_paths.append(remote_filename)
                                    os.remove(merged_filepath)
                            else:
                                answer_paths.append(f'answer_{application_student.pk}.pdf')

                        if include_discursives and exam_has_discursive_questions:
                            if custom_pages_discursive:
                                answer_paths.append(f'custom_page_{"_".join(custom_pages_discursive)}_{str(application_student.pk)}.pdf')

                            exam_has_discursive_without_essay = application.exam.get_discursive_questions().filter(
                                is_essay=False
                            )
                            if exam_has_discursive_without_essay:
                                answer_paths.append(f'discursive_{application_student.pk}.pdf')

                            if exam_has_essay_questions:
                                answer_paths.append(f'draft_essay_{application.pk}.pdf')
                                answer_paths.append(f'essay_{application_student.pk}.pdf')

                        if include_exams:
                            if custom_pages_student_exam:
                                exams_paths.append(f'custom_page_{"_".join(custom_pages_student_exam)}_{str(application_student.pk)}.pdf')
                            exams_paths.append(f'exam_{application_student.pk}.pdf')

                    pdf_paths = [f'attendance_{school_class.pk}.pdf', *answer_paths]
                    
                    if custom_pages_school_classes:
                        pdf_paths.insert(0, f'custom_page_{"_".join(custom_pages_school_classes)}_{str(school_class.pk)}.pdf')
                        
                    if include_exams:
                        pdf_paths.extend(exams_paths)

                    pdf_full_urls = [
                        fs.url(os.path.join(base_remote_path, path)) for path in pdf_paths
                    ]

                    class_files.append({
                        'paths': pdf_full_urls,
                        'school_class': str(school_class)
                    })

                all_paths = []
                for school_class in class_files:
                    all_paths.extend(school_class['paths'])

                final_file = merge_urls(all_paths, export_tmp_path)
                
                read_pdf = PdfReader(final_file)
                total_bag_pages = len(read_pdf.pages)

                with open(final_file, 'rb') as f:
                    zip_file.writestr(f'{safe_string(unity.name)}-{safe_string(exam_name)}.pdf', f.read())
        
            elif client.omr_print_file_separation == Client.BAG_SEPARATED_FILES:
                print(f'Grouping files from {unity.name}')

                class_files = []
                unity_school_classes = SchoolClass.objects.filter(
                    coordination__unity=unity,
                    pk__in=school_classes.values('pk')
                )

                exam_has_choice_questions = application.exam.has_choice_questions
                exam_has_sum_questions = application.exam.has_sum_questions
                exam_has_discursive_questions = application.exam.has_discursive_questions
                exam_has_essay_questions = application.exam.has_essay_questions
                
                for school_class in unity_school_classes:
                    application_students = ApplicationStudent.objects.filter(
                        application=application
                    ).filter_by_school_class(
                        school_class
                    ).exclude(
                        pk__in=unique_students_pks,
                    ).order_by(
                        'student__name',
                    ).values(
                        'id', 'pk', 'student__name',
                    )

                    if not application_students:
                        continue

                    unique_students_pks.extend(list(application_students.values_list('pk', flat=True)))

                    # Lista de assinatura
                    total_bag_pages += write_file_on_zip(
                        zip_file=zip_file, 
                        file=get_file(get_file_url(f'attendance_{school_class.pk}.pdf'), export_tmp_path), 
                        save_path=f'{safe_string(unity.name)}/{safe_string(school_class.coordination.name)} - {safe_string(school_class.name)}/lista_presenca_{safe_string(school_class.name)}.pdf'
                    )

                    answer_paths, exams_paths = [], []

                    if not application_students:
                        continue
                    
                    len_application_students = len(application_students)
                    for index, application_student in enumerate(application_students):
                        if exam_has_choice_questions or exam_has_sum_questions:
                            if custom_pages_objective:
                                if sheet_model != "reduced":
                                    answer_paths.append(f'custom_page_{"_".join(custom_pages_objective)}_{str(application_student["pk"])}.pdf')
                                elif index % 2 == 0:
                                    answer_paths.append(f'custom_page_{"_".join(custom_pages_objective)}_{str(application_student["pk"])}.pdf')
                                    
                                    if index < len_application_students - 1:
                                        application_student_2 = application_students[index + 1]
                                        answer_paths.append(f'custom_page_{"_".join(custom_pages_objective)}_{str(application_student_2["pk"])}.pdf')

                            if sheet_model == "reduced": 
                                if index % 2 == 0:
                                    url1 = os.path.join(base_remote_path, f'answer_{application_student["pk"]}.pdf')

                                    url2 = None
                                    if index < len_application_students - 1:
                                        application_student_2 = application_students[index + 1]
                                        url2 = os.path.join(base_remote_path, f'answer_{application_student_2["pk"]}.pdf')

                                    merged_filepath = merge_a5_files(url1, url2, blank_pages)
                                    
                                    remote_filename = f'mergedanswer_{application_student["pk"]}.pdf'
                                    fs.save(
                                        os.path.join(base_remote_path, remote_filename),
                                        open(merged_filepath, 'rb')
                                    )
                                    
                                    answer_paths.append(remote_filename)
                                    os.remove(merged_filepath)
                            else:
                                answer_paths.append(f'answer_{application_student["pk"]}.pdf')

                        if include_discursives and exam_has_discursive_questions:
                            if custom_pages_discursive:
                                answer_paths.append(f'custom_page_{"_".join(custom_pages_discursive)}_{str(application_student["id"])}.pdf')

                            exam_has_discursive_without_essay = application.exam.get_discursive_questions().filter(
                                is_essay=False
                            )
                            if exam_has_discursive_without_essay:                            
                                answer_paths.append(f'discursive_{application_student["id"]}.pdf')

                            if exam_has_essay_questions:
                                answer_paths.append(f'draft_essay_{application.pk}.pdf')
                                answer_paths.append(f'essay_{application_student["id"]}.pdf')

                        if include_exams:
                            exam = get_file_url(f'exam_{application_student["id"]}.pdf')
                            
                            if custom_pages_student_exam:
                                custom_page = get_file_url(f'custom_page_{"_".join(custom_pages_student_exam)}_{str(application_student["id"])}.pdf')

                                merged_custom_page_end_exam = merge_urls([custom_page, exam], export_tmp_path)

                                total_bag_pages += write_file_on_zip(
                                    zip_file, 
                                    merged_custom_page_end_exam, 
                                    f'{safe_string(unity.name)}/{safe_string(school_class.coordination.name)} - {safe_string(school_class.name)}/cadernos/caderno_{slugify(unidecode(application_student["student__name"]))}.pdf'
                                )
                            
                            else:
                                total_bag_pages += write_file_on_zip(zip_file, get_file(exam, export_tmp_path), f'{safe_string(unity.name)}/{safe_string(school_class.coordination.name)} - {safe_string(school_class.name)}/cadernos/caderno_{slugify(unidecode(application_student["student__name"]))}.pdf')
                    
                    if custom_pages_school_classes:
                        # Página customizada para turma
                        total_bag_pages += write_file_on_zip(zip_file, get_file(get_file_url(f'custom_page_{"_".join(custom_pages_school_classes)}_{str(school_class.pk)}.pdf'), export_tmp_path), f'{safe_string(unity.name)}/{safe_string(school_class.coordination.name)} - {safe_string(school_class.name)}/pagina_customizada_{safe_string(school_class.name)}.pdf')
                    
                    answer_full_urls = [fs.url(os.path.join(base_remote_path, path)) for path in answer_paths]
                    all_answers = merge_urls(answer_full_urls, export_tmp_path)
                    total_bag_pages += write_file_on_zip(
                        zip_file, all_answers, 
                        f'{safe_string(unity.name)}/{safe_string(school_class.coordination.name)} - {safe_string(school_class.name)}/gabaritos_{safe_string(school_class.name)}.pdf'
                    )

    fs = PrivateMediaStorage()
    saved_file = fs.save(
        f'applications/answer_sheets/{application_pk}/{zip_filename}_{safe_string(exam_name)}.zip',
        open(zip_path, 'rb')
    )

    try:
        shutil.rmtree(export_tmp_path, ignore_errors=True)
    except Exception as e:
        print('Houve um erro ao remover os arquivos temporários locais:', e)

    application.answer_sheet = saved_file
    application.end_last_answer_sheet_generation = timezone.localtime(timezone.now())
    application.sheet_exporting_status = Application.FINISHED
    application.bag_pages = total_bag_pages
    application.save()

    print(f'Saved bag for application {application_pk}')
    self.update_state(state=states.SUCCESS)
    return fs.url(saved_file)