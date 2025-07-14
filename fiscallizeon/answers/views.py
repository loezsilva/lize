from datetime import datetime, timedelta

from django.shortcuts import get_object_or_404
from fiscallizeon.answers.models import Attachments, FileAnswer, OptionAnswer, ProofAnswer, TextualAnswer, SumAnswer, SumAnswerQuestionOption
from fiscallizeon.applications.models import Application, ApplicationStudent, Annotation
from fiscallizeon.questions.models import Question
from fiscallizeon.core.utils import CheckHasPermission
from django.views.generic import TemplateView, View, DetailView
from django.conf import settings
from django.urls import reverse
from fiscallizeon.exams.models import ExamTeacherSubject

from django.core.exceptions import BadRequest
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http.response import HttpResponseRedirect
from django.utils.crypto import get_random_string
from fiscallizeon.subjects.models import Subject
from django.db.models import OuterRef, Subquery



class FileAnswerTemplateView(TemplateView):
    template_name = "answers/qrcode_response.html"

    def dispatch(self, request, *args, **kwargs):
        application_student = ApplicationStudent.objects.get(pk=kwargs.get('application_student_pk'))
        if not application_student.application.is_happening or application_student.application_state == 'finished':
            raise BadRequest('Application not in progress.')           

        return super(FileAnswerTemplateView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["question"] = Question.objects.get(pk=kwargs.get('question_id'))
        context['application_student'] = ApplicationStudent.objects.get(pk=kwargs.get('application_student_pk'))

        question_response = FileAnswer.objects.filter(question=context["question"], student_application=context['application_student'])
        
        if question_response:
            context["question_response"] = question_response.first()

        return context
class AttachmentTemplateView(TemplateView):
    template_name = "attachments/attachment_qrcode_response.html"

    def dispatch(self, request, *args, **kwargs):
        application_student = ApplicationStudent.objects.get(pk=kwargs.get('application_student'))
        if not application_student.application.is_happening or application_student.application_state == 'finished':
            raise BadRequest('Application not in progress.')           

        return super(AttachmentTemplateView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['exam_teacher_subject'] = ExamTeacherSubject.objects.get(pk=kwargs.get('exam_teacher_subject'))
        context['application_student'] = ApplicationStudent.objects.get(pk=kwargs.get('application_student'))

        return context
    
class ProofOfAnswersTemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = "answers/proof_of_answers.html"
    required_permissions = [settings.COORDINATION, settings.STUDENT]
    
    def dispatch(self, request, *args, **kwargs):
        
        self.proof = ProofAnswer.objects.filter(application_student__pk=self.kwargs['pk']).order_by('-created_at').first()
        
        if self.proof and request.user.user_type == settings.COORDINATION:
            return HttpResponseRedirect(reverse('answers:proof_of_answers_coordination', kwargs={ "pk": self.proof.id }))
        
        if not self.proof:
            
            messages.warning(request, 'Não há comprovante de resposta associado')
            
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))
        
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        
        context = super().get_context_data(**kwargs)
        
        context["proof"] = self.proof
        
        return context    
