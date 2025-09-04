from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal  # Add this import


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=30, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', default='profile_pics/default.png')
    website = models.URLField(blank=True)
    
    def __str__(self):
        return f'{self.user.username} Profile'

# Signal to create profile when user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

# Signal to save profile when user is saved
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class BlogCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name

class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(BlogCategory, on_delete=models.SET_NULL, null=True)
    content = models.TextField()
    featured_image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views = models.PositiveIntegerField(default=0)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('blog_detail', kwargs={'slug': self.slug})
    
    def __str__(self):
        return self.title
    
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse

class Genre(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name

class Artist(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    bio = models.TextField(blank=True)
    image = models.ImageField(upload_to='artists/', blank=True, null=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator

# Remove Artist model and update Genre to be choices
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

class Album(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    artist = models.CharField(max_length=200)  # Changed from ForeignKey to CharField
    genre = models.CharField(max_length=20, choices=GENRE_CHOICES)  # Changed from ForeignKey to CharField
    release_date = models.DateField()
    cover_art = models.ImageField(upload_to='album_covers/')
    description = models.TextField(blank=True)
    uploader = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    downloads = models.PositiveIntegerField(default=0)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('album_detail', kwargs={'slug': self.slug})
    
    def __str__(self):
        return f"{self.title} by {self.artist}"

class Track(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='tracks', null=True, blank=True)
    artist = models.CharField(max_length=200)  # Changed from ForeignKey to CharField
    genre = models.CharField(max_length=20, choices=GENRE_CHOICES, blank=True)  # Changed from ForeignKey to CharField
    audio_file = models.FileField(upload_to='tracks/')
    duration = models.DurationField(blank=True, null=True)
    track_number = models.PositiveIntegerField(null=True, blank=True)
    uploader = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    downloads = models.PositiveIntegerField(default=0)
    likes = models.ManyToManyField(User, related_name='liked_tracks', blank=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
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
    
    def __str__(self):
        return f"Comment by {self.user.username} on {self.track.title if self.track else self.album.title}"
    
    
class DistributionPlatform(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='platform_logos/', blank=True, null=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
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
    
    def __str__(self):
        return f"Distribution Request #{self.id} - {self.artist.username}"
    
    def calculate_total(self):
        # 10,000 MWK for 6 songs, so ~1,667 MWK per song
        base_price_per_track = Decimal('1666.67')
        track_count = self.tracks.count()
        return track_count * base_price_per_track
    
    def get_track_count(self):
        return self.tracks.count()
    
    # def save(self, *args, **kwargs):
    #     # Calculate total amount before saving
    #     if not self.total_amount or self.tracks.exists():
    #         self.total_amount = self.calculate_total()
    #     super().save(*args, **kwargs)