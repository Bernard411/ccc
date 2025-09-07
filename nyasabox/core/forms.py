from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.validators import validate_email, FileExtensionValidator
from django.core.exceptions import ValidationError
from .models import Album, Track, Comment, Profile, DistributionRequest, DistributionPlatform, GENRE_CHOICES

class AlbumForm(forms.ModelForm):
    class Meta:
        model = Album
        fields = ['title', 'artist', 'genre', 'release_date', 'cover_art', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'artist': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter artist name', 'required': True}),
            'genre': forms.Select(attrs={'class': 'form-control', 'required': True}, choices=GENRE_CHOICES),
            'release_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': True}),
            'cover_art': forms.FileInput(attrs={'class': 'form-control', 'required': True}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    cover_art = forms.ImageField(
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif'])]
    )

class TrackForm(forms.ModelForm):
    class Meta:
        model = Track
        fields = ['title', 'album', 'artist', 'genre', 'audio_file', 'track_number']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'album': forms.Select(attrs={'class': 'form-control'}),
            'artist': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter artist name', 'required': True}),
            'genre': forms.Select(attrs={'class': 'form-control', 'required': True}, choices=GENRE_CHOICES),
            'audio_file': forms.FileInput(attrs={'class': 'form-control', 'required': True}),
            'track_number': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

    audio_file = forms.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['mp3', 'wav'])]
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['album'].queryset = Album.objects.filter(uploader=user)
        self.fields['album'].required = False
        self.fields['track_number'].required = False

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add your comment...', 'required': True}),
        }

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'required': True}))

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'required': True}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'location', 'birth_date', 'profile_picture', 'website']
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        }

    profile_picture = forms.ImageField(
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif'])],
        required=False
    )

class DistributionRequestForm(forms.ModelForm):
    platforms = forms.ModelMultipleChoiceField(
        queryset=DistributionPlatform.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True
    )
    tracks = forms.ModelMultipleChoiceField(
        queryset=Track.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True
    )

    class Meta:
        model = DistributionRequest
        fields = ['platforms', 'tracks']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            distributed_track_ids = DistributionRequest.objects.filter(
                tracks__in=Track.objects.filter(uploader=user),
                status='distributed'
            ).values_list('tracks__id', flat=True).distinct()
            self.fields['tracks'].queryset = Track.objects.filter(uploader=user).exclude(id__in=distributed_track_ids)

    def clean_tracks(self):
        tracks = self.cleaned_data.get('tracks')
        if not tracks:
            raise forms.ValidationError("Please select at least one track.")
        return tracks

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control', 'required': True}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control', 'required': True}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email address is already in use.")
        return email

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label='Username or Email',
        widget=forms.TextInput(attrs={'class': 'form-control', 'required': True})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'required': True})
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if '@' in username:
            validate_email(username)
            try:
                username = User.objects.get(email=username).username
            except User.DoesNotExist:
                raise ValidationError("No account found with this email address.")
        return username