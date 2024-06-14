from django.db import models

class Video(models.Model):
    file = models.FileField(upload_to='videos/')
    subtitles = models.TextField(blank=True, default='')
    s3_url = models.URLField(blank=True, null=True)

    def save(self, *args, **kwargs):
        super(Video, self).save(*args, **kwargs)
        if not self.s3_url:
            self.s3_url = self.file.url
            super(Video, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Delete the file from S3
        self.file.delete()
        # Call the original delete method
        super(Video, self).delete(*args, **kwargs)
