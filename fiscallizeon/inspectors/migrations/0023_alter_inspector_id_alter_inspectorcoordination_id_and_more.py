# Generated by Django 4.0.4 on 2022-04-24 20:26

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('inspectors', '0022_merge_20220424_1725'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inspector',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='inspectorcoordination',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='teachersubject',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
    ]
