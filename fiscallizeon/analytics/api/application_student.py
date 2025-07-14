from statistics import fmean
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response

from rest_framework.generics import ListAPIView
from rest_framework.renderers import JSONRenderer
from fiscallizeon.analytics.api.serializers.application_student import ApplicationStudentGeneralPerformanceSerialize, ApplicationStudentSerializer
from fiscallizeon.bncc.serializers.ability import AbilitySerializerAnilytics
from fiscallizeon.bncc.serializers.competence import CompetenceSimpleSerializer
from fiscallizeon.core.utils import CheckHasPermission, SimpleAPIPagination
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.applications.models import ApplicationStudent
from django.db.models import Q, Case, F, When

from django_filters.rest_framework import DjangoFilterBackend
from fiscallizeon.bncc.models import Abiliity, Competence
from fiscallizeon.exams.models import Exam
from fiscallizeon.subjects.models import Subject, Topic
from fiscallizeon.subjects.serializers.subjects import SubjectVerySimpleSerializer
from fiscallizeon.subjects.serializers.topics import TopicSimpleSerializer
from fiscallizeon.bncc.utils import get_bncc


class ApplicationStudentListAPIView(LoginRequiredMixin, CheckHasPermission, ListAPIView):
    renderer_classes = [JSONRenderer]
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    serializer_class = ApplicationStudentSerializer
    queryset = ApplicationStudent.objects.all().order_by('student__name', '-application__date')
    authentication_classes = (CsrfExemptSessionAuthentication, )
    page_size = 50
    filter_backends = [DjangoFilterBackend]
    filterset_fields = { 'application__exam' : ['in', 'exact'] }


    def get_serializer_context(self):
        context = super(ApplicationStudentListAPIView, self).get_serializer_context()
        context["question"] = self.request.GET.get('question')
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        
        return queryset
    

class ApplicationStudentAnalysisViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationStudentGeneralPerformanceSerialize
    queryset = ApplicationStudent.objects.all()
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    def get_queryset(self):
        queryset = ApplicationStudent.objects.filter(student__client__in=self.request.user.get_clients_cache())
        return queryset
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['classes'] = self.request.GET.get('classes').split(',') if self.request.GET.get('classes') else []
        context['unities'] = self.request.GET.get('unities').split(',') if self.request.GET.get('unities') else []
        
        return context
    
    def get_exam_questions(self, exam=None, return_subjects=False):
        if not exam:
            exam = self.get_object().application.exam

        exam_questions = exam.examquestion_set.availables()

        user = self.request.user
        if user.user_type == settings.TEACHER:
            teacher = user.inspector
            if exam.correction_by_subject:
                exam_questions = exam_questions.filter(
                    Q(exam_teacher_subject__teacher_subject__subject__in=teacher.subjects.all()) |
                    Q(question__subject__in=teacher.subjects.all())
                ).distinct()
            else:
                exam_questions = exam_questions.filter(
                    Q(exam_teacher_subject__teacher_subject__teacher=teacher) |
                    Q(question__subject__in=teacher.subjects.all())
                ).distinct()
                
        if return_subjects:
            if exam.is_abstract:
                subjects_ids = exam_questions.values_list('question__subject', flat=True).distinct()
            else:
                subjects_ids = exam_questions.values_list('exam_teacher_subject__teacher_subject__subject', flat=True).distinct()
            return subjects_ids
            
        return exam_questions.order_by('exam_teacher_subject__order', 'order')

    def get_bncc_summary(self, application_student, bncc, exam_pk=None):
        '''
            Pega a performance de aluno em todos os cadernos que ele participou
            Caso o parametro exam_pk seja passado, pega apenas a performance do exam especificado
        '''
        exams = Exam.objects.filter(
            Q(pk=exam_pk) if exam_pk else Q(),
            Q(application__applicationstudent__student=application_student.student),
            Q(
                Q(application__applicationstudent__start_time__isnull=False) |
                Q(application__applicationstudent__is_omr=True)
            ),
        ).order_by('application__date').distinct()
        
        if type(bncc) == Abiliity:
            exams = exams.filter(questions__abilities=bncc)
        elif type(bncc) == Competence:
            exams = exams.filter(questions__competences=bncc)
        elif type(bncc) == Topic:
            exams = exams.filter(questions__topics=bncc)
        
        exams_performance = []
        
        for exam in exams:
            applications_student = ApplicationStudent.objects.filter(student=application_student.student, application__exam=exam).order_by('application__date')
            
            summary = {
                "id": exam.id,
                "name": exam.name,
                "subject": {
                    "id": bncc.subject.id if bncc.subject else '',
                    "name": bncc.subject.__str__(),
                },
                "dates": [date.strftime('%d/%m/%Y') for date in applications_student.values_list('application__date', flat=True).distinct()],
                "performance": fmean([application_student.get_performance(bncc_pk=bncc.pk) for application_student in applications_student])
            }
            
            if exam_pk:
                return summary
            
            exams_performance.append(summary)
        
        return exams_performance
        
    @action(detail=True, methods=['get'])
    def bncc_summary(self, request, pk=None):
        exam_pk = self.request.GET.get('exam_pk', None)
        application_student = ApplicationStudent.objects.get(pk=pk)
        bncc = get_bncc(self.request.GET.get('bncc_pk'))
        if not bncc:
            return Response('Erro ao encontrar a bncc, alguns parâmentros não foram informados.', status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_bncc_summary(application_student, bncc, exam_pk), status=status.HTTP_200_OK)
        
    @action(detail=True, methods=['get'])
    def subject_summary(self, request, pk=None):
        exam_pk = self.request.GET.get('exam_pk', None)
        application_student = ApplicationStudent.objects.get(pk=pk)
        subject_pk = self.request.GET.get('subject_pk', None)
        
        if not subject_pk:
            return Response('Erro ao encontrar a disciplina, alguns parâmentros não foram informados.', status=status.HTTP_400_BAD_REQUEST)
        
        '''
            Pega a performance de aluno em todos os cadernos que ele participou
            Caso o parametro exam_pk seja passado, pega apenas a performance do exam especificado
        '''
        subject = Subject.objects.get(pk=subject_pk)
        exams = Exam.objects.filter(
            Q(pk=exam_pk) if exam_pk else Q(),
            Q(application__applicationstudent__student=application_student.student),
            Q(
                Q(application__applicationstudent__start_time__isnull=False) |
                Q(application__applicationstudent__is_omr=True)
            ),
            Q(
                Q(examteachersubject__teacher_subject__subject__subject=subject) |
                Q(questions__subject=subject)
            )
        ).order_by('application__date').distinct()[:10]
        
        exams_performance = []
        
        for exam in exams:
            applications_student = ApplicationStudent.objects.filter(
                Q(student=application_student.student, application__exam=exam),
                Q(
                    Q(start_time__isnull=False) |
                    Q(is_omr=True)
                )
            )
            summary = {
                "id": exam.id,
                "name": exam.name,
                "dates": [date.strftime('%d/%m/%Y') for date in applications_student.values_list('application__date', flat=True).distinct()],
                "performance": fmean([application_student.get_performance(subject=subject) for application_student in applications_student])
            }
            
            if exam_pk:
                return Response(summary, status=status.HTTP_200_OK)
            
            exams_performance.append(summary)
        
        return Response(exams_performance, status=status.HTTP_200_OK)
        
        
    @action(detail=False, methods=['get'])
    def get_correct_questions(self, request, pk=None):
        include_partial = self.request.GET.get('include_partial', True)
        application_student = ApplicationStudent.objects.get(pk=self.request.GET.get('application_student_pk')) if self.request.GET.get('application_student_pk') else None
        
        if self.request.GET.get('applications_student'):
            students = []
            applications_student = ApplicationStudent.objects.filter(pk__in=self.request.GET.getlist('applications_student'))
            
            
            for application_student in applications_student:
                subjects_ids = self.request.GET.getlist('q_subjects') if self.request.GET.get('q_subjects') else self.get_exam_questions(exam=application_student.application.exam, return_subjects=True)
                students.append({
                    "id": application_student.id,
                    "right_questions": application_student.get_correct_questions(include_partial=include_partial, subjects_ids=subjects_ids)
                })
            return Response(students)
        
        if not application_student:
            return Response('Não há aluno', status=status.HTTP_404_NOT_FOUND)
        
        subjects_ids = self.request.GET.getlist('q_subjects') if self.request.GET.get('q_subjects') else self.get_exam_questions(exam=application_student.application.exam, return_subjects=True)
        
        return Response(application_student.get_correct_questions(include_partial=include_partial, subjects_ids=subjects_ids), status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def get_exams_historical_performance(self, request, pk=None):
        application_student = self.get_object()
        
        exams_performance = []
        
        exams = Exam.objects.filter(
            Q(category=application_student.application.exam.category),
            Q(application__applicationstudent__student=application_student.student), 
            Q(teacher_subjects__subject__in=self.get_exam_questions(return_subjects=True)),
            Q(application__date__year=self.request.GET.get('year')) if self.request.GET.get('year') else Q(),
            Q(
                Q(application__applicationstudent__start_time__isnull=False) |
                Q(application__applicationstudent__is_omr=True),
            )
        ).order_by('application__date').distinct()[:10]
            
        for exam in exams:
            applications_student = ApplicationStudent.objects.filter(student=application_student.student, application__exam=exam)
            performances = [application_student.get_performance() for application_student in applications_student]
            exams_performance.append({
                "name": exam.name,
                "dates": [date.strftime('%d/%m/%Y') for date in applications_student.values_list('application__date', flat=True).distinct()],
                "questions_count": exam.questions.count(),
                "performance": fmean(performances),  
            })

        return Response(exams_performance, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def get_bncc_and_subjects_summary_exams(self, request, pk=None):
        application_student = self.get_object()
        application_exam = application_student.application.exam
        exam_questions = self.get_exam_questions()
        
        q_subjects = self.request.GET.getlist('q_subjects', None)
        
        exams = Exam.objects.filter(
            Q(category=application_exam.category),
            Q(application__applicationstudent__student=application_student.student),
            Q(examquestion__question__subject__in=exam_questions.values_list('question__subject')) if application_exam.is_abstract else Q(examquestion__exam_teacher_subject__teacher_subject__subject__in=exam_questions.values_list('exam_teacher_subject__teacher_subject__subject').distinct()),
            Q(
                Q(application__applicationstudent__start_time__isnull=False) | 
                Q(application__applicationstudent__is_omr=True)
            )
        ).order_by('application__date').distinct()
        
        all_subjects = Subject.objects.filter(
            Q(pk__in=exam_questions.values_list(
                'question__subject' if application_exam.is_abstract else 'exam_teacher_subject__teacher_subject__subject'
            )) if not q_subjects else Q(pk__in=q_subjects)
        ).distinct()
        
        subject_exams = exams[:10]
        
        all_topics = Topic.objects.filter(pk__in=exam_questions.values_list('question__topics')).distinct()
        topic_exams = exams.filter(questions__topics__in=all_topics)[:10]
        
        all_abilities = Abiliity.objects.filter(pk__in=exam_questions.values_list('question__abilities')).distinct()
        abilities_exams = exams.filter(questions__abilities__in=all_abilities)[:10]
        
        all_competences = Competence.objects.filter(pk__in=exam_questions.values_list('question__competences')).distinct()
        competences_exams = exams.filter(questions__competences__in=all_competences)[:10]
        
        subjects = {
            "list": [],
            "exams": [
                {
                    "id": exam.id,
                    "name": exam.name,
                } for exam in subject_exams
            ],
        }
        
        topics = {
            "list": [],
            "exams": [
                {
                    "id": exam.id,
                    "name": exam.name,
                } for exam in topic_exams
            ],
        }
        abilities = {
            "list": [],
            "exams": [
                {
                    "id": exam.id,
                    "name": exam.name,
                } for exam in abilities_exams
            ],
        }
        competences = {
            "list": [],
            "exams": [
                {
                    "id": exam.id,
                    "name": exam.name,
                } for exam in competences_exams
            ],
        }
        
        if self.request.GET.get('only_subjects'):
            for subject in all_subjects:
                
                subject_serialized = SubjectVerySimpleSerializer(instance=subject).data
                subject_serialized['exams_performance'] = []
                for exam in subject_exams:
                    applications_student = exam.get_application_students_started().filter(student=application_student.student)
                    applications_student_performances = [application_student.get_performance(subject=subject) for application_student in applications_student]
                    
                    if applications_student_performances:
                        subject_serialized['exams_performance'].append({
                            "id": exam.id,
                            "name": exam.name,
                            "dates": [date.strftime('%d/%m/%Y') for date in applications_student.values_list('application__date', flat=True).distinct()],
                            "performance": fmean(applications_student_performances),
                        })
                    else:
                        subject_serialized['exams_performance'].append({"performance": 0})
                        
                subjects['list'].append(subject_serialized)
                
        else:
            for topic in all_topics:
                topic_serialized = TopicSimpleSerializer(topic).data
                topic_serialized['exams_performance'] = []
                
                for exam in topic_exams:
                    summary = self.get_bncc_summary(application_student, topic, exam.pk)

                    if summary:
                        topic_serialized['exams_performance'].append(summary)
                    else:
                        topic_serialized['exams_performance'].append({"performance": 0})
                        
                topics['list'].append(topic_serialized)
                
            for ability in all_abilities:
                
                ability_serialized = AbilitySerializerAnilytics(ability).data
                ability_serialized['exams_performance'] = []
                
                for exam in abilities_exams:
                    summary = self.get_bncc_summary(application_student, ability, exam.pk)
                    if summary:
                        ability_serialized['exams_performance'].append(summary)
                    else:
                        ability_serialized['exams_performance'].append({"performance": 0})
                        
                abilities['list'].append(ability_serialized)
                
            for competence in all_competences:
                
                competence_serialized = CompetenceSimpleSerializer(competence).data
                competence_serialized['exams_performance'] = []
                
                for exam in competences_exams:
                    summary = self.get_bncc_summary(application_student, competence, exam.pk)
                    if summary:
                        competence_serialized['exams_performance'].append(summary)
                    else:
                        competence_serialized['exams_performance'].append({"performance": 0})

                competences['list'].append(competence_serialized)
                
        return Response({
            "topics": topics,
            "abilities": abilities,
            "competences": competences,
            "subjects": subjects,
        }, status=status.HTTP_200_OK)
        
    @action(detail=True, methods=['get'])
    def get_performance_in_bnccs_and_subjects(self, request, pk=None):
        application_student = self.get_object()
        exam = application_student.application.exam
        
        subjects = []
        subjects_filtered = Subject.objects.filter(
            pk__in=self.get_exam_questions().values_list(
                'question__subject' if exam.is_abstract else 'exam_teacher_subject__teacher_subject__subject'
            )
        ).distinct()
        subjects_filtered = subjects_filtered.filter(
            Q(pk__in=self.request.GET.getlist('q_subjects')) if self.request.GET.get('q_subjects') else Q()
        )
        
        for subject in subjects_filtered:
            subjects.append({
                "id": subject.id,
                "name": subject.__str__(),
                "performance": application_student.get_performance(subject=subject)
            })
        
        topics = []
        for topic in Topic.objects.filter(pk__in=self.get_exam_questions().filter(
                Q(question__subject__in=self.request.GET.getlist('q_subjects')) if exam.is_abstract else Q(exam_teacher_subject__teacher_subject__subject__in=self.request.GET.getlist('q_subjects')) if self.request.GET.get('q_subjects') else Q()
            ).availables().values_list('question__topics').distinct()).distinct():
            topics.append({
                "id": topic.id,
                "name": topic.name,
                "performance": application_student.get_performance(bncc_pk=topic.id)
            })
        
        abilities = []
        for ability in Abiliity.objects.filter(pk__in=self.get_exam_questions().filter(
                Q(question__subject__in=self.request.GET.getlist('q_subjects')) if exam.is_abstract else Q(exam_teacher_subject__teacher_subject__subject__in=self.request.GET.getlist('q_subjects')) if self.request.GET.get('q_subjects') else Q()
            ).availables().values_list('question__abilities').distinct()).distinct():
            abilities.append({
                "id": ability.id,
                "text": ability.text,
                "performance": application_student.get_performance(bncc_pk=ability.id)
            })
        competences = []
        for competence in Competence.objects.filter(pk__in=self.get_exam_questions().filter(
                Q(question__subject__in=self.request.GET.getlist('q_subjects')) if exam.is_abstract else Q(exam_teacher_subject__teacher_subject__subject__in=self.request.GET.getlist('q_subjects')) if self.request.GET.get('q_subjects') else Q()
            ).availables().values_list('question__competences').distinct()).distinct():
            competences.append({
                "id": competence.id,
                "text": competence.text,
                "performance": application_student.get_performance(bncc_pk=competence.id)
            })
            
        return Response({
            "subjects": subjects,
            "topics": topics,
            "abilities": abilities,
            "competences": competences,
        })