from django.db import models

class Video(models.Model):
    file = models.FileField(upload_to='videos/')
    description = models.TextField(blank=True, default='')
    subtitles = models.TextField(blank=True, null=True)
    s3_url = models.URLField(blank=True, null=True)
