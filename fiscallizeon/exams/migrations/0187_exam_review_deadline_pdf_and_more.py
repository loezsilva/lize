# Generated by Django 4.0.6 on 2024-09-26 15:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0186_alter_exam_copy_exam_with_ia_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='exam',
            name='review_deadline_pdf',
            field=models.DateField(blank=True, null=True, verbose_name='Prazo para elaborador revisar o PDF'),
        ),
        migrations.AddField(
            model_name='historicalexam',
            name='review_deadline_pdf',
            field=models.DateField(blank=True, null=True, verbose_name='Prazo para elaborador revisar o PDF'),
        ),
    ]
