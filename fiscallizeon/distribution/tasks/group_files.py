import os, re
import zipfile
import shutil

from PyPDF2 import PdfReader

from django.utils import timezone

from fiscallizeon.celery import app
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.distribution.models import RoomDistribution, Room, RoomDistributionStudent
from fiscallizeon.clients.models import SchoolCoordination, Unity, Client
from fiscallizeon.exams.models import ClientCustomPage
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.distribution.utils import merge_urls, get_file
from unidecode import unidecode
from django.template.defaultfilters import slugify

def safe_string(string):
    string = re.sub(r'[\s]+|/', '_', string) # Remove espaços
    string = re.sub(r'[^a-zA-Z0-9_]+', '', string)
    return string

def write_file_on_zip(zip_file, file, save_path):

    try:
        read_pdf = PdfReader(file)
    except Exception as e:
        print(f'File not read: {file}')
        raise Exception('Could not read PDF file')
    
    with open(file, 'rb') as f:
        zip_file.writestr(save_path, f.read())

    return len(read_pdf.pages)

@app.task(autoretry_for=(Exception,), max_retries=5, retry_backoff=True)
def group_files(room_distribution_pk, export_version=0, include_exams=False, include_discursives=False, custom_pages_pks=[]):
    print(f'Grouping files for room distribution {room_distribution_pk}')
    room_distribution = RoomDistribution.objects.get(pk=room_distribution_pk)

    school_coordinations = SchoolCoordination.objects.filter(
        rooms__room_distribution__distribution=room_distribution
    ).distinct()

    unities = Unity.objects.filter(coordinations__in=school_coordinations).distinct()

    rooms = Room.objects.filter(
        room_distribution__distribution=room_distribution,
    ).distinct()

    room_distribution_tmp_path = os.path.join(
        'tmp', 'distribution', str(room_distribution_pk), str(export_version)
    )
    os.makedirs(room_distribution_tmp_path, exist_ok=True)

    first_application = room_distribution.application_set.first()
    zip_filename = 'ensalamento-{}-{}_{}-{}'.format(
        export_version,
        first_application.date.strftime('%d-%m-%Y'),
        first_application.start.strftime('%H%M'),
        first_application.end.strftime('%H%M'),
    )
    
    client = Client.objects.get(pk=unities.first().client.pk)

    custom_pages = ClientCustomPage.objects.filter(
        pk__in=custom_pages_pks
    ).order_by('id')
    
    custom_pages_objective = [str(custom_page.id) for custom_page in custom_pages.filter(location__in=[ClientCustomPage.OBJECTIVE_ANSWER_SHEET])]
    custom_pages_discursive = [str(custom_page.id) for custom_page in custom_pages.filter(location__in=[ClientCustomPage.DISCURSIVE_ANSWER_SHEET])]
    custom_pages_student_exam = [str(custom_page.id) for custom_page in custom_pages.filter(location__in=[ClientCustomPage.STUDENT_EXAM])]
    custom_pages_after_student_exam = [str(custom_page.id) for custom_page in custom_pages.filter(location__in=[ClientCustomPage.AFTER_STUDENT_EXAM])]
    custom_pages_school_classes = [str(custom_page.id) for custom_page in custom_pages.filter(location__in=[ClientCustomPage.SIGNATURE_SHEET])]

    zip_path = os.path.join(room_distribution_tmp_path, f'{zip_filename}.zip')
    with zipfile.ZipFile(zip_path, "a", zipfile.ZIP_DEFLATED, allowZip64=True) as zip_file:
        base_remote_path = os.path.join(
            'ensalamentos', 'tmp', str(room_distribution_pk), str(export_version)
        )
        fs = PrivateMediaStorage()
        
        for unity in unities:
            if client.omr_print_file_separation == Client.BAG_DEFAULT:
                coordination_rooms = rooms.filter(coordination__unity=unity)
                rooms_files = []

                for room in coordination_rooms:
                    room_distribution_students = RoomDistributionStudent.objects.filter(
                        distribution=room_distribution,
                        room=room,
                    )
                    application_students = ApplicationStudent.objects.filter(
                        student__in=room_distribution_students.values_list('student', flat=True),
                        application__in=room_distribution.application_set.all(),
                    ).order_by('student__name')

                    answer_paths, exams_paths, discursive_paths = [], [], []
                    for application_student in application_students:
                        if application_student.application.exam.has_choice_questions:
                            if custom_pages_objective:
                                answer_paths.append(f'custom_page_{"_".join(custom_pages_objective)}_{str(application_student.pk)}.pdf')
                            answer_paths.append(f'answer_{application_student.pk}.pdf')
                        
                        if include_discursives and application_student.application.exam.has_discursive_questions:
                            if custom_pages_discursive:
                                discursive_paths.append(f'custom_page_{"_".join(custom_pages_discursive)}_{str(application_student.pk)}.pdf')

                            exam_has_discursive_without_essay = application_student.application.exam.get_discursive_questions().filter(
                                is_essay=False
                            )
                            if exam_has_discursive_without_essay:
                                discursive_paths.append(f'discursive_{application_student.pk}.pdf')

                            if application_student.application.exam.has_essay_questions:
                                answer_paths.append(f'draft_essay_{application_student.application_id}.pdf')
                                answer_paths.append(f'essay_{application_student.pk}.pdf')
                        
                        if include_exams:
                            if custom_pages_student_exam:
                                exams_paths.append(f'custom_page_{"_".join(custom_pages_student_exam)}_{str(application_student.pk)}.pdf')

                            exams_paths.append(f'exam_{application_student.pk}.pdf')

                            if custom_pages_after_student_exam:
                                exams_paths.append(f'custom_page_{"_".join(custom_pages_after_student_exam)}_{str(application_student.pk)}.pdf')

                    pdf_paths = [f'attendance_{room.pk}.pdf', *answer_paths]

                    if custom_pages_school_classes:
                        pdf_paths.insert(0, f'custom_page_{"_".join(custom_pages_school_classes)}_{str(room.pk)}.pdf')

                    if include_discursives:
                        pdf_paths.extend(discursive_paths)
                    if include_exams:
                        pdf_paths.extend(exams_paths)

                    full_pdf_paths = [
                        fs.url(os.path.join(base_remote_path, path)) for path in pdf_paths
                    ]
                    
                    rooms_files.extend(full_pdf_paths)

                unity_file = merge_urls(rooms_files, room_distribution_tmp_path)

                with open(unity_file, 'rb') as f:
                    zip_file.writestr(f'{unity.name}.pdf', f.read())
                    print(f"Arquivo da unidade {unity} agrupado com sucesso")
        
            elif client.omr_print_file_separation == Client.BAG_SEPARATED_FILES:
                def get_file_url(file):
                    return fs.url(os.path.join(base_remote_path, file))
                    
                coordination_rooms = rooms.filter(coordination__unity=unity)
                
                # Removi a lista de pátio: Conversa com Pedro e Franklin em 28/03/2024
                # write_file_on_zip(zip_file=zip_file, file=get_file(get_file_url(f'yard_{unity.pk}.pdf'), room_distribution_tmp_path), save_path=f'{safe_string(unity.name)}/lista_patio_{unity.name}.pdf')

                for room in coordination_rooms:
                    room_distribution_students = RoomDistributionStudent.objects.filter(
                        distribution=room_distribution,
                        room=room,
                    )

                    # Lista de assinatura
                    attendance_list_url = get_file_url(f'attendance_{room.pk}.pdf')
                    if custom_pages_school_classes:
                        custom_page_url = get_file_url(f'custom_page_{"_".join(custom_pages_school_classes)}_{str(room.pk)}.pdf')
                        attendance_file = merge_urls([custom_page_url,attendance_list_url], room_distribution_tmp_path)
                    else:
                        attendance_file = get_file(attendance_list_url, room_distribution_tmp_path)

                    write_file_on_zip(
                        zip_file=zip_file, 
                        file=attendance_file,
                        save_path=f'{safe_string(unity.name)}/{safe_string(room.name)}/lista_presenca_{safe_string(room.name)}.pdf'
                    )

                    application_students = ApplicationStudent.objects.filter(
                        student__in=room_distribution_students.values_list('student', flat=True),
                        application__in=room_distribution.application_set.all(),
                    ).order_by('student__name')

                    answer_paths, exams_paths, discursive_paths = [], [], []
                    for application_student in application_students:
                        if application_student.application.exam.has_choice_questions:
                            if custom_pages_objective:
                                answer_paths.append(f'custom_page_{"_".join(custom_pages_objective)}_{str(application_student.pk)}.pdf')
                            answer_paths.append(f'answer_{application_student.pk}.pdf')
                        
                        if include_discursives and application_student.application.exam.has_discursive_questions:
                            if custom_pages_discursive:
                                discursive_paths.append(f'custom_page_{"_".join(custom_pages_discursive)}_{str(application_student.pk)}.pdf')

                            exam_has_discursive_without_essay = application_student.application.exam.get_discursive_questions().filter(
                                is_essay=False
                            )
                            if exam_has_discursive_without_essay:
                                discursive_paths.append(f'discursive_{application_student.pk}.pdf')

                            if application_student.application.exam.has_essay_questions:
                                answer_paths.append(f'draft_essay_{application_student.application_id}.pdf')
                                answer_paths.append(f'essay_{application_student.pk}.pdf')
                        
                        if include_exams:
                            exam_url = get_file_url(f'exam_{application_student.pk}.pdf')

                            if custom_pages_student_exam or custom_pages_after_student_exam:
                                custom_page, custom_page_after = None, None
                                if pages := custom_pages_student_exam:
                                    custom_page = get_file_url(f'custom_page_{"_".join(pages)}_{str(application_student.id)}.pdf')
                                
                                if pages := custom_pages_after_student_exam:
                                    custom_page_after = get_file_url(f'custom_page_{"_".join(pages)}_{str(application_student.id)}.pdf')

                                merged_custom_page_end_exam = merge_urls([custom_page, exam_url, custom_page_after], room_distribution_tmp_path)

                                write_file_on_zip(
                                    zip_file=zip_file, 
                                    file=merged_custom_page_end_exam,
                                    save_path=f'{safe_string(unity.name)}/{safe_string(room.name)}/cadernos/{slugify(unidecode(application_student.student.name))}.pdf'
                                )

                            else:
                                write_file_on_zip(
                                    zip_file=zip_file, 
                                    file=get_file(exam_url, room_distribution_tmp_path),
                                    save_path=f'{safe_string(unity.name)}/{safe_string(room.name)}/cadernos/{slugify(unidecode(application_student.student.name))}-{str(application_student.pk)[:5]}.pdf'
                                )

                    pdf_paths = answer_paths
                    
                    if include_discursives:
                        pdf_paths.extend(discursive_paths)

                    full_pdf_paths = [
                        fs.url(os.path.join(base_remote_path, path)) for path in pdf_paths
                    ]

                    unity_file = merge_urls(full_pdf_paths, room_distribution_tmp_path)

                    write_file_on_zip(
                        zip_file=zip_file, 
                        file=unity_file, 
                        save_path=f'{safe_string(unity.name)}/{safe_string(room.name)}/gabaritos_{safe_string(room.name)}.pdf'
                    )

                print(f"Arquivo da unidade {unity} agrupado com sucesso")

    fs = PrivateMediaStorage()
    saved_file = fs.save(
        f'ensalamentos/{room_distribution_pk}/{zip_filename}.zip',
        open(zip_path, 'rb')
    )

    room_distribution.exams_bag = saved_file
    room_distribution.last_exams_bag_generation = timezone.localtime(timezone.now())
    room_distribution.status = RoomDistribution.EXPORTED
    room_distribution.save()
    try:
        shutil.rmtree(os.path.dirname(room_distribution_tmp_path), ignore_errors=True)
    except Exception as e:
        print('Problema na exclusão de arquivos temporários:', e)

    print(f'Saved exams bag for room distribution {room_distribution_pk}')
    return saved_file
