from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication

from django.utils import timezone
from django.db.models import ProtectedError

from statistics import fmean
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.students.models import Student
from fiscallizeon.students.serializers2.students import StudentSerializer, StudentCreateUpdateSerializer, StudentSchoolClassesSerializer
from fiscallizeon.core.paginations import LimitOffsetPagination
from fiscallizeon.core.api import CsrfExemptSessionAuthentication


@extend_schema(tags=['Alunos'])
class StudentsViewSet(viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    pagination_class = LimitOffsetPagination
    authentication_classes = [CsrfExemptSessionAuthentication, TokenAuthentication]
    filterset_fields = ('classes__school_year',)
    
    @extend_schema(request=StudentCreateUpdateSerializer) # Não remova
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    

    @extend_schema(request=StudentCreateUpdateSerializer) # Não remova
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def get_queryset(self):
        return Student.objects.filter(
            client=self.request.user.client
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(
                {"detail": "Este aluno não pode ser deletado pois está relacionado \
                 a outros registros. Utilize a função api/v2/students/{id}/disable/ \
                    para desativar o aluno"},
                status=status.HTTP_400_BAD_REQUEST
            )

    def perform_create(self, serializer):
        instance = serializer.save(
            client=self.request.user.client
        )
        data = self.request.data
        user = instance.user
        
        if data.get('username') and data.get('username') != 'string':
            user.username = data.get('username')
            user.save()
            
        if data.get('password') and data.get('password') != 'string':
            user.set_password(data.get('password'))
            user.must_change_password = True
            user.save()
        
    def perform_update(self, serializer):
        instance = serializer.save()
        data = self.request.data
        user = instance.user
        if user:
            
            if data.get('username') and data.get('username') != 'string':
                if user.username != data.get('username'):
                    user.username = data.get('username')
                    user.save()
                    
            if data.get('password') and data.get('password') != 'string':
                user.set_password(data.get('password'))
                user.must_change_password = True
                user.save()
    
    @action(detail=True, methods=['post'])
    def disable(self, request, pk):
        student = self.get_object()
        student.user.is_active = False
        student.user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def enable(self, request, pk):
        student = self.get_object()
        student.user.is_active = True
        student.user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def set_classes(self, request, pk):
        student = self.get_object()
        serializer = StudentSchoolClassesSerializer(data=request.data)
        if serializer.is_valid():
            current_classes = SchoolClass.objects.filter(
                students__in=[student],
                school_year=timezone.now().year
            )

            new_classes = SchoolClass.objects.filter(pk__in=serializer.data['school_classes'])
            school_years = new_classes.values_list('school_year', flat=True)
            
            if len(set(school_years)) > 1:
                return Response(
                    {'error': 'O aluno deve ser inserido em turmas de mesmo ano letivo'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            for current_class in current_classes:
                current_class.students.remove(student)
                current_class.save()
                try:
                    for application in current_class.applications.all():
                        if application.student_can_be_remove_or_add:
                            application.students.remove(student.pk)
                except:
                    pass
            for school_class in new_classes:
                school_class.students.add(student)
                for application in school_class.applications.all():
                    if student not in application.students.all() and not application.is_time_finished and application.student_can_be_remove_or_add:
                        application.students.add(student.pk)

            return self.retrieve(request, pk)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=False, methods=['POST'])
    def get_exams(self, request, pk=None):
        from rest_framework import serializers
        from fiscallizeon.exams.models import Exam
        from fiscallizeon.subjects.models import Subject
        
        students = Student.objects.filter(client__in=self.request.user.get_clients_cache(), id_erp__in=request.data).distinct()
        
        class ExamSerializer(serializers.ModelSerializer):
            
            subjects = serializers.SerializerMethodField()
            students = serializers.SerializerMethodField()
            
            class Meta:
                model = Exam
                fields = ['id', 'name', 'subjects', 'students']
            
            def get_students(self, exam):
                class SimpleStudentSerializer(serializers.ModelSerializer):
                    performance = serializers.SerializerMethodField()
                    class Meta:
                        model = Student
                        fields = ['id', 'id_erp', 'performance']
                        
                    def get_performance(self, obj):
                        performances = []
                        applications_student = obj.applicationstudent_set.filter(application__exam=exam)
                        for application_student in applications_student:
                            student_performance = application_student.get_performance()
                            performances.append(student_performance)
                        return fmean(performances) if len(performances) else 0
                    
                return SimpleStudentSerializer(instance=students.filter(applicationstudent__application__exam=exam), many=True).data
            
            def get_subjects(self, obj):
                return Subject.objects.filter(pk__in=obj.get_subjects()).distinct().values('id', 'name')
        
        exams = Exam.objects.filter(application__applicationstudent__student__in=students).distinct()
        
        availables_exams = []
        for exam in exams:
            # if not exam.has_opened_applications: # Não remover essa condição, ela que define que só vai mostrar provas que já acabaram
            availables_exams.append(exam)
        
        return Response(ExamSerializer(instance=availables_exams, many=True).data)
    
    @action(detail=False, methods=['POST'])
    def get_score(self, request, pk=None):
        from rest_framework import serializers
        from fiscallizeon.exams.models import Exam
        from fiscallizeon.applications.models import ApplicationStudent
        from fiscallizeon.subjects.models import Subject
        import numpy as np
        
        exam_id  = request.data.get('exam')
        student_id = request.data.get('student')
        subjects = request.data.get('subjects')
        
        scores = {
            "subjects": [],
        }
        
        try:
            exam = Exam.objects.get(id=exam_id)
            if application_student := ApplicationStudent.objects.filter(application__duplicate_application=False, application__exam=exam, student=student_id).first():
                scores["subjects"] = [
                    {
                        "id": subject.id,
                        "max_score": subject.get_max_score(exam),
                        "score": application_student.get_total_grade(subject),
                        "score_active": None,
                    } for subject in exam.get_subjects().filter(pk__in=subjects)
                ]
        except Exception as e:
            print("🚀 ~ file: students.py:154 ~ e:", e)
        return Response(scores)
    
    @action(detail=False, methods=['POST'])
    def get_performance_subjects(self, request, pk=None):
        from fiscallizeon.exams.models import Exam
        from fiscallizeon.applications.models import ApplicationStudent
        
        exam_id  = request.data.get('exam')
        student_id = request.data.get('student')
        get_exam_score = request.data.get('get_exam_score')
        
        scores = {
            "exam": None,
            "subjects": [],
        }

        exam = Exam.objects.get(id=exam_id)
        application_student = ApplicationStudent.objects.filter(application__exam=exam, student=student_id).first()

        this_exam_teacher_subjects = exam.examteachersubject_set
        exam_subjects = exam.get_subjects()

        # Esse if realiza a exclude do item de língua estrangeira que não foi escolhido
        if this_exam_teacher_subjects.filter(is_foreign_language=True).exists():

            foreign_language_options = this_exam_teacher_subjects.filter(is_foreign_language=True).order_by('order')
            first_option = foreign_language_options.first().teacher_subject.subject
            last_option = foreign_language_options.last().teacher_subject.subject

            if application_student.foreign_language == ApplicationStudent.ENGLISH:
                exam_subjects = exam_subjects.exclude(pk=last_option.pk)
            else:
                exam_subjects = exam_subjects.exclude(pk=first_option.pk)
        
        try:
            if application_student:

                scores["exam"] = {
                    "id": str(exam.id),
                    "name": exam.name,
                    "performance": application_student.get_performance() if get_exam_score else None,
                }
                scores["subjects"] = [
                    {
                        "id": subject.id,
                        "name": subject.name,
                        "performance": application_student.get_performance(subject),
                    } for subject in exam_subjects
                ]
        except Exception as e:
            print("🚀 ~ file: students.py:154 ~ e:", e)
        return Response(scores)
    
    @action(detail=False, methods=['POST'])
    def get_performances(self, request, pk=None):
        from rest_framework import serializers
        from fiscallizeon.exams.models import Exam
        from fiscallizeon.applications.models import ApplicationStudent
        from fiscallizeon.subjects.models import Subject
        import numpy as np
        
        data = request.data
        
        exams_ids = list(map(lambda x: x['id'], data['exams']))
        students_ids = list(map(lambda x: x['aluno_matricula'], data['students']))
        subjects_ids = data['subjects']
        
        sum_exams_notes = data['sum_exams_notes']
        sum_subjects_notes = data['sum_subjects_notes']
        
        students = Student.objects.filter(enrollment_number__in=students_ids, client__in=self.request.user.get_clients_cache()).distinct()
        exams = Exam.objects.filter(id__in=exams_ids).distinct()
        
        students_performances = []
        
        for student in students:
            score_sum = 0
            
            student_scores = []
            
            for exam in exams:
                
                if application_student := ApplicationStudent.objects.filter(student=student, application__exam=exam).first():
                    
                    if len(subjects_ids):
                        
                        for subject_id in subjects_ids:
                            
                            student_subject_score = application_student.get_score(subject=Subject.objects.get(id=subject_id))
                            
                            if sum_subjects_notes:
                                score_sum += student_subject_score
                            else:
                                student_scores.append(student_subject_score)
                            
                    else:
                        student_score = application_student.get_score()
                        if sum_exams_notes:
                            score_sum += student_score
                        else:
                            student_scores.append(application_student.get_score())
                    
            if sum_exams_notes or sum_subjects_notes:
                score = score_sum
            else:
                score = fmean(student_scores) if len(student_scores) else 0
                    
            students_performances.append({
                "enrollment_number": student.enrollment_number,
                "score": score
            })
                    
        return Response(students_performances)