from django import forms
from .models import Album, Track, Comment

class AlbumForm(forms.ModelForm):
    class Meta:
        model = Album
        fields = ['title', 'artist', 'genre', 'release_date', 'cover_art', 'description']
        widgets = {
            'release_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class TrackForm(forms.ModelForm):
    class Meta:
        model = Track
        fields = ['title', 'album', 'artist', 'genre', 'audio_file', 'track_number']
        widgets = {
            'track_number': forms.NumberInput(attrs={'min': 1}),
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Add your comment...'}),
        }
        
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserChangeForm
from .models import Profile

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'location', 'birth_date', 'profile_picture', 'website']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }
        
        
from django import forms
from .models import DistributionRequest, DistributionPlatform, Track

from django import forms
from .models import DistributionRequest, DistributionPlatform, Track

class DistributionRequestForm(forms.ModelForm):
    platforms = forms.ModelMultipleChoiceField(
        queryset=DistributionPlatform.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    
    tracks = forms.ModelMultipleChoiceField(
        queryset=Track.objects.none(),  # Will be set in __init__
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    
    class Meta:
        model = DistributionRequest
        fields = ['platforms', 'tracks']  # Only include many-to-many fields
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Only show tracks that belong to the user
            user_tracks = Track.objects.filter(uploader=self.user)
            
            # Exclude tracks that are already distributed (status = distributed)
            distributed_track_ids = DistributionRequest.objects.filter(
                tracks__in=user_tracks,
                status='distributed'
            ).values_list('tracks__id', flat=True).distinct()
            
            self.fields['tracks'].queryset = user_tracks.exclude(
                id__in=distributed_track_ids
            )
    
    def clean_tracks(self):
        tracks = self.cleaned_data.get('tracks')
        if not tracks:
            raise forms.ValidationError("Please select at least one track.")
        return tracks
    
    def save(self, commit=True):
        # Don't try to save many-to-many relationships here
        # They will be handled by save_m2m() after the instance is saved
        instance = super().save(commit=False)
        if commit:
            instance.save()
            self.save_m2m()
        return instance