import subprocess
import os
import boto3
from celery import shared_task
from .models import Video
from django.conf import settings

@shared_task
def process_video(video_id):
    video = Video.objects.get(id=video_id)
    video_path = video.file.path

    # Extract subtitles using CCExtractor
    subtitles_path = f"{video_path}.srt"
    subprocess.run(['ccextractor', video_path, '-o', subtitles_path])

    # Read and save subtitles
    with open(subtitles_path, 'r') as f:
        subtitles = f.read()

    video.subtitles = subtitles
    video.save()

    # Upload video to S3
    s3 = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
    s3.upload_file(video_path, settings.AWS_STORAGE_BUCKET_NAME, f'videos/{os.path.basename(video_path)}')

    # Update video with S3 URL
    video.s3_url = f'https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/videos/{os.path.basename(video_path)}'
    video.save()

    # Save subtitles to DynamoDB
    dynamodb = boto3.resource('dynamodb', aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                              aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
    table = dynamodb.Table(settings.DYNAMODB_TABLE_NAME)
    table.put_item(
        Item={
            'video_id': str(video.id),
            'subtitles': subtitles
        }
    )
