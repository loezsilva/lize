from datetime import date

from django.db import transaction
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.clients.models import ExamPrintConfig, SchoolCoordination
from fiscallizeon.exams.models import Exam, ExamQuestion, ExamTeacherSubject, TeacherSubject, StatusQuestion
from django.db import transaction

cadernos = [
    ["4078a8a7-818f-48c6-8059-1f0a527aea35","P2_F2_HISTÓRIA E GEOGRAFIA_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["5ed9faef-ab2b-4be3-996b-3495e48bad87","P2_F1_LÍNGUA INGLESA_CRE_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["56a178cf-c174-4335-b528-e12f7f45bf80","P2_F5_CIÊNCIAS_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["dc3b63e6-f1de-4d08-b121-55a3f5cd34e5","P2_F5_GEOGRAFIA_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["2de255e8-ed36-48c8-831d-aa8cde0d3ec9","P2_F5_HISTÓRIA_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["94fa2e07-cabf-4eb8-a278-3fdf897f4cda","P2_F5_MATEMÁTICA_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["d2f89adb-be86-4369-a86a-d2d229e3f6e9","P2_F5_LÍNGUA PORTUGUESA_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["41f81ad2-ecde-4534-aaee-8e36c9333191","P2_F4_CIÊNCIAS_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["72224008-4c85-4a7a-87f5-a1c86e3f7a09","P2_F4_GEOGRAFIA_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["a558a74f-3393-42cf-8eef-95f52a2865e9","P2_F4_HISTÓRIA_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["574e7cfb-c450-43c1-91e4-b94136b040db","P2_F4_MATEMÁTICA_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["39005f77-2cf9-4d9f-becf-360e438d46ba","P2_F4_LÍNGUA PORTUGUESA_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["3520b491-6d6a-407f-8cec-b9652e343344","P2_F3_CIÊNCIAS_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["7cbcda8c-a2e3-463f-a005-f496b149c719","P2_F3_GEOGRAFIA_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["80562f5b-fe1c-4244-a7ff-fe36fce3dc4b","P2_F3_HISTÓRIA_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["5289736f-6b4a-43f2-aa94-b753e5188dbe","P2_F3_MATEMÁTICA_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["b399fa75-2bbd-4617-b737-841920039103","P2_F3_LÍNGUA PORTUGUESA_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["cbbbad26-0e70-4bb1-aa16-1467e5d388f6","P2_F2_CIÊNCIAS_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["4f3d729d-5b74-4ab1-93d9-be20723f3019","P2_F2_GEOGRAFIA_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["5fef1600-67d4-4a1c-8181-11b7a7c1df46","P2_F2_HISTÓRIA_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["8793a3d5-4630-421e-a91f-d6695b253b28","P2_F2_MATEMÁTICA_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["a9cd1839-c596-4017-aa9d-1fbe9d8b52a6","P2_F2_LÍNGUA PORTUGUESA_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["ef90c86d-e32c-4350-99d9-ce70bfba2a9b","P2_F1_NATUREZA E SOCIEDADE_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["5dee7269-c466-425d-a5d7-7752e41f44fc","P2_F1_MATEMÁTICA_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["9eb805f3-740e-4b70-91f3-b4f18ef0e94a","P2_F1_LÍNGUA PORTUGUESA_SAS_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["7ffc9825-c3c3-4124-a5de-fb11a37d6ad5","P2_F5_CIÊNCIAS_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["5e666d52-90bf-4c43-85b5-098661fc5f46","P2_F5_GEOGRAFIA_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["d53b835f-9bf8-4058-88ca-87310f077cc1","P2_F5_HISTÓRIA_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["b1737b93-6bae-4119-af20-aa5146621b6d","P2_F5_MATEMÁTICA_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["8e8428f4-a906-479e-b25b-581cb11a7d98","P2_F5_LÍNGUA PORTUGUESA_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["9eceeee6-de5f-4261-9671-4f5f55f6b3d0","P2_F4_CIÊNCIAS_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["9c57af5a-fdcd-4133-ac47-df7307e3b3f9","P2_F4_GEOGRAFIA_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["cb87581c-21e0-415d-8aef-222ba71c6c31","P2_F4_HISTÓRIA_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["1f6e082e-aead-4b51-8f9a-e31eba7bb2eb","P2_F4_MATEMÁTICA_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["e8d049a4-5a43-4444-81ca-f0dc711da593","P2_F4_LÍNGUA PORTUGUESA_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["0819a9f7-26f6-4b80-bc57-ba615a76afe5","P2_F3_CIÊNCIAS_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["403e6291-0386-410b-b9da-f929ac2c5d56","P2_F3_HISTÓRIA E GEOGRAFIA_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["88de09eb-0739-4342-be77-138f383a5829","P2_F3_MATEMÁTICA_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["cbcec3cf-b2c0-4076-bb0b-8928d2c9ab7c","P2_F3_LÍNGUA PORTUGUESA_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["9d948182-11e5-4273-a13e-a6dfda9d87e1","P2_F2_CIÊNCIAS_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["cf587852-fe23-4287-ac35-0727b3fe3aff","P2_F2_HISTÓRIA E GEOGRAFIA_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["6d7cd979-004d-4302-b251-904e802c29ca","P2_F2_MATEMÁTICA_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["3964b515-aca9-47a8-a8bc-251defface4f","P2_F2_LÍNGUA PORTUGUESA_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["c258a8b6-9859-4a21-b63a-33a0c85cecd6","P2_F1_CIÊNCIAS_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["ef148649-00d2-4fe4-bc84-1ac32bfec403","P2_F1_HISTÓRIA E GEOGRAFIA_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["b830936b-60b6-423b-8741-3bd02f8a2f63","P2_F1_MATEMÁTICA_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["55af21fe-2d24-4f40-8c77-6da1f66a2b09","P2_F1_LÍNGUA PORTUGUESA_ANGLO_2023","avaliacoes2.fund1@rededecisao.com.br"],
    ["7e4339c0-c978-4a82-a559-3885e3552136","P2_Língua Inglesa_F5_SAS_2023","renato.sa@rededecisao.com.br"],
    ["7d5752d5-7247-4de2-9ecb-1caaec185531","P2_Língua Inglesa_F4_SAS_2023","renato.sa@rededecisao.com.br"],
    ["10017bfe-32b9-4fbd-8083-5ed01c278838","P2_Língua Inglesa_F3_SAS_2023","renato.sa@rededecisao.com.br"],
    ["3a186386-46c8-4be6-8551-c21f4591d5ac","P2_Língua Inglesa_F2_SAS_2023","renato.sa@rededecisao.com.br"],
    ["b119335c-8c20-43e7-87fb-e0126c6da68d","P2_Língua Inglesa_F1_SAS_2023","renato.sa@rededecisao.com.br"],
    ["541c5e60-5b2d-4599-b4c5-316ed63010c9","P2_Língua Inglesa_F5_Oxford_2023","renato.sa@rededecisao.com.br"],
    ["150dcb9d-66e6-4f86-9e03-eb5c92c9d6eb","P2_Língua Inglesa_F4_Oxford_2023","renato.sa@rededecisao.com.br"],
    ["9cc42d5e-08f1-4d97-9787-8a654b9edba1","P2_Língua Inglesa_F3_Oxford_2023","renato.sa@rededecisao.com.br"],
    ["7a1f6c03-b921-4c55-b0bf-246294ce811f","P2_Língua Inglesa_F2_Oxford_2023","renato.sa@rededecisao.com.br"],
    ["b34005fd-0e32-4052-a07f-e561f65b987f","P2_Língua Inglesa_F1_Oxford_2023","renato.sa@rededecisao.com.br"],
    ["0ae495d5-df89-43c1-bbf0-a6e2da4584d6","P2_Língua Inglesa_F6_SAS_2023","renato.sa@rededecisao.com.br"],
    ["1cfc7e79-20fd-4486-ae83-5ce07864ac9b","P2_Física_M3_ANGLO_2023","adilson.junior@rededecisao.com.br"],
    ["23b83d3f-cb58-4af3-80fe-e6a3e0aae2ba","P2_Física_F9_ANGLO_2023","adilson.junior@rededecisao.com.br"],
    ["23c6400d-4314-4e29-b11f-8fa84edc59c8","P2_Língua Inglesa_F9_OXFORD_2023","renato.sa@rededecisao.com.br"],
    ["2619e07b-b171-44c1-83d8-e27760127de3","P2_Matemática Unificada_M1_ANGLO_2023","marcia.scarparo@rededecisao.com.br"],
    ["270fb38c-95d6-48f9-af4d-fe6944eb1d11","P2_Matemática_F9_ANGLO_2023","marcia.scarparo@rededecisao.com.br"],
    ["28c3be36-ca2f-4bcb-9c9a-6c8e5ae5c6c3","P2_Matemática_F7_SAS_2023","marcia.scarparo@rededecisao.com.br"],
    ["36493fef-db3f-4850-a7f0-2d912ec2b9ca","P2_Matemática_F8_ANGLO_2023","marcia.scarparo@rededecisao.com.br"],
    ["3c292b3a-1606-4f47-ad25-173fafc564e2","P2_Física_F9_SAS_2023","adilson.junior@rededecisao.com.br"],
    ["4333d53d-3921-48d3-82e0-3ac8632cc7db","P2_Matemática_F7_ANGLO_2023","marcia.scarparo@rededecisao.com.br"],
    ["43b2fc43-7d6e-47de-b672-61ada9eabbd1","P2_Química Unificada_M1_ANGLO_2023","adilson.junior@rededecisao.com.br"],
    ["474b56e3-f652-47e5-b5ac-4415877c975e","P2_Física Unificada_M2_ANGLO_2023","adilson.junior@rededecisao.com.br"],
    ["493a5d28-5b3c-467e-8fb4-93f160eb0e42","P2_Língua Inglesa_F7_SAS_2023","renato.sa@rededecisao.com.br"],
    ["4970f189-3fcf-4c90-94a2-1661032b3b09","P2_Língua Inglesa_F7_OXFORD_2023","renato.sa@rededecisao.com.br"],
    ["53dcd27c-dc8b-4726-aceb-ad395ed4485a","P2_Língua Inglesa_M3_ANGLO_2023","renato.sa@rededecisao.com.br"],
    ["5dfe822c-9be8-47a3-baa3-f8e9e32f7790","P2_Língua Inglesa_F8_OXFORD_2023","renato.sa@rededecisao.com.br"],
    ["5ee0d496-cb0f-41ce-bed8-f96b4d22f402","P2_Matemática Unificada_M2_ANGLO_2023","marcia.scarparo@rededecisao.com.br"],
    ["62f4d0d9-c8e1-43da-bd0e-150e84861929","P2_Língua Inglesa_F6_OXFORD_2023","renato.sa@rededecisao.com.br"],
    ["7902317f-e1ee-4dc4-8d43-3f35b7b0379d","P2_Química Unificada_M2_ANGLO_2023","adilson.junior@rededecisao.com.br"],
    ["881caa9f-83bf-4c82-96d3-32f3f6d1eb8b","P2_Matemática_F8_SAS_2023","marcia.scarparo@rededecisao.com.br"],
    ["8d2c00cf-a60e-4377-9cc1-70f290e7c80f","P2_Matemática_F9_SAS_2023","marcia.scarparo@rededecisao.com.br"],
    ["90300594-04bd-43fc-8bcf-8bb5ca179ac2","P2_Língua Inglesa_M1_SAS_2023","renato.sa@rededecisao.com.br"],
    ["9e50bd70-1977-48f5-bebb-624840451e4e","P2_CiênciasA_F9_ANGLO_2023","adilson.junior@rededecisao.com.br"],
    ["9fd9ba3b-29ee-49d8-b6f8-c1770dcd7bcd","P2_Matemática Unificada_M1_SAS_2023","marcia.scarparo@rededecisao.com.br"],
    ["a039fd98-a9ca-40c5-86d7-c6f0c64f3cfb","P2_Química Unificada_M1_SAS_2023","adilson.junior@rededecisao.com.br"],
    ["a87a2d18-18bd-4765-924b-85023a4ff6ec","P2_Química Unificada_M2_SAS_2023","adilson.junior@rededecisao.com.br"],
    ["a944c989-8706-49a8-a6a7-09c615e3d2e1","P2_Matemática Unificada_M3_SAS_2023","marcia.scarparo@rededecisao.com.br"],
    ["b67f9e57-a5bd-4364-b360-d89193e7b559","P2_Língua Inglesa_F8_SAS_2023","renato.sa@rededecisao.com.br"],
    ["b944c388-e75a-49dd-9c05-b41e0bad6c28","P2_Química_M3_SAS_2023","adilson.junior@rededecisao.com.br"],
    ["ba173e55-fc55-440d-9f5f-782491763676","P2_Matemática Unificada_M2_SAS_2023","marcia.scarparo@rededecisao.com.br"],
    ["bae489a1-ca51-440d-869d-6d56f01d2d88","P2_Língua Inglesa_F9_SAS_2023","renato.sa@rededecisao.com.br"],
    ["be59dbe5-bdb4-4bee-96ff-b4983215e59e","P2_Química_F9_SAS_2023","adilson.junior@rededecisao.com.br"],
    ["c14b57cc-fe1f-48bb-b545-dfec367a660b","P2_Física_M3_SAS_2023","adilson.junior@rededecisao.com.br"],
    ["c6a6e479-3685-4136-a6ec-1e694886505d","P2_Língua Inglesa_M2_SAS_2023","renato.sa@rededecisao.com.br"],
    ["d2cbc81b-f71e-4c66-9566-4e3cf3b42ca0","P2_Língua Inglesa_M3_SAS_2023","renato.sa@rededecisao.com.br"],
    ["d36698b7-f964-43ab-8dd5-c3be372d1271","P2_Física Unificada_M1_SAS_2023","adilson.junior@rededecisao.com.br"],
    ["d821a08d-68e2-4ae5-9d1a-4e0df7ce3ae1","P2_Língua Inglesa_M2_ANGLO_2023","renato.sa@rededecisao.com.br"],
    ["d8acac03-c407-4edf-853a-c4d9327f6186","P2_Física Unificada_M2_SAS_2023","adilson.junior@rededecisao.com.br"],
    ["dc83b8af-bfd7-4218-bcaf-cf9e2afce63d","P2_Física Unificada_M1_ANGLO_2023","adilson.junior@rededecisao.com.br"],
    ["e1e4e3f3-3aec-4766-90e1-ee973dea7a4c","P2_Matemática_F6_SAS_2023","marcia.scarparo@rededecisao.com.br"],
    ["e7613d82-fabd-4443-abd2-ab613d394d38","P2_Química_M3_ANGLO_2023","adilson.junior@rededecisao.com.br"],
    ["ecc13582-4057-4325-a71c-51080c383c10","P2_Matemática_F6_ANGLO_2023","marcia.scarparo@rededecisao.com.br"],
    ["f37daf30-4eb4-42f0-a8d8-8ebd424bb3ec","P2_Língua Inglesa_M1_ANGLO_2023","renato.sa@rededecisao.com.br"],
    ["f569c791-fa74-4bd0-9f4c-d526d788da7c","P2_Física_F8_ANGLO_2023","adilson.junior@rededecisao.com.br"],
    ["fa86478c-c9bf-452f-a893-d1dac87ab141","P2_Matemática Unificada_M3_ANGLO_2023","marcia.scarparo@rededecisao.com.br"]
]

for caderno in cadernos[1:]:
    with transaction.atomic():
        orginal_caderno_id = caderno[0]
        original_caderno_name = caderno[1]
        final_caderno_name = caderno[2]
        to_email_teachers = caderno[3]
        print(original_caderno_name, to_email_teachers)
        original_exam = Exam.objects.using('default').get(pk=orginal_caderno_id)
        copy_exam = Exam.objects.using('default').get(pk=orginal_caderno_id)
        copy_exam.name = f'{final_caderno_name}'
        exams_same_name = Exam.objects.using('default').filter(name=copy_exam.name)
        exams_same_name.delete()
        copy_exam.elaboration_deadline = start_date = date(2024, 5, 5)
        copy_exam.release_elaboration_teacher = date(2024, 4, 5)
        copy_exam.total_grade = 10
        copy_exam.status = Exam.ELABORATING
        copy_exam_print_config = ExamPrintConfig.objects.using('default').get(
            pk=original_exam.exam_print_config.pk
        )
        copy_exam_print_config.pk = None
        copy_exam_print_config.name = f'Configuração {copy_exam.name}'
        copy_exam_print_config.save()
        copy_exam.pk = None
        copy_exam.source_exam = original_exam
        copy_exam.exam_print_config = copy_exam_print_config
        copy_exam.save(skip_hooks=True)
        original_exam.coordinations.all()
        copy_exam.coordinations.set(SchoolCoordination.objects.filter(
            unity__client__name__icontains="decis",
            unity__client__educationsystem=original_exam.education_system,
            high_school=original_exam.coordinations.all().first().high_school,
            elementary_school=original_exam.coordinations.all().first().elementary_school,
            elementary_school2=original_exam.coordinations.all().first().elementary_school2
        ).distinct())
        original_exam_teacher_subject = ExamTeacherSubject.objects.using('default').filter(exam=original_exam).first()
        copy_teacher_subject = TeacherSubject.objects.using('default').filter(
              teacher=Inspector.objects.using('default').filter(email=to_email_teachers).first(),
              subject=original_exam_teacher_subject.teacher_subject.subject,
              active=True
        ).order_by('created_at').last()
        if not copy_teacher_subject:
            copy_teacher_subject = TeacherSubject.objects.using('default').filter(
                teacher=Inspector.objects.using('default').filter(email=to_email_teachers).first(),
                subject=original_exam_teacher_subject.teacher_subject.subject
            ).order_by('created_at').last()
            if not copy_teacher_subject:
                copy_teacher_subject = TeacherSubject.objects.using('default').create(
                    teacher=Inspector.objects.using('default').filter(email=to_email_teachers).first(),
                    subject=original_exam_teacher_subject.teacher_subject.subject
                )
        count_questions = original_exam.examquestion_set.availables().count()
        copy_exam_teacher_subject = ExamTeacherSubject(
            teacher_subject=copy_teacher_subject,
            exam=copy_exam,
            grade=original_exam_teacher_subject.grade,
            quantity=10 if count_questions < 10 else count_questions,
            order=0,
            elaboration_email_sent=True
        )
        copy_exam_teacher_subject.save(skip_hooks=True)
        for index, exam_question in enumerate(ExamQuestion.objects.using('default').filter(exam=original_exam).availables(exclude_annuleds=True).order_by('exam_teacher_subject__order', 'order')):
            original_exam_question = ExamQuestion.objects.using('default').get(pk=exam_question.pk)
            copy_exam_question = ExamQuestion.objects.using('default').get(pk=exam_question.pk)
            if ExamQuestion.objects.using('default').filter(
                exam=copy_exam,
                question=original_exam_question.question,
                exam_teacher_subject=copy_exam_teacher_subject
            ).exists():
                continue
            copy_exam_question.pk = None
            copy_exam_question.exam = copy_exam
            copy_exam_question.order = index
            copy_exam_question.exam_teacher_subject = copy_exam_teacher_subject
            copy_exam_question.save(skip_hooks=True)
            for status in original_exam_question.statusquestion_set.all().order_by('created_at'):
                copy_status_question = StatusQuestion.objects.using('default').get(pk=status.pk)
                copy_status_question.pk = None
                copy_status_question.exam_question = copy_exam_question
                copy_status_question.save()
                 

