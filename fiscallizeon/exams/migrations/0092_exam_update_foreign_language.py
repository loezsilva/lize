# Criado manualmente

from django.db import migrations
from django.db import transaction

from fiscallizeon.exams.models import Exam, ExamQuestion, ExamTeacherSubject

@transaction.atomic
def update_exams(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0091_examquestion_is_foreign_language_and_more'),
    ]

    operations = [
        migrations.RunPython(update_exams, reverse_code=migrations.RunPython.noop),
    ]
