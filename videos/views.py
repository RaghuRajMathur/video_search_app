import subprocess
from celery import shared_task
from django.shortcuts import redirect, render
from boto3.dynamodb.conditions import Attr
from videos.tasks import process_video
from .forms import VideoForm, SearchForm
from .models import Video
from django.conf import settings
import boto3
import os

def upload_video(request):
    if request.method == 'POST':
        form = VideoForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save()
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
            dynamodb = boto3.resource('dynamodb', aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                      aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
            table = dynamodb.Table('Subtitles')
            response = table.scan(
                FilterExpression=Attr('subtitles').contains(keyword)
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
    video.s3_url = f'https://{settings.AWS_STORAGE_BUCKET_NAME}.s3://videosearchbucket{os.path.basename(video_path)}'
    video.save()

    # Save subtitles to DynamoDB
    dynamodb = boto3.resource('dynamodb', aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                              aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
    table = dynamodb.Table('Subtitles')
    table.put_item(
        Item={
            'video_id': str(video.id),
            'subtitles': subtitles
        }
    )