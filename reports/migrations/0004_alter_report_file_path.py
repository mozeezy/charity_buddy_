# Generated by Django 5.1.1 on 2024-10-01 04:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0003_alter_cause_images'),
    ]

    operations = [
        migrations.AlterField(
            model_name='report',
            name='file_path',
            field=models.TextField(),
        ),
    ]
