from django.core.management.base import BaseCommand
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.inspectors.models import TeacherSubject

class Command(BaseCommand):
    help = "Cria relação de turma e professor"

    def handle(self, *args, **kwargs):
        
        teachers_subject = TeacherSubject.objects.all().distinct()

        for teacher_subject in teachers_subject.filter(teacher__user__isnull=False):
            
            teacher_grades = teacher_subject.teacher.subjects.all().values_list('knowledge_area__grades')
            
            if teacher_subject.teacher.classes_he_teaches.exists():
                
                teacher_subject.classes.set(
                    teacher_subject.teacher.classes_he_teaches.filter(
                        grade__in=teacher_grades,
                        school_year=2022
                    ).distinct()
                )
            else:
                
                classes = SchoolClass.objects.filter(
                    coordination__unity__client__in=teacher_subject.teacher.user.get_clients_cache(), 
                    grade__in=teacher_grades,
                    school_year=2022
                ).distinct()
                
                teacher_subject.classes.set(classes)
                
            print(teacher_subject.teacher)