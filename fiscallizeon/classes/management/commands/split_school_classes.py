from django.db.models.functions import Length
from django.db.models import Count, F, Value, CharField, Case, When, IntegerField, Q

from django.core.management.base import BaseCommand
from fiscallizeon.applications.models import Application
from fiscallizeon.exams.models import Exam
from fiscallizeon.classes.models import SchoolClass, Grade
from fiscallizeon.students.models import Student


class Command(BaseCommand):
    help = 'Divide turmas do PH'
    CLIENT_ID = '86ba20fe-3822-4f72-ab9a-01720bf93662' #PH
    CURRENT_YEAR = 2022

    prefix_lookup = {
        '1.6': 'EF6',
        '1.7': 'EF7',
        '1.8': 'EF8',
        '1.9': 'EF9',
        '2.1': 'EM1',
        '2.2': 'EM2',
    }

    shift_lookup = {
        'M': 'Manh',
        'T': 'Tarde',
    }

    exams_data = [
        #EM
        {'classes': ['2.1', '2.2'], 'tipos': ['A', 'B'], 'day': '14', 'start': '07:45', 'end': '09:15', 'subject': 'Matemática'},
        {'classes': ['2.1', '2.2'], 'tipos': ['A', 'B'], 'day': '14', 'start': '12:00', 'end': '13:00', 'subject': 'textual'},
        {'classes': ['2.1', '2.2'], 'tipos': ['A', 'B'], 'day': '15', 'start': '08:15', 'end': '09:15', 'subject': 'Química'},
        {'classes': ['2.1', '2.2'], 'tipos': ['A', 'B'], 'day': '15', 'start': '12:00', 'end': '13:00', 'subject': 'filosofia'},
        {'classes': ['2.1', '2.2'], 'tipos': ['A', 'B'], 'day': '16', 'start': '08:15', 'end': '09:15', 'subject': 'Geografia'},
        {'classes': ['2.1', '2.2'], 'tipos': ['A', 'B'], 'day': '16', 'start': '12:00', 'end': '13:00', 'subject': 'Biologia'},
        {'classes': ['2.1', '2.2'], 'tipos': ['A', 'B'], 'day': '17', 'start': '07:45', 'end': '09:00', 'subject': 'linguísticos'},
        {'classes': ['2.1', '2.2'], 'tipos': ['A', 'B'], 'day': '17', 'start': '09:45', 'end': '10:45', 'subject': 'Sociologia'},
        {'classes': ['2.1'],        'tipos': ['A', 'B'], 'day': '17', 'start': '12:00', 'end': '13:00', 'subject': 'Inglês'},
        {'classes': ['2.1', '2.2'], 'tipos': ['A', 'B'], 'day': '18', 'start': '08:15', 'end': '09:15', 'subject': 'Física'},
        {'classes': ['2.1', '2.2'], 'tipos': ['A', 'B'], 'day': '18', 'start': '12:00', 'end': '13:00', 'subject': 'História'},

        #EF Manha
        {'classes': ['1.6', '1.7', '1.8', '1.9'], 'tipos': ['A', 'B'], 'shift': 'M', 'day': '14', 'start': '10:45', 'end': '12:15', 'subject': 'Matemática'},
        {'classes': ['1.6', '1.7', '1.8', '1.9'], 'tipos': ['A', 'B'], 'shift': 'M', 'day': '15', 'start': '08:15', 'end': '09:15', 'subject': 'História'},
        {'classes': ['1.6', '1.7', '1.8', '1.9'], 'tipos': ['A', 'B'], 'shift': 'M', 'day': '15', 'start': '11:15', 'end': '12:15', 'subject': 'Redação'},
        {'classes': ['1.6', '1.7', '1.8', '1.9'], 'tipos': ['A', 'B'], 'shift': 'M', 'day': '16', 'start': '08:15', 'end': '09:15', 'subject': 'Geografia'},
        {'classes': ['1.6', '1.7', '1.8', '1.9'], 'tipos': ['A', 'B'], 'shift': 'M', 'day': '16', 'start': '11:15', 'end': '12:15', 'subject': 'Inglês'},
        {'classes': ['1.6', '1.7', '1.8', '1.9'], 'tipos': ['A', 'B'], 'shift': 'M', 'day': '17', 'start': '11:00', 'end': '12:15', 'subject': 'Portuguesa'},
        {'classes': ['1.6', '1.7', '1.8', '1.9'], 'tipos': ['A', 'B'], 'shift': 'M', 'day': '18', 'start': '11:00', 'end': '12:15', 'subject': 'Ciências'},

        #EF Tarde
        {'classes': ['1.6', '1.7', '1.8', '1.9'], 'tipos': ['C', 'D'], 'shift': 'T', 'day': '14', 'start': '16:40', 'end': '18:10', 'subject': 'Matemática'},
        {'classes': ['1.6', '1.7', '1.8', '1.9'], 'tipos': ['C', 'D'], 'shift': 'T', 'day': '15', 'start': '14:25', 'end': '15:25', 'subject': 'História'},
        {'classes': ['1.6', '1.7', '1.8', '1.9'], 'tipos': ['C', 'D'], 'shift': 'T', 'day': '15', 'start': '17:10', 'end': '18:10', 'subject': 'Redação'},
        {'classes': ['1.6', '1.7', '1.8', '1.9'], 'tipos': ['C', 'D'], 'shift': 'T', 'day': '16', 'start': '14:25', 'end': '15:25', 'subject': 'Geografia'},
        {'classes': ['1.6', '1.7', '1.8', '1.9'], 'tipos': ['C', 'D'], 'shift': 'T', 'day': '16', 'start': '17:10', 'end': '18:10', 'subject': 'Inglês'},
        {'classes': ['1.6', '1.7', '1.8', '1.9'], 'tipos': ['C', 'D'], 'shift': 'T', 'day': '17', 'start': '16:55', 'end': '18:10', 'subject': 'Portuguesa'},
        {'classes': ['1.6', '1.7', '1.8', '1.9'], 'tipos': ['C', 'D'], 'shift': 'T', 'day': '18', 'start': '16:55', 'end': '18:10', 'subject': 'Ciências'},
    ]

    def generate_application_exam(self):
        for exam_data in self.exams_data:
            for school_class_prefix in exam_data['classes']:
                for tipo in exam_data['tipos']:
                    class_tipo = tipo
                    if tipo == 'C':
                        class_tipo = 'A'
                    elif tipo == 'D':
                        class_tipo = 'B'
                    
                    temporary_classes = self.get_temporary_classes_by_ethimology(prefix=school_class_prefix, suffix='Tipo ' + class_tipo)
                    exam = self.get_exam(exam_data['subject'], school_class_prefix, tipo, exam_data.get('shift', None))

                    if not exam:
                        print('Não encontrou a prova', exam_data['subject'], school_class_prefix, tipo, exam_data.get('shift', None))
                        continue

                    application = Application.objects.create(
                        exam=exam,
                        category=Application.PRESENTIAL,
                        date=f'2022-03-{exam_data["day"]}',
                        start=exam_data['start'],
                        end=exam_data['end'],
                    )

                    if exam_data.get('shift', None):
                        temporary_classes = temporary_classes.filter(name__regex=r'^.{5}' + exam_data['shift'])
                    application.school_classes.set(temporary_classes, clear=True)

                    students = Student.objects.filter(classes__in=temporary_classes).distinct()
                    application.students.set(students)

                    for class_name in temporary_classes:
                        print(f'{application.pk}, {application.date}, {application.start}, {application.end}, {application.exam.name}, {class_name.name}, {class_name.coordination.unity.name}, {class_name.students.count()}')


    def get_ph_classes(self):
        ph_classes = SchoolClass.objects.annotate(
            length=Length('name'),
        ).filter(
            coordination__unity__client=self.CLIENT_ID,
            school_year=self.CURRENT_YEAR,
            temporary_class=False,
            length=6,
        ).exclude(
            grade__name__in=['3', 'Curso', 'Concurso.'],
            grade__level=Grade.HIGHT_SCHOOL,
        ).exclude(
            grade__name__in=['1', '2', '3', '4', '5'],
            grade__level__in=[Grade.ELEMENTARY_SCHOOL, Grade.ELEMENTARY_SCHOOL_2]
        ).order_by(
            'name', 'coordination__unity__name',
        )

        # for school_class in ph_classes:
        #     print(f'{school_class.name}, {school_class.coordination.unity.name}, {school_class.name[-1]}, {school_class.students.count()}, {school_class.pk}')

        return ph_classes

    def get_temporary_classes_by_ethimology(self, prefix, suffix):
        return SchoolClass.objects.filter(
            name__endswith=suffix,
            name__startswith=prefix,
            school_year=self.CURRENT_YEAR,
            coordination__unity__client=self.CLIENT_ID,
            temporary_class=True,
        )

    def split_class(self, school_class):

        school_class_a, _ = SchoolClass.objects.get_or_create(
            name=school_class.name + ' - Tipo A',
            grade=school_class.grade,
            coordination=school_class.coordination,
            temporary_class=True,
            school_year=self.CURRENT_YEAR,
        )

        school_class_b, _ = SchoolClass.objects.get_or_create(
            name=school_class.name + ' - Tipo B',
            grade=school_class.grade,
            coordination=school_class.coordination,
            temporary_class=True,
            school_year=self.CURRENT_YEAR,
        )

        students = list(school_class.students.all().order_by('?'))
        students_a = students[:int(len(students) / 2)]
        students_b = students[int(len(students) / 2):]

        school_class_a.students.set(students_a, clear=True)
        school_class_b.students.set(students_b, clear=True)

    def get_temporary_classes(self, school_class):
        return SchoolClass.objects.filter(
            coordination=school_class.coordination,
            grade=school_class.grade,
            school_year=self.CURRENT_YEAR,
            temporary_class=True,
            name__startswith=school_class.name + ' - Tipo',
        ).order_by('name')

    def get_exam(self, subject, grade, tipo=None, shift=None):
        exam = Exam.objects.filter(
            Q(coordinations__unity__client=self.CLIENT_ID),
            Q(name__startswith='BIM 1'),
            Q(name__icontains=subject),
            Q(name__icontains=self.prefix_lookup[grade]),
            Q(created_at__year=self.CURRENT_YEAR),
        ).distinct()

        if tipo:
            exam = exam.filter(name__endswith=f'- {tipo}')

        if shift:
            exam = exam.filter(
                name__icontains=self.shift_lookup[shift],
            )

        return exam.first()

    def handle(self, *args, **kwargs):
        ph_classes = self.get_ph_classes()
        ph_split_classes = ph_classes.exclude(Q(name__endswith='PM') | Q(name__endswith='PT'))
        for school_class in ph_split_classes:
            self.split_class(school_class)
            print(f"Split: {school_class}")
        
        #Resolve problema das PMs
        temporary_classes = ph_classes.filter(Q(name__endswith='PM') | Q(name__endswith='PT'))
        for school_class in temporary_classes:
            regular_class = ph_split_classes.filter(
                grade=school_class.grade,
                coordination=school_class.coordination,
                name__startswith=school_class.name[:3],
                name__endswith=school_class.name[-1],
                length=6,
            ).first()

            splited_classes = self.get_temporary_classes(regular_class)
            if splited_classes.count():
                turma = splited_classes.order_by('?').first()
                turma.students.add(*school_class.students.all())
                print(f'{school_class} -> {turma}\n\n')

        self.generate_application_exam()
