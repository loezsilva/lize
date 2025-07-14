from django.db import transaction

from rest_framework import serializers

from fiscallizeon.students.models import Student

from ..models import Application, ApplicationStudent


class FilteredStudentPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        request = self.root.context.get('request', None)
        if request:
            return Student.objects.filter(
                client__in=request.user.get_clients_cache(),
                user__is_active=True,
            )
        return super().get_queryset()


class ApplicationSerializer(serializers.ModelSerializer):
    students = FilteredStudentPrimaryKeyRelatedField(
        many=True,
        queryset=Student.objects.none(),
        required=False,
    )

    class Meta:
        model = Application
        fields = (
            'id',
            'exam',
            'date',
            'start',
            'end',
            'date_end',
            # 'min_time_finish',
            # 'min_time_pause',
            # 'max_time_tolerance',
            'block_after_tolerance',
            'orientations',
            'category',
            'student_stats_permission_date',
            'priority',
            'release_result_at_end',
            'show_result_only_for_started_application',
            'deadline_for_correction_of_responses',
            'deadline_for_sending_response_letters',
            'students',
            'school_classes',
        )

    def create(self, validated_data):
        students_data = validated_data.pop('students', [])
        school_classes_data = validated_data.pop('school_classes', [])
        
        with transaction.atomic():
            application = Application.objects.create(**validated_data)
            application_student_list = []
            for student_data in students_data:
                student = student_data
                application_student_list.append(ApplicationStudent(application=application, student=student))
            
            if application_student_list:
                ApplicationStudent.objects.bulk_create(application_student_list)

            application.school_classes.set(school_classes_data)

            return application