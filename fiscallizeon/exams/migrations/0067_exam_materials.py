# Generated by Django 4.0.2 on 2022-03-07 13:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('materials', '0014_studymaterial_exam'),
        ('exams', '0066_auto_20220214_1437'),
    ]

    operations = [
        migrations.AddField(
            model_name='exam',
            name='materials',
            field=models.ManyToManyField(blank=True, related_name='exams', to='materials.StudyMaterial', verbose_name='Materiais'),
        ),
    ]
