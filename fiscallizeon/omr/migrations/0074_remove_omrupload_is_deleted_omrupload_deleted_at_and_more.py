# Generated by Django 4.2.19 on 2025-06-16 16:56

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('omr', '0073_omrupload_is_deleted'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='omrupload',
            name='is_deleted',
        ),
        migrations.AddField(
            model_name='omrupload',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Data em que foi deletado'),
        ),
        migrations.AddField(
            model_name='omrupload',
            name='deleted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deleted_by', to=settings.AUTH_USER_MODEL, verbose_name='Usuário que deletou'),
        ),
        migrations.AlterField(
            model_name='omrupload',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='user_upload', to=settings.AUTH_USER_MODEL, verbose_name='Usuário'),
        ),
    ]
