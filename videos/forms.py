from django import forms
from .models import Video

class VideoForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ['file', 'description']  # Ensure this matches the fields in your Video model

class SearchForm(forms.Form):
    keyword = forms.CharField(max_length=100)
