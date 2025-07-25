# Generated by Django 4.0.2 on 2022-08-01 22:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('corrections', '0003_rename_note_correctionfileanswer_point_and_more'),
        ('questions', '0039_historicalquestion_text_correction_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalquestion',
            name='text_correction',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='corrections.textcorrection', verbose_name='Template de correção'),
        ),
        migrations.AlterField(
            model_name='question',
            name='text_correction',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='corrections.textcorrection', verbose_name='Template de correção'),
        ),
    ]
