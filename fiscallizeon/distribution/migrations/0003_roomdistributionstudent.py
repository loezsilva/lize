# Generated by Django 3.2.4 on 2021-11-17 19:21

from django.db import migrations, models
import django.db.models.deletion
import django_lifecycle.mixins
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0005_alter_student_options'),
        ('distribution', '0002_delete_roomdistributionstudent'),
    ]

    operations = [
        migrations.CreateModel(
            name='RoomDistributionStudent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Registrado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('distribution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='room_distribution', to='distribution.roomdistribution')),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='room_distribution', to='distribution.room')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='room_distribution', to='students.student')),
            ],
            options={
                'abstract': False,
            },
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
    ]
