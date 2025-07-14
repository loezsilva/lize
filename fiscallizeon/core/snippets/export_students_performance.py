"""
    Exporta desempenho dos alunos de determinada instituição de determinado ano e de determinada série
"""
import csv
from fiscallizeon.analytics.models import GenericPerformances
from fiscallizeon.bncc.utils import get_bncc
from fiscallizeon.classes.models import Grade

YEAR = 2022
CLIENT_PK = '60c76b23-e58e-44de-997f-821f3b26993d'
GRADES = [Grade.HIGHT_SCHOOL]

lines = []

performances = GenericPerformances.objects.filter(
    application_student__isnull=True,
    subject__isnull=True,
    exam__isnull=True,
    school_class__isnull=True,
    content_type__model__in=['topic', 'abiliity', 'competence'], 
    student__client=CLIENT_PK,
    student__classes__grade__level__in=GRADES,
    student__classes__school_year=YEAR,
).order_by('student__name', 'content_type__model')

for generic in performances:
    
    model_name = generic.content_type.name.split('/')[0].lower()
    bncc = get_bncc(generic.object_id)
    
    if bncc.subject and bncc.subject.knowledge_area.grades.filter(level=Grade.HIGHT_SCHOOL).exists():
        line: list = [
            generic.student.__str__(), # Nome do aluno
            generic.student.enrollment_number, # Matrícula
            generic.student.classes.all().last().grade.__str__(), # Série do aluno
            bncc.subject.__str__(), # Disciplina
            model_name, # 
            bncc.name if generic.content_type.model == 'topic' else bncc.text, # Texto do topico
            float(generic.performance), # Performance
        ]
        
        lines.append(line)

with open('desempenho_alunos.csv', 'w', encoding='UTF8', newline='') as f:
    # Aluno, matrícula, série, caderno, disciplina, topico, tipo_topico(assunto, hab, comp), desempenho
    header = ["Aluno", "Matrícula", "Série", "Disciplina", "Tipo", "Texto", "Desempenho"]
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(lines)