from statistics import fmean
from rest_framework import serializers
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.applications.serializers.application import ApplicationSimpleSerializer
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.clients.models import Unity
from fiscallizeon.questions.models import Question
from fiscallizeon.students.serializers.students import StudentSerializerSimple

from fiscallizeon.subjects.models import Subject

class ApplicationStudentSerializer(serializers.ModelSerializer):
    
    student = StudentSerializerSimple()
    application = ApplicationSimpleSerializer()
    alternatives = serializers.SerializerMethodField()
    question = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationStudent
        fields = (
            'id',
            'student',
            'application',
            'alternatives',
            'question',
        )

    def get_question(self, obj):

        if self.context['question']:
        
            selected_question = Question.objects.get(id=self.context['question'])
            
            option_answer = obj.option_answers.filter(question_option__question=selected_question).order_by('-created_at') if selected_question.get_category_display() == 'Objetiva' else None
            file_answer = obj.option_answers.filter(question=selected_question).order_by('-created_at') if selected_question.get_category_display() == 'Discursiva' else None
            textual_answer = obj.option_answers.filter(question=selected_question).order_by('-created_at') if selected_question.get_category_display() == 'Arquivo anexado' else None

            question = {
                'aswered': True if option_answer or file_answer or textual_answer else False,
                'option_answer_id': option_answer.first().question_option.id if option_answer else None,
                'file_answer_id': file_answer.first().id if file_answer else None,
                'textual_answer_id': textual_answer.first().id if textual_answer else None,
            }
        
            return question
        
        else:
        
            return None

    def get_alternatives(self, obj):
        if self.context['question']:
            alternatives = []
            for alternative in Question.objects.get(pk=self.context['question']).alternatives.all():
                answer = alternative.optionanswer_set.filter(student_application=obj).order_by('-created_at')

                _alternative = {
                    'id': alternative.id,
                    'is_correct': alternative.is_correct,
                    'answered': True if answer.exists() and answer.exists() else False,
                    'selected_alternative_id': answer.first().question_option.id if answer.exists() else '',
                    'hit': True if answer.exists() and answer.first().question_option.id and alternative.id else False,
                }
                alternatives.append(_alternative)
            
            return alternatives
        
        else: 
        
            return []
        

class ApplicationStudentGeneralPerformanceSerialize(serializers.ModelSerializer):
    general_performance = serializers.SerializerMethodField()
    classes_performance = serializers.SerializerMethodField()
    unities_performance = serializers.SerializerMethodField()
    
    class Meta:
        model = ApplicationStudent
        fields = ('general_performance', 'classes_performance', 'unities_performance')
        
    def get_classes_performance(self, obj):
        classes_list = self.context['classes'] or []
        q_subjects = self.context['q_subjects'] if hasattr(self.context, 'q_subjects') else None
        classes = SchoolClass.objects.filter(id__in=classes_list)
        classes_summary = []
        
        exam = obj.application.exam
        
        if not exam:
            return []
        
        for classe in classes:
            classe_object = {
                "name": classe.__str__(),
                "performance": 0
            }
            exam.generate_classes_performances(classe=classe)
                        
            if q_subjects:
                subjects = Subject.objects.filter(pk__in=q_subjects)
                subjects_performances = []
                applications_student = ApplicationStudent.objects.filter(application__exam=exam, student__classes=classe)
                
                for subject in subjects:
                    students_performances = []
                    for application_student in applications_student:                        
                        students_performances.append(application_student.get_performance(subject=subject))
                    
                    if students_performances:
                        subjects_performances.append(fmean(students_performances))
                
                classe_object['performance'] = fmean(subjects_performances) if subjects_performances else 0
                
            else:
                classe_performance = classe.last_performance(exam=exam)
                classe_object['performance'] = classe_performance.first().performance if classe_performance else 0
            classes_summary.append(classe_object)

        return classes_summary

    def get_unities_performance(self, obj):
        unities_list = self.context['unities'] or []
        q_subjects = self.context['q_subjects'] if hasattr(self.context, 'q_subjects') else None        
        exam = obj.application.exam
        unities = Unity.objects.filter(id__in=unities_list)
        unities_summary = []
        
        if not exam:
            return []
        
        for unity in unities:
            unity_object = {
                "name": unity.name,
                "performance": 0,
            }
            
            exam.generate_unities_performances(unity=unity)
            if q_subjects:
                subjects = Subject.objects.filter(pk__in=q_subjects)
                subjects_performances = []
                applications_student = ApplicationStudent.objects.filter(application__exam=exam, student__client__unities=unity)
                
                for subject in subjects:
                    students_performances = []
                    for application_student in applications_student:
                        students_performances.append(application_student.get_performance(subject=subject))
                    
                    if students_performances:
                        subjects_performances.append(fmean(students_performances))
                
                unity_object['performance'] = fmean(subjects_performances) if subjects_performances else 0
            else:    
                unity_performance = unity.last_performance(exam=exam)
                unity_object['performance'] = unity_performance.first().performance if unity_performance else 0
            unities_summary.append(unity_object)

        return unities_summary
    
    def get_general_performance(self, obj):  
        q_subjects = self.context['q_subjects'] if hasattr(self.context, 'q_subjects') else None
        subjects_performances = []
        if q_subjects:
            subjects = Subject.objects.filter(pk__in=q_subjects)
            for subject in subjects:
                student_subject_performance = obj.get_performance(subject=subject)
                if student_subject_performance:
                    subjects_performances.append(student_subject_performance)
                    
                return fmean(subjects_performances) if subjects_performances else 0
        return obj.last_performance.first().performance if obj.last_performance else 0
