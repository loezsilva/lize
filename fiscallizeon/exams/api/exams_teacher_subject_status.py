from rest_framework.views import APIView
from rest_framework.response import Response
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.exams.models import ExamTeacherSubject
from django.db.models import Q
from fiscallizeon.notifications.models import Notification

class GetGenerateQuestionIAStatusAPIWiew(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def get(self, request, *args, **kwargs):
        exam_id = request.GET.get('exam_id')

        if exam_id:
            has_pending = ExamTeacherSubject.objects.filter(
                exam_id=exam_id, 
                teacher_subject__teacher__is_inspector_ia=True, 
                question_generation_status_with_ai=ExamTeacherSubject.GENERATING
            ).exists()

            has_finished = ExamTeacherSubject.objects.filter(
                Q(question_generation_status_with_ai=ExamTeacherSubject.FINISHED) | Q(question_generation_status_with_ai=ExamTeacherSubject.ERROR),
                exam_id=exam_id, 
                teacher_subject__teacher__is_inspector_ia=True, 
            ).exists()

            if has_pending:
                return Response( data={'status_exam': "pendente"})
            elif has_finished:
                localhost_base_url = "http://localhost:8000/"
                staging_base_url = "https://staging.lizeedu.com.br/"
                production_base_url = "https://app.lizeedu.com.br/"
                urls = (
                    f"{localhost_base_url}provas/?category=exam, "
                    f"{localhost_base_url}provas/{exam_id}/editar/, "
                    f"{staging_base_url}provas/?category=exam, "
                    f"{staging_base_url}provas/{exam_id}/editar/, "
                    f"{production_base_url}provas/?category=exam, "
                    f"{production_base_url}provas/{exam_id}/editar/"
                )
                title = "Solicitaçaão de questões realizada com sucesso!"
                description = "A solicitação realizada a IA já foi concluída."

                Notification.create_single_notification_for_user(urls, title, description, self.request.user)
                return Response( data={'status_exam': "concluido"})
            
            return Response( data={'status_exam': "inicial"})

get_generate_question_ia_task_status = GetGenerateQuestionIAStatusAPIWiew.as_view()
