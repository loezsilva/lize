# Generated by Django 4.2.19 on 2025-03-18 23:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('materials', '0023_alter_studymaterial_material_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='studymaterial',
            name='send_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='send_materials', to=settings.AUTH_USER_MODEL, verbose_name='Enviado por'),
        ),
    ]
