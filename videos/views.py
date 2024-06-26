import subprocess
import os
import boto3
from celery import shared_task
from django.shortcuts import redirect, render
from .forms import VideoForm, SearchForm
from .models import Video
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def upload_video(request):
    if request.method == 'POST':
        form = VideoForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save(commit=False)
            video.file = request.FILES['file']
            video.save()
            process_video.delay(video.id)
            return redirect('video_list')
    else:
        form = VideoForm()
    return render(request, 'videos/upload.html', {'form': form})

def video_list(request):
    videos = Video.objects.all()
    return render(request, 'videos/list.html', {'videos': videos})

def search_subtitles(request):
    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            keyword = form.cleaned_data['keyword']

            # Query DynamoDB for videos containing the keyword in subtitles
            dynamodb = boto3.resource('dynamodb',
                                      aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                      aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                                      region_name=settings.AWS_DYNAMODB_REGION_NAME)
            table = dynamodb.Table(settings.DYNAMODB_TABLE_NAME)
            response = table.scan(
                FilterExpression="contains(#keywords, :keyword)",
                ExpressionAttributeNames={"#keywords": "keywords"},
                ExpressionAttributeValues={":keyword": keyword}
            )
            items = response.get('Items', [])
            return render(request, 'videos/search_results.html', {'items': items, 'keyword': keyword})
    else:
        form = SearchForm()
    return render(request, 'videos/search.html', {'form': form})

@shared_task
def process_video(video_id):
    video = Video.objects.get(id=video_id)
    video_path = video.file.path

    # Path to ccextractor executable
    ccextractor_path = os.path.join(settings.BASE_DIR, 'tools', 'ccxgui.exe')

    # Extract subtitles using CCExtractor
    subtitles_path = f"{video_path}.srt"
    logger.info(f'Running ccextractor: {ccextractor_path} {video_path} -o {subtitles_path}')
    result = subprocess.run([ccextractor_path, video_path, '-o', subtitles_path], shell=True)
    logger.info(f'ccextractor result: {result}')

    # Read and save subtitles
    if os.path.exists(subtitles_path):
        with open(subtitles_path, 'r') as f:
            subtitles = f.read()

        logger.info(f'Subtitles extracted: {subtitles[:100]}...')  # Log the first 100 characters
        video.subtitles = subtitles
        video.save()

        # Cleanup: Remove subtitles file after reading
        os.remove(subtitles_path)

        # Upload video to S3
        s3 = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
        s3.upload_file(video_path, settings.AWS_STORAGE_BUCKET_NAME, f'videos/{os.path.basename(video_path)}')

        # Update video with S3 URL
        video.s3_url = f'https://{settings.AWS_STORAGE_BUCKET_NAME}.s3-website.eu-north-1.amazonaws.com/videos/{os.path.basename(video_path)}'
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
    else:
        logger.error('Subtitles file not found after running ccextractor')
