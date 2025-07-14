import csv
from fiscallizeon.inspectors.models import Inspector

lines = []

teachers = Inspector.objects.filter(
    inspector_type=Inspector.TEACHER,
    coordinations__unity__client__name__icontains="decisão"
)

for teacher in teachers:
    line: list = [
        teacher.name,
        teacher.email,
        teacher.coordinations.all().first().unity.client.name if teacher.coordinations.all().first() else "",
        ",".join(teacher.coordinations.all().values_list("name", flat=True)),
        ",".join(teacher.subjects.all().values_list("name", flat=True))
    ]
    lines.append(line)

with open('professores_decisao_18_abr.csv', 'w', encoding='UTF8', newline='') as f:
    header = ["Nome", "Email", "Cliente", "Coordenações", "Disciplinas"]
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(lines)