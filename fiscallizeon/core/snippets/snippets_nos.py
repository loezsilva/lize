


from fiscallizeon.students.models import Student
from django.db.models import Q, F

students = Student.objects.filter(
    Q(client__name__icontains="nós"),
    Q(
        Q(user__name__icontains="errado") |
        Q(name__icontains="errado")
    )
).distinct()


students = Student.objects.filter(
    client__name__icontains="nós",
).exclude(
    email=F('user__email') 
)


for s in students:
    print(f'{s.name, s.email, s.user.email}')

for s in students:
    s.name = s.user.name
    s.email = s.user.email
    s.save(skip_hooks=True)





Student.objects.filter(
    client__name__icontains="nós",
    user__is_active=False
).count()


for s in students:
    s.enrollment_number = f'{s.enrollment_number}-errado'
    s.save()


for s in Student.objects.filter(client__name__icontains="nós"):
    turma = s.get_last_class()
    if turma:
        unity = turma.coordination.unity
        turma.integration_token = unity.integration_token
        turma.save(skip_hooks=True)
        s.integration_token = unity.integration_token
        s.save(skip_hooks=True)


from fiscallizeon.accounts.models import User



User.objects.filter(
    student__client__name__icontains="nós",
    is_active=False
).count()


students =Student.objects.filter(
    client__name__icontains="nós",
    user__is_active=False,
    id_erp__isnull=False,
    # applicationstudent__created_at__year=2025
).distinct()


for s in students:
    print(f'{s.name, s.email, s.user.email}')



for s in Student.objects.filter(client__name__icontains="nós"):
    print(f'{s.pk},{s.id_erp},{"sim" if s.user},{s.name},{s.email},{s.user.email},{s.get_last_class().name if s.get_last_class() else "-"},{s.get_last_class().coordination.unity.name if s.get_last_class() else "-"},{s.integration_token.name if s.integration_token else "-"}')


User.objects.filter(
    student__created_at__gte="2025-02-21 12:00:00",
    student__client__name__icontains="nós"
).delete()


Student.objects.filter(
    Q(client__name__icontains="nós"),
    Q(
        Q(integration_token__isnull=True) |
        Q(classes__isnull=True)
    )
).count()

User.ob