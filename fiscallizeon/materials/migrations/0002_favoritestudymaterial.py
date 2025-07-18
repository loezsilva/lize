# Generated by Django 3.2.4 on 2022-01-25 21:58

from django.db import migrations, models
import django.db.models.deletion
import django_lifecycle.mixins
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0005_alter_student_options'),
        ('materials', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FavoriteStudyMaterial',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Registrado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorites_files', to='students.student')),
                ('study_material', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='materials.studymaterial')),
            ],
            options={
                'verbose_name': 'Material de estudo favorito',
                'verbose_name_plural': 'Materiais de estudo favoritos',
            },
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
    ]
