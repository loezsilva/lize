import time
from statistics import fmean  
from datetime import timedelta
from fiscallizeon.classes.models import Grade
from fiscallizeon.subjects.models import Topic
from fiscallizeon.students.models import Student
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.bncc.models import Abiliity, Competence   

students = Student.objects.filter(client__pk='60c76b23-e58e-44de-997f-821f3b26993d', classes__school_year=2022, classes__grade__level=Grade.HIGHT_SCHOOL).distinct()

start_process = time.time()

def generate_performance(self, recalculate=True):
    
    questions_availables = ExamQuestion.objects.filter(question__in=self.finish_application_students.distinct().values_list('application__exam__questions')).availables().distinct()
    topics = Topic.objects.filter(questions__examquestion__in=questions_availables).distinct()
    abilities = Abiliity.objects.filter(question__examquestion__in=questions_availables).distinct()
    competences = Competence.objects.filter(question__examquestion__in=questions_availables).distinct()

    for topic in topics:
        performances = []
        questions_availables_filtred = ExamQuestion.objects.filter(question__topics=topic)
        if questions_availables_filtred.count():
            topic_performance = topic.last_performance(student=self)
            
            for application_student in self.finish_application_students.filter(application__exam__questions__in=questions_availables_filtred.values('question')).distinct():
                performances.append(application_student.get_performance(bncc_pk=topic.pk, recalculate=recalculate))
            
            if topic_performance:
                topic_performance.using('default').update(
                    performance=fmean(performances) if performances else 0,
                    process_time=timedelta(seconds=(time.time() - start_process))
                )
            else:
                topic.performances.create(
                    student=self, 
                    performance=fmean(topic_performance) if topic_performance else 0,
                    process_time=timedelta(seconds=(time.time() - start_process))
                )
        
        
    # for ability in abilities:
    #     performances = []
    #     ability_performance = ability.last_performance(student=self)
    #     questions_availables_filtred = ExamQuestion.objects.filter(question__abilities=ability)
    #     for application_student in self.finish_application_students.filter(application__exam__questions__in=questions_availables_filtred.values('question')).distinct():
    #         performances.append(application_student.get_performance(bncc_pk=ability.pk, recalculate=recalculate))
        
    #     if ability_performance:
    #         ability_performance.using('default').update(
    #             performance=fmean(performances) if performances else 0,
    #             process_time=timedelta(seconds=(time.time() - start_process))
    #         )
    #     else:
    #         ability.performances.create(
    #             student=self, 
    #             performance=fmean(performances) if performances else 0,
    #             process_time=timedelta(seconds=(time.time() - start_process))
    #         )
            
    # for competence in competences:                
    #     performances = []
    #     competence_performance = competence.last_performance(student=self)
    #     questions_availables_filtred = ExamQuestion.objects.filter(question__competences=competence)
    #     for application_student in self.finish_application_students.filter(application__exam__questions__in=questions_availables_filtred.values('question')).distinct():
    #         performances.append(application_student.get_performance(bncc_pk=competence.pk, recalculate=recalculate))
        
    #     if competence_performance:
    #         competence_performance.using('default').update(
    #             performance=fmean(performances) if performances else 0,
    #             process_time=timedelta(seconds=(time.time() - start_process))
    #         )
    #     else:
    #         competence.performances.create(
    #             student=self, 
    #             performance=fmean(performances) if performances else 0,
    #             process_time=timedelta(seconds=(time.time() - start_process))
    #         )


for num, student in enumerate(students):
    generate_performance(student)
    print(student.__str__(), num, students.count())