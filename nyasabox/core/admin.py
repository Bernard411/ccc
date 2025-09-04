from django.contrib import admin
from .models import (
    Profile, BlogCategory, BlogPost,
    Album, Track, Comment,
    DistributionPlatform, DistributionRequest
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'birth_date', 'website')
    search_fields = ('user__username', 'location', 'website')
    list_filter = ('birth_date',)


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ('name',)


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'created_at', 'views')
    list_filter = ('category', 'author', 'created_at')
    search_fields = ('title', 'content')
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'genre', 'release_date', 'uploader', 'downloads')
    list_filter = ('genre', 'release_date')
    search_fields = ('title', 'artist')
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = 'release_date'
    ordering = ('-release_date',)


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'album', 'genre', 'downloads', 'created_at')
    list_filter = ('genre', 'artist', 'album')
    search_fields = ('title', 'artist', 'album__title')
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'track', 'album', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('text', 'user__username')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


@admin.register(DistributionPlatform)
class DistributionPlatformAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(DistributionRequest)
class DistributionRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'artist', 'status', 'requested_at', 'total_amount')
    list_filter = ('status', 'requested_at', 'payment_date', 'distributed_date')
    search_fields = ('artist__username', 'payment_reference')
    date_hierarchy = 'requested_at'
    ordering = ('-requested_at',)
    filter_horizontal = ('tracks', 'platforms')
