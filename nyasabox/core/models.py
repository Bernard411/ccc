from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal
import random
import string
from datetime import timedelta
from django.utils import timezone

# Genre choices
GENRE_CHOICES = (
    ('afrobeat', 'Afrobeat'),
    ('amapiano', 'Amapiano'),
    ('bongo', 'Bongo Flava'),
    ('dancehall', 'Dancehall'),
    ('gospel', 'Gospel'),
    ('hiphop', 'Hip Hop'),
    ('rumba', 'Rumba'),
    ('reggae', 'Reggae'),
    ('soca', 'Soca'),
    ('traditional', 'Traditional'),
    ('rnb', 'R&B'),
    ('pop', 'Pop'),
    ('rock', 'Rock'),
    ('jazz', 'Jazz'),
    ('blues', 'Blues'),
    ('country', 'Country'),
    ('electronic', 'Electronic'),
    ('classical', 'Classical'),
    ('other', 'Other'),
)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=30, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', default='profile_pics/default.png')
    website = models.URLField(blank=True)
    is_email_verified = models.BooleanField(default=False)
    is_artist = models.BooleanField(default=False)
    artist_status = models.CharField(
        max_length=20,
        choices=(('pending', 'Pending'), ('verified', 'Verified'), ('rejected', 'Rejected')),
        default='pending',
        blank=True
    )
    verification_proof = models.FileField(upload_to='verifications/', blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['user'], name='idx_profile_user'),
            models.Index(fields=['is_artist', 'artist_status'], name='idx_profile_artist'),
        ]

    def __str__(self):
        return f'{self.user.username} Profile'

@receiver(post_save, sender=User)
def manage_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        instance.profile.save()

class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    purpose = models.CharField(max_length=20, choices=(('email_verification', 'Email Verification'), ('password_reset', 'Password Reset'), ('artist_verification', 'Artist Verification')))

    class Meta:
        indexes = [
            models.Index(fields=['user', 'code'], name='idx_otp_user_code'),
            models.Index(fields=['created_at'], name='idx_otp_created_at'),
        ]

    def generate_code(self):
        return ''.join(random.choices(string.digits, k=6))

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_valid(self):
        return timezone.now() <= self.expires_at

    def __str__(self):
        return f"OTP {self.code} for {self.user.username} ({self.purpose})"

class BlogCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, max_length=100)

    class Meta:
        indexes = [
            models.Index(fields=['slug'], name='idx_blogcategory_slug'),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(BlogCategory, on_delete=models.SET_NULL, null=True)
    content = models.TextField()
    featured_image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['slug'], name='idx_blogpost_slug'),
            models.Index(fields=['created_at'], name='idx_blogpost_created_at'),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog_detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.title

class Album(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    artist = models.CharField(max_length=200)
    genre = models.CharField(max_length=20, choices=GENRE_CHOICES)
    release_date = models.DateField()
    cover_art = models.ImageField(upload_to='album_covers/')
    description = models.TextField(blank=True)
    uploader = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    downloads = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['slug'], name='idx_album_slug'),
            models.Index(fields=['created_at'], name='idx_album_created_at'),
            models.Index(fields=['uploader'], name='idx_album_uploader'),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Album.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('album_detail', kwargs={'slug': self.slug})

    def __str__(self):
        return f"{self.title} by {self.artist}"

class Track(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='tracks', null=True, blank=True)
    artist = models.CharField(max_length=200)
    genre = models.CharField(max_length=20, choices=GENRE_CHOICES, blank=True)
    audio_file = models.FileField(upload_to='tracks/')
    duration = models.DurationField(blank=True, null=True)
    track_number = models.PositiveIntegerField(null=True, blank=True)
    uploader = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    downloads = models.PositiveIntegerField(default=0)
    likes = models.ManyToManyField(User, related_name='liked_tracks', blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['slug'], name='idx_track_slug'),
            models.Index(fields=['created_at'], name='idx_track_created_at'),
            models.Index(fields=['uploader'], name='idx_track_uploader'),
            models.Index(fields=['downloads'], name='idx_track_downloads'),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Track.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        if not self.genre and self.album:
            self.genre = self.album.genre
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('track_detail', kwargs={'slug': self.slug})

    def get_formatted_duration(self):
        if self.duration:
            total_seconds = int(self.duration.total_seconds())
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}:{seconds:02d}"
        return "0:00"

    def __str__(self):
        return self.title

class Comment(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user'], name='idx_comment_user'),
            models.Index(fields=['created_at'], name='idx_comment_created_at'),
        ]

    def __str__(self):
        return f"Comment by {self.user.username} on {self.track.title if self.track else self.album.title}"

class DistributionPlatform(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='platform_logos/', blank=True, null=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['name'], name='idx_platform_name'),
        ]

    def __str__(self):
        return self.name

class DistributionRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Payment'),
        ('paid', 'Paid'),
        ('processing', 'Processing'),
        ('distributed', 'Distributed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    )

    artist = models.ForeignKey(User, on_delete=models.CASCADE, related_name='distribution_requests')
    tracks = models.ManyToManyField(Track, related_name='distribution_requests')
    platforms = models.ManyToManyField(DistributionPlatform, related_name='distribution_requests')
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_reference = models.CharField(max_length=100, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    distributed_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['artist'], name='idx_distribution_artist'),
            models.Index(fields=['requested_at'], name='idx_distribution_requested_at'),
            models.Index(fields=['status'], name='idx_distribution_status'),
        ]

    def __str__(self):
        return f"Distribution Request #{self.id} - {self.artist.username}"

    def calculate_total(self):
        return Decimal(str(self.tracks.count() * 1666.67))

    def get_track_count(self):
        return self.tracks.count()

    def save(self, *args, **kwargs):
        if not self.total_amount or self.tracks.exists():
            self.total_amount = self.calculate_total()
        super().save(*args, **kwargs)