class ProofOfAnswersCoordinationTemplateView(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = "answers/proof_of_answers_coordination.html"
    required_permissions = [settings.COORDINATION]
    model = ProofAnswer
    
class ProofAnswerCreateView(CheckHasPermission, View):
    model = ProofAnswer
    required_permissions = [settings.STUDENT, ]
    
    def dispatch(self, request, *args, **kwargs):
        application_student = get_object_or_404(ApplicationStudent, pk=self.kwargs['pk'])
        
        self.proof = ProofAnswer.objects.using('default').filter(application_student__pk=self.kwargs['pk']).order_by('-created_at').first()
        
        if request.user.user_type == settings.STUDENT and request.user != application_student.student.user:
            messages.error(request, "Você não tem permissão para fazer esta ação.")
            return HttpResponseRedirect(reverse("core:redirect_dashboard"))
        
        if not application_student.total_answered_questions() > 0:
            messages.error(request, 'Não foi possível criar o comprovante de respostas.')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))
        
        if not application_student.application.category == Application.HOMEWORK and not application_student.application.is_time_finished:
            messages.error(request, "Você não tem permissão para fazer esta ação.")
            return HttpResponseRedirect(reverse("core:redirect_dashboard"))
        
        if self.proof and datetime.strftime(self.get_application_student_date(application_student), "%Y-%m-%d %H:%M:%S") == datetime.strftime(self.proof.end_date - timedelta(hours=3), "%Y-%m-%d %H:%M:%S"):
            return HttpResponseRedirect(reverse('answers:proof_of_answers', kwargs={ "pk": self.kwargs['pk'] }))

        return super().dispatch(request, *args, **kwargs)
    
    def get_alternative_letter(self, index):
        return "abcdefgh"[index]
            
    def get_application_student_date(self, application_student):
        return application_student.end_date if hasattr(application_student, "end_date") else application_student.get_last_answer_date()
    
    def get(self, request, *args, **kwargs):
        application_student = ApplicationStudent.objects.using('default').get(pk=self.kwargs['pk'])
        
        exam = application_student.application.exam
        
        data = {
            "code": get_random_string(8),
            "application_student": application_student,
            "start_date": application_student.start_date if hasattr(application_student, 'start_date') else application_student.application.date_time_start_tz,
            "end_date":  self.get_application_student_date(application_student),
            "exam_name": str(exam),
            "is_randomized": exam.is_randomized,
            "group_attachments": exam.group_attachments, 
            "answers_json": [],
        }
        
        exam_questions = exam.examquestion_set.using('default').availables().order_by("exam_teacher_subject__order", "order")
        
        for exam_question in exam_questions:
            answer = None
            answer_data = {
                "question_id": str(exam_question.question.id),
                "category": str(exam_question.question.get_category_display()),
                "number_print": application_student.application.exam.number_print_question(exam_question.question),
                "question_enunciation": str(exam_question.question.get_enunciation_str()[:250]), 
                "send_on_qrcode": False,
                "print_only_enunciation": exam_question.question.print_only_enunciation,
                "answer_id": "",
                "alternative_letter": "",
                "selected_alternative_letter": "",
                "file_name": "",
                "files_names": "",
                "text": "",
                "answer_updated_at": "",
            }
            
            if exam_question.question.category == Question.CHOICE:
                answer = OptionAnswer.objects.using('default').filter(
                    status=OptionAnswer.ACTIVE, 
                    question_option__question=exam_question.question,
                    student_application=application_student
                ).last()
                
                if answer:
                    answer_data["alternative_letter"] = self.get_alternative_letter(int(answer.question_option.index))
            
            elif exam_question.question.category == Question.SUM_QUESTION:
                answer = SumAnswer.objects.using('default').filter(
                    question=exam_question.question,
                    student_application=application_student
                ).order_by('-updated_at').first()
                
            elif exam_question.question.category == Question.TEXTUAL:
                answer = TextualAnswer.objects.using('default').filter(
                    question=exam_question.question,
                    student_application=application_student
                ).order_by('-updated_at').first()
                
            elif exam_question.question.category == Question.FILE:
                answer = FileAnswer.objects.using('default').filter(
                    question=exam_question.question,
                    student_application=application_student
                ).order_by('-updated_at').first()
                
            if answer:
                answer_data["answer_id"] = str(answer.id)
                answer_data["answer_updated_at"] = str(answer.updated_at)
                
                if exam_question.question.category == Question.TEXTUAL or exam_question.question.category == Question.FILE:
                    
                    if exam_question.question.category == Question.FILE:
                        answer_data["send_on_qrcode"] = answer.send_on_qrcode
                        
                        if exam.group_attachments:
                            attachments = Attachments.objects.filter(application_student=application_student, exam_teacher_subject=exam_question.exam_teacher_subject)
                            if attachments.exists():
                                names = []
                                for attachment in attachments:
                                    names.append(attachment.filename)
                                answer_data["files_names"] = names
                        else:
                            answer_data["file_name"] = str(answer.arquivo.name) if hasattr(answer, "arquivo") else ""
                    
                    if exam_question.question.category == Question.TEXTUAL:
                        answer_data["text"] = str(answer.content) if hasattr(answer, "content") else ""
                        
                if exam_question.question.category == Question.CHOICE:
                    answer_data["text"] = str(answer.question_option.text)
                    answer_data["selected_alternative_letter"] = self.get_alternative_letter(int(answer.index_alternative)) if exam.is_randomized else self.get_alternative_letter(int(answer.question_option.get_index()))
                
                if exam_question.question.category == Question.SUM_QUESTION:
                    alternative_letters = []
                    marked_options = SumAnswerQuestionOption.objects.filter(
                            sum_answer=answer,
                            checked=True
                        )
                    for option in marked_options:
                        alternative_letter = self.get_alternative_letter(int(option.question_option.index))
                        alternative_letters.append(alternative_letter)
                    
                    answer_data["alternative_letters"] = alternative_letters
                    answer_data["text"] = " ".join([option.question_option.text for option in marked_options])

            data["answers_json"].append(answer_data)

        ProofAnswer.objects.create(**data)
        
        return HttpResponseRedirect(reverse('answers:proof_of_answers', kwargs={ "pk": application_student.id }))
    
class AnswersPendentCorrectionTemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    template_name = 'answers/answers_pending.html'
    
    def dispatch(self, request, *args, **kwargs):
        
        answers = request.GET.getlist('answer_id')
        
        self.application_students = ApplicationStudent.objects.filter(
            file_answers__in=answers
        )

        return super().dispatch(request, *args, **kwargs)

    def get_application_student_details(self):
        subject_pks = self.request.GET.getlist('disciplinas', [])
        subjects_filter = Subject.objects.filter(pk__in=subject_pks) if subject_pks else []

        user = self.request.user
        if user.user_type == settings.TEACHER:
            teacher = user.inspector
            if self.object.correction_by_subject:  
                subjects = teacher.subjects.all()                
                queryset = self.application_students.get_annotation_count_answers_filter_subjects(subjects=subjects_filter or subjects, exclude_annuleds=True)
            else:          
                queryset = self.application_students.get_annotation_count_answers_filter_teacher(teacher=teacher, subjects=subjects_filter, exclude_annuleds=True)
        else:
            queryset = self.application_students.get_annotation_count_answers(subjects=subjects_filter, exclude_annuleds=True)
        
        queryset = queryset.annotate(
            has_suspicion_advantage=Subquery(
                Annotation.objects.filter(
                    application_student__pk=OuterRef('pk'),
                    suspicion_taking_advantage=True
                ).values('pk')[:1]
            )
        )

        return queryset.values(
            'application__pk',
            'student__name', 
            'student__enrollment_number', 
            'pk', 
            'total_answers',
            'is_omr',
            'start_time',
            'total_corrected_answers',
            'total_text_file_answers',
            'total_correct_answers',
            'total_incorrect_answers',
            'total_partial_answers',
            'total_grade',
            'has_suspicion_advantage'
        )

    def get_questions(self):
        questions = self.object.questions

        user = self.request.user
        if user.user_type == settings.TEACHER:
            teacher = user.inspector
            if self.object.correction_by_subject:
                questions = questions.filter(
                    examquestion__exam_teacher_subject__teacher_subject__subject__in=teacher.subjects.all()
                ).distinct()
            else:
                if teacher.can_correct_questions_other_teachers:
                    questions = questions.filter(
                        examquestion__exam_teacher_subject__teacher_subject__subject__in=teacher.subjects.all()
                    ).distinct()
                else:
                    questions = questions.filter(
                        examquestion__exam_teacher_subject__teacher_subject__teacher=teacher
                    ).distinct()

        return questions.availables(self.get_object())
        
    def get_subjects(self):
        
        exam_subjects = self.get_object().get_subjects()

        user = self.request.user
        
        if user.user_type == settings.TEACHER:
            return user.inspector.subjects.all().intersection(exam_subjects)

        return exam_subjects

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["applications_student"] = self.get_application_student_details() 
        return context