# Generated by Django 4.2.18 on 2025-02-27 13:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('integrations', '0024_merge_20250226_1533'),
    ]

    operations = [
        migrations.AlterField(
            model_name='integration',
            name='erp',
            field=models.PositiveSmallIntegerField(choices=[(1, 'Activesoft'), (2, 'Ischolar'), (3, 'AthenaWeb'), (5, 'Realms'), (4, 'Sophia')], default=1, verbose_name='ERP'),
        ),
    ]
