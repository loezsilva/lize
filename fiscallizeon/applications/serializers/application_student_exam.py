
from rest_framework import serializers

from django.conf import settings
from django.db.models import F, Case, When, Value, UUIDField, Q, JSONField, OuterRef
from django.db.models.functions import JSONObject
from django.contrib.postgres.expressions import ArraySubquery


from fiscallizeon.applications.models import ApplicationStudent, RandomizationVersion
from fiscallizeon.exams import json_utils
from fiscallizeon.questions.serializers.questions import QuestionExamSerializer
from fiscallizeon.questions.models import Question
from fiscallizeon.answers.models import FileAnswer
from fiscallizeon.subjects.models import Subject
from django.forms.models import model_to_dict


class ApplicationStudentExamSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()
    omr_scan_url = serializers.SerializerMethodField()
    randomization_version = serializers.SerializerMethodField()
    fullname = serializers.CharField(source='student.name')
    enrollment_number = serializers.CharField(source='student.enrollment_number')
    user_pk = serializers.SerializerMethodField()
    exam_name = serializers.CharField(source='application.exam.name')
    is_abstract = serializers.BooleanField(source='application.exam.is_abstract')
    can_be_corrected = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationStudent
        fields = (
            'pk', 
            'questions', 
            'fullname', 
            'user_pk', 
            'start_time', 
            'end_time', 
            'device', 
            'empty_questions', 
            'is_omr', 
            'omr_scan_url', 
            'exam_name', 
            'is_abstract', 
            'enrollment_number',
            'randomization_version',
            'can_be_corrected',
            'duplicated_answers',
            'empty_option_questions',
        )

    def get_user_pk(self, application_student):
        return application_student.student.user.pk if application_student.student.user else ''
        
    def get_randomization_version(self, application_student):
        
        if application_student.application.exam.is_randomized and application_student.read_randomization_version:
            randomization_version = RandomizationVersion.objects.get(
                application_student=application_student,
                version_number=application_student.read_randomization_version
            )         
            return {
                "id": randomization_version.id,
                "exam_json": randomization_version.exam_json
            }
        return None

    def get_questions(self, application_student):
        
        questions = Question.objects.availables(
            self.instance.application.exam
        ).get_application_student_report(
            application_student
        ).filter(
            examquestion__exam=self.instance.application.exam
        ).annotate(
            exam_teacher_subject=F('examquestion__exam_teacher_subject__id'),
            teacher_subject_id=F('examquestion__exam_teacher_subject__teacher_subject__subject__id'),
        ).order_by(
            'examquestion__exam_teacher_subject__order', 'examquestion__order', 'created_at'
        ).distinct()

        request = self.context['request']
        subjects_pk = request.query_params.getlist('subjects', None)
        randomization_version = self.get_randomization_version(application_student)

        if subjects_pk:
            questions.filter(Q(subject__in=subjects_pk) if application_student.application.exam.is_abstract else Q(teacher_subject_id__in=subjects_pk))
            
        user =  self.context['request'].user
        if user.user_type == settings.TEACHER:
            teacher = user.inspector
            if application_student.application.exam.correction_by_subject:
                questions = questions.filter(
                    examquestion__exam_teacher_subject__teacher_subject__subject__in=teacher.subjects.all().distinct(),
                    examquestion__exam=self.instance.application.exam,
                ).distinct()
            else:
                questions = questions.filter(
                    examquestion__exam=self.instance.application.exam,
                ).distinct()

                if user.inspector.can_correct_questions_other_teachers:
                    questions = questions.filter(
                        examquestion__exam_teacher_subject__teacher_subject__subject__in=teacher.subjects.all().distinct(),
                    ).distinct()
                else:
                    questions = questions.filter(
                        examquestion__exam_teacher_subject__teacher_subject__teacher=teacher,
                    ).distinct()
                    
        if randomization_version:
            questions_json = json_utils.convert_json_to_choice_questions_list(randomization_version.get('exam_json'))
            questions_pks = [question['pk'] for question in questions_json]
            preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(questions_pks)])
            questions = questions.order_by(preserved)

        if user.user_type in [settings.TEACHER, settings.COORDINATION]:
            questions = questions.annotate(
                suggestions=ArraySubquery(
                    FileAnswer.objects.filter(
                        student_application=application_student,
                        question=OuterRef('pk'),
                        ai_grade__isnull=False,
                        ai_teacher_feedback__isnull=False,
                    )[:1].values(
                        json=JSONObject(
                            grade="ai_grade", 
                            comment="ai_teacher_feedback", 
                            teacher_feedback="ai_student_feedback"
                        )
                    )
                )
            )

        serializer = QuestionExamSerializer(questions.annotate(
            randomization_version_pk=Value(randomization_version.get('id') if randomization_version else None, output_field=UUIDField()),
            exam_id=Value(application_student.application.exam.id)
        ).distinct(), many=True)
        return serializer.data

    def get_omr_scan_url(self, application_student):
        return application_student.get_files_urls()
    
    def get_can_be_corrected(self, application_student):
        is_teacher = self.context['request'].user.user_type == settings.TEACHER
        return application_student.can_be_corrected(self.context['request'].user.inspector if is_teacher else None)