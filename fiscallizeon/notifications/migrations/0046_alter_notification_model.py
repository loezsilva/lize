# Generated by Django 4.0.6 on 2023-11-23 17:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0045_alter_notification_especial_trigger_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='model',
            field=models.CharField(blank=True, choices=[('exams.Exam', 'Cadernos'), ('ExamTemplate', 'Gabarito avulso'), ('questions.Question', 'Questions'), ('students.Student', 'Alunos'), ('inspectors.Inspector', 'Professor'), ('Inspector', 'Fiscais')], max_length=100, null=True, verbose_name='Para qual modelo?'),
        ),
    ]
