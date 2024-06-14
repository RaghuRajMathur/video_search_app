# Generated by Django 5.0.6 on 2024-06-13 15:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='video',
            name='title',
        ),
        migrations.RemoveField(
            model_name='video',
            name='uploaded_at',
        ),
        migrations.AddField(
            model_name='video',
            name='s3_url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='video',
            name='subtitles',
            field=models.TextField(blank=True, default=''),
        ),
    ]