from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.validators import validate_email, FileExtensionValidator
from django.core.exceptions import ValidationError
from .models import Album, Track, Comment, Profile, DistributionRequest, DistributionPlatform, GENRE_CHOICES, OTP

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
        fields = ['title', 'album', 'artist', 'genre', 'audio_file', 'track_number', 'cover_art',]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'album': forms.Select(attrs={'class': 'form-control'}),
            'artist': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter artist name', 'required': True}),
            'genre': forms.Select(attrs={'class': 'form-control', 'required': True}, choices=GENRE_CHOICES),
            'audio_file': forms.FileInput(attrs={'class': 'form-control', 'required': True}),
            'track_number': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'cover_art': forms.FileInput(attrs={'class': 'form-control', 'required': True}),
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
    is_artist = forms.BooleanField(
        required=False,
        label="Register as an Artist",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'is_artist']
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

class OTPVerificationForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter 6-digit OTP', 'required': True})
    )

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if not code.isdigit():
            raise ValidationError("OTP must be a 6-digit number.")
        return code

class ArtistUpgradeForm(forms.ModelForm):
    verification_proof = forms.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        widget=forms.FileInput(attrs={'class': 'form-control', 'required': True}),
        label="Verification Document (e.g., ID, Artist Profile)"
    )

    class Meta:
        model = Profile
        fields = ['bio', 'website', 'verification_proof']
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'required': True}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        }


from django import forms
from django.core.exceptions import ValidationError

class PaymentForm(forms.Form):
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)
    amount = forms.DecimalField(min_value=0.01, required=True)
    operator_ref_id = forms.ChoiceField(choices=[], required=True)
    mobile = forms.CharField(max_length=20, required=True)

    def __init__(self, *args, **kwargs):
        self.operators = kwargs.pop('operators', [])  # Store operators as instance attribute
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['operator_ref_id'].choices = [(op['ref_id'], op['name']) for op in self.operators]
        if user:
            self.fields['first_name'].initial = user.first_name or ''
            self.fields['last_name'].initial = user.last_name or ''
            self.fields['email'].initial = user.email or ''

    def clean_mobile(self):
        mobile = self.cleaned_data['mobile']
        mobile = mobile.strip().replace(' ', '').replace('-', '')
        if mobile.startswith('+265'):
            mobile = mobile[4:]
        elif mobile.startswith('0'):
            mobile = mobile[1:]
        if len(mobile) != 9 or not mobile.isdigit():
            raise ValidationError("Enter a valid mobile number of nine (9) digits.")
        operator_ref_id = self.cleaned_data.get('operator_ref_id')
        if operator_ref_id:
            operator = next((op for op in self.operators if op['ref_id'] == operator_ref_id), None)
            if operator:
                operator_name = operator.get('name', '').lower()
                if 'tnm' in operator_name and not mobile.startswith('8'):
                    raise ValidationError("TNM number must start with 8.")
                if 'airtel' in operator_name and not mobile.startswith('9'):
                    raise ValidationError("Airtel number must start with 9.")
        return mobile  # Return 9-digit number without +265


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email', 'required': True})
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise ValidationError("No account found with this email address.")
        return email

class PasswordResetConfirmForm(forms.Form):
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'required': True}),
        label="New Password"
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'required': True}),
        label="Confirm New Password"
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords do not match.")
        return cleaned_data