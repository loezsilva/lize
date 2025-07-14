from rest_framework import serializers

from fiscallizeon.integrations.models import SubjectCode
from fiscallizeon.subjects.models import Subject, SubjectRelation
from django.db.models import Q
from statistics import fmean

from ..models import ApplicationStudent


class ApplicationStudentResultSerializer(serializers.ModelSerializer):
    # student = serializers.CharField(source='student.name')
    # enrollment = serializers.CharField(source='student.enrollment_number')
    student = serializers.SerializerMethodField()
    enrollment = serializers.SerializerMethodField()
    exam = serializers.SerializerMethodField()
    exam_id = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    subject_id = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()
    exam_id_erp = serializers.SerializerMethodField()
    subject_id_erp = serializers.SerializerMethodField()
    stage_id_erp = serializers.SerializerMethodField()
    student_id = serializers.SerializerMethodField()
    application_id = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationStudent
        fields = (
            'student',
            'enrollment',
            'exam',
            'exam_id',
            'subject',
            'subject_id',
            'grade',
            'exam_id_erp',
            'subject_id_erp',
            'stage_id_erp',
            'student_id',
            'application_id',
        )

    def get_student(self, obj):
        return obj['student__name']

    def get_enrollment(self, obj):
        return obj['student__enrollment_number']

    def get_exam(self, obj):
        return obj['application__exam__name']

    def get_exam_id(self, obj):
        return obj['application__exam__id']

    def get_subject(self, obj):
        return obj['subject_name']

    def get_subject_id(self, obj):
        return obj['subject_id']

    def return_total_grade(self, application_student_id, subjects):
        application_students = ApplicationStudent.objects.filter(pk=application_student_id)
        
        return application_students.get_annotation_count_answers(
            subjects=subjects,
            only_total_grade=True,
            exclude_annuleds=True,
        )[0].total_grade

    def get_grade(self, obj):
        total_grade = None

        application_student = ApplicationStudent.objects.filter(id=obj['id']).first()
        
        if application_student.application.exam.related_subjects:
            if _relations := application_student.application.exam.relations.filter(
                client=application_student.student.client,
                subjects=obj['subject__id']
            ):
                for relation in SubjectRelation.objects.filter(pk__in=_relations):
                    
                    grades = []
                    
                    if relation.relation_type == SubjectRelation.SUM:
                        total_grade = self.return_total_grade(application_student_id=obj['id'], subjects=relation.subjects.all().values_list('id', flat=True))
                        
                    elif relation.relation_type == SubjectRelation.AVG:
                        for subject in relation.subjects.all():
                            grades.append(self.return_total_grade(application_student_id=obj['id'], subjects=[str(subject.id)]))
                        
                        total_grade = fmean(grades) if len(grades) else 0
            
            else:
                total_grade = self.return_total_grade(application_student_id=obj['id'], subjects=[obj['subject_id']])
        else:
            total_grade = self.return_total_grade(application_student_id=obj['id'], subjects=[obj['subject_id']])
            
        return total_grade

        # try:
        #     last_performance = Subject.objects.get(
        #         id=obj['subject_id']
        #     ).last_performance(application_student=obj['id'])
        #     return last_performance
        # except Subject.DoesNotExist:
        #     return None

    def get_exam_id_erp(self, obj):
        return obj['application__exam__id_erp']

    def _get_subject_code(self, subject):
        subject_code = SubjectCode.objects.filter(subject=subject).last()
        if subject_code:
            return subject_code.code
        elif not subject_code and subject.parent_subject:
            self._get_subject_code(subject.parent_subject)
        elif not subject.parent_subject:
            return None

    def get_subject_id_erp(self, obj):
        subject_id = obj['subject_id']
        subject = Subject.objects.get(id=subject_id)
        return self._get_subject_code(subject)

    def get_stage_id_erp(self, obj):
        return obj['application__exam__teaching_stage__code_export']

    def get_student_id(self, obj):
        return obj['student__id']

    def get_application_id(self, obj):
        return obj['application__id']


class ApplicationStudentAnswerSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    exam_question = serializers.SerializerMethodField()
    student_id = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()
    weight = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()

    class Meta:
        fields = (
            'id',
            'exam_question',
            'student_id',
            'content',
            'weight',
            'grade',
            'category',
        )

    def get_id(self, obj):
        return obj['id']

    def get_exam_question(self, obj):
        return obj['exam_question']

    def get_student_id(self, obj):
        return obj['student_id']

    def get_content(self, obj):
        return obj['content']

    def get_weight(self, obj):
        return obj['weight']

    def get_grade(self, obj):
        return obj['grade']

    def get_category(self, obj):
        return obj['category']
