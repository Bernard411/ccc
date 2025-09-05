from django import forms
from .models import Album, Track, Comment

from django import forms
from .models import Album, Track, Comment, GENRE_CHOICES

class AlbumForm(forms.ModelForm):
    class Meta:
        model = Album
        fields = ['title', 'artist', 'genre', 'release_date', 'cover_art', 'description']
        widgets = {
            'release_date': forms.DateInput(attrs={'type': 'date', 'required': True}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'artist': forms.TextInput(attrs={'placeholder': 'Enter artist name', 'required': True}),
            'genre': forms.Select(attrs={'required': True}, choices=GENRE_CHOICES),
            'title': forms.TextInput(attrs={'required': True}),
            'cover_art': forms.FileInput(attrs={'required': True}),
        }

class TrackForm(forms.ModelForm):
    class Meta:
        model = Track
        fields = ['title', 'album', 'artist', 'genre', 'audio_file', 'track_number']
        widgets = {
            'track_number': forms.NumberInput(attrs={'min': 1}),
            'artist': forms.TextInput(attrs={'placeholder': 'Enter artist name', 'required': True}),
            'genre': forms.Select(attrs={'required': True}, choices=GENRE_CHOICES),
            'title': forms.TextInput(attrs={'required': True}),
            'audio_file': forms.FileInput(attrs={'required': True}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show albums uploaded by the current user
        if 'initial' in kwargs and 'user' in kwargs['initial']:
            user = kwargs['initial']['user']
            self.fields['album'].queryset = Album.objects.filter(uploader=user)
        
        # Make album field not required
        self.fields['album'].required = False
        self.fields['track_number'].required = False


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
    




# authentication forms 
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your email'
    }))
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email address is already in use.")
        return email

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label='Username or Email',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password'].widget.attrs.update({'class': 'form-control'})
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if '@' in username:
            validate_email(username)
            try:
                username = User.objects.get(email=username).username
            except User.DoesNotExist:
                raise ValidationError("No account found with this email address.")
        return username