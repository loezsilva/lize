import json
from rest_framework import serializers

from fiscallizeon.applications.models import Application, ApplicationDeadlineCorrectionResponseException
from fiscallizeon.students.serializers.students import StudentAndClassesSerializer
# from fiscallizeon.students.serializers.students import StudentAndClassesSerializer
from fiscallizeon.core.print_colors import *
from ..models import ApplicationStudent
from fiscallizeon.students.models import Student

class ApplicationSearchSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source='exam')
    students_count = serializers.SerializerMethodField()
    has_distribution = serializers.SerializerMethodField()
    coordinations = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = ('id', 'date', 'start', 'end', 'exam_name', 'students_count', 'has_distribution', 'coordinations')

    def get_students_count(self, obj):
        return obj.students.count()

    def get_has_distribution(self, obj):
        return True if obj.room_distribution else False

    def get_coordinations(self, obj):
        list_of_coordinations = []
        for school_classe in obj.school_classes.all():
            if not school_classe.coordination.id in list_of_coordinations:
                list_of_coordinations.append(school_classe.coordination.id)
        
        return list_of_coordinations

class ApplicationsStudentsCoordinationSerializer(serializers.ModelSerializer):
    
    students_count = serializers.SerializerMethodField()

    students = StudentAndClassesSerializer(many=True)

    class Meta:
        model = Application
        fields = ('id', 'students', 'students_count')

    def get_students_count(self, obj):
        return obj.students.count()
    
class ApplicationDuplicateSerializer(serializers.ModelSerializer):
    exam = serializers.CharField(source='exam.name')
    studentsCount = serializers.SerializerMethodField()
    sheetsExportingStatus = serializers.SerializerMethodField()
    sheetsExportingProgress = serializers.SerializerMethodField()
    studentStatsPermissionDate = serializers.SerializerMethodField()
    lastAnswerSheetGeneration = serializers.SerializerMethodField()
    schoolClasses = serializers.SerializerMethodField()
    answerSheetUrl = serializers.SerializerMethodField()
    inspectors = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = ('id', 'date', 'start', 'end',
                  'exam', 'studentsCount', 'category',
                  'subject', 'inspectors', 'duplicate_application',
                  'sheetsExportingStatus', 'sheetsExportingProgress',
                  'studentStatsPermissionDate', 'lastAnswerSheetGeneration',
                  'schoolClasses', 'answerSheetUrl')
        
    def get_data(self, obj):
        return obj.data.format
        
    def get_inspectors(self, obj):
        list_inspector = []
        for inspector in obj.inspectors.all():
                list_inspector.append(inspector.name)
        return list_inspector
    
    def get_studentsCount(self, obj):
        return obj.students.count()

    def get_sheetsExportingStatus(self, obj):
        return obj.sheet_exporting_status
    
    def get_sheetsExportingProgress(self, obj):
        return 0
    
    def get_studentStatsPermissionDate(self, obj):
        return obj.student_stats_permission_date
    
    
    def get_lastAnswerSheetGeneration(self, obj):
        return obj.last_answer_sheet_generation
    
    def get_schoolClasses(self, obj):
        list_school_classes = []
        for school_classe in obj.get_classes():
            list_school_classes.append(f"{school_classe.get('name')} - {school_classe.get('coordination__unity__name')}")
        return list_school_classes
    
    def get_answerSheetUrl(self, obj):
        return obj.answer_sheet.url if obj.answer_sheet else ''

class ApplicationSimpleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Application
        fields = ('id', 'date', 'start', 'end')
        
class ApplicationCheckExamSimpleSerializer(serializers.ModelSerializer):
    exam = serializers.CharField(source='exam.name')
    school_classes = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()
    
    def get_school_classes(self, obj):

        return [school_class.name for school_class in obj.school_classes.all()]
    
    def get_students(self, obj):
        return [student.name for student in obj.students.all()]  

    class Meta:
        model = Application
        fields = ('id', 'date', 'start', 'end', 'exam', 'school_classes',  'students')


class ApplicationDeadlineCorrectionResponseExceptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationDeadlineCorrectionResponseException
        fields = ('id', 'date', 'teacher')


class ApplicationStudentStudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ('id', 'name', 'enrollment_number')

class ApplicationStudentSerializer(serializers.ModelSerializer):
    student = ApplicationStudentStudentSerializer()
    omr_scan_url = serializers.JSONField(source='get_files_urls', read_only=True)
    urls = serializers.JSONField(read_only=True)
    
    class Meta:
        model = ApplicationStudent
        fields = ('id', 'is_omr', 'student', 'omr_scan_url', 'urls')