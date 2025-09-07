from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q, Count, Sum
from django.contrib import messages
from django.conf import settings
import json
from .models import Album, Track, Comment, BlogPost, BlogCategory, DistributionRequest, DistributionPlatform
from .forms import AlbumForm, TrackForm, CommentForm, CustomUserCreationForm, CustomAuthenticationForm, UserUpdateForm, ProfileUpdateForm, DistributionRequestForm

def index(request):
    # Get latest albums with track count
    latest_albums = Album.objects.all().order_by('-created_at')[:8].annotate(track_count=Count('tracks'))

    # Get latest single tracks (not part of albums)
    latest_tracks = Track.objects.filter(album__isnull=True).order_by('-created_at')[:12]

    # Get popular tracks by downloads
    popular_tracks = Track.objects.all().order_by('-downloads')[:10]

    # Get popular albums by total downloads of their tracks
    popular_albums = Album.objects.annotate(total_downloads=Sum('tracks__downloads')).order_by('-total_downloads')[:6]

    # Get top artists by track count and total downloads
    top_artists_data = Track.objects.values('artist').annotate(
        track_count=Count('id'),
        total_downloads=Sum('downloads')
    ).order_by('-track_count')[:8]

    # Format artist data
    artists_with_data = [
        {
            'name': artist['artist'],
            'track_count': artist['track_count'],
            'total_downloads': artist['total_downloads'] or 0,
            'sample_track': Track.objects.filter(artist=artist['artist']).first()
        }
        for artist in top_artists_data
    ]

    # Prepare tracks data for JavaScript player
    tracks_data = [
        {
            'id': track.id,
            'title': track.title,
            'artist': track.artist,
            'url': track.audio_file.url if track.audio_file else '',
            'cover_image': (
                track.album.cover_art.url if track.album and track.album.cover_art
                else getattr(track, 'cover_art', None).url if hasattr(track, 'cover_art') and track.cover_art
                else ''
            ),
            'duration': track.get_formatted_duration() if hasattr(track, 'get_formatted_duration') and track.duration else '0:00'
        }
        for track in set(latest_tracks) | set(popular_tracks)  # Use set to avoid duplicates
    ]

    context = {
        'latest_albums': latest_albums,
        'latest_tracks': latest_tracks,
        'popular_tracks': popular_tracks,
        'popular_albums': popular_albums,
        'top_artists': artists_with_data,
        'tracks_json': json.dumps(tracks_data),
    }
    return render(request, 'index.html', context)

def album_detail(request, slug):
    album = get_object_or_404(Album, slug=slug)
    tracks = album.tracks.all().order_by('track_number')
    comment_form = CommentForm()

    if request.method == 'POST' and request.user.is_authenticated:
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.album = album
            comment.user = request.user
            comment.save()
            messages.success(request, 'Comment posted successfully!')
            return redirect('album_detail', slug=album.slug)

    context = {
        'album': album,
        'tracks': tracks,
        'comment_form': comment_form,
    }
    return render(request, 'album_detail.html', context)

def track_detail(request, slug):
    track = get_object_or_404(Track, slug=slug)
    comment_form = CommentForm()

    # Get similar tracks (same genre, artist, or album)
    similar_tracks = Track.objects.filter(
        Q(genre=track.genre) | Q(artist=track.artist) | Q(album=track.album)
    ).exclude(id=track.id).distinct()[:5]

    if request.method == 'POST' and request.user.is_authenticated:
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.track = track
            comment.user = request.user
            comment.save()
            messages.success(request, 'Comment posted successfully!')
            return redirect('track_detail', slug=track.slug)

    context = {
        'track': track,
        'comment_form': comment_form,
        'similar_tracks': similar_tracks,
    }
    return render(request, 'track_detail.html', context)

@login_required
def like_track(request, slug):
    track = get_object_or_404(Track, slug=slug)
    liked = track.likes.filter(id=request.user.id).exists()
    if liked:
        track.likes.remove(request.user)
    else:
        track.likes.add(request.user)

    return JsonResponse({'liked': not liked, 'likes_count': track.likes.count()})

def download_track(request, slug):
    track = get_object_or_404(Track, slug=slug)
    if not track.audio_file:
        messages.error(request, 'Audio file not found.')
        return redirect('track_detail', slug=track.slug)
    
    track.downloads += 1
    track.save()
    return redirect(track.audio_file.url)

@login_required
def upload_music(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'album':
            album_form = AlbumForm(request.POST, request.FILES)
            if album_form.is_valid():
                album = album_form.save(commit=False)
                album.uploader = request.user
                album.save()

                track_files = request.FILES.getlist('track_files[]')
                track_numbers = request.POST.getlist('track_numbers[]')
                track_titles = request.POST.getlist('track_titles[]')

                for track_file, track_number, track_title in zip(track_files, track_numbers, track_titles):
                    if track_file and track_title:
                        Track.objects.create(
                            title=track_title,
                            album=album,
                            artist=album.artist,
                            genre=album.genre,
                            audio_file=track_file,
                            track_number=track_number,
                            uploader=request.user
                        )

                messages.success(request, f'Album "{album.title}" uploaded with {len(track_files)} tracks!')
                return redirect('album_detail', slug=album.slug)

        elif form_type == 'track':
            track_form = TrackForm(request.POST, request.FILES, initial={'user': request.user})
            if track_form.is_valid():
                track = track_form.save(commit=False)
                track.uploader = request.user
                if not track.genre and track.album:
                    track.genre = track.album.genre
                track.save()
                messages.success(request, f'Track "{track.title}" uploaded successfully!')
                return redirect('track_detail', slug=track.slug)

    album_form = AlbumForm()
    track_form = TrackForm(initial={'user': request.user})
    context = {
        'album_form': album_form,
        'track_form': track_form,
    }
    return render(request, 'upload.html', context)

def search(request):
    query = request.GET.get('q', '')
    content_type = request.GET.get('type', 'all')
    sort_by = request.GET.get('sort', 'relevance')

    track_results = album_results = blog_results = None

    if query:
        if content_type in ['all', 'tracks']:
            track_results = Track.objects.filter(
                Q(title__icontains=query) |
                Q(artist__icontains=query) |
                Q(album__title__icontains=query) |
                Q(genre__icontains=query)
            ).distinct()

        if content_type in ['all', 'albums']:
            album_results = Album.objects.filter(
                Q(title__icontains=query) |
                Q(artist__icontains=query) |
                Q(description__icontains=query) |
                Q(genre__icontains=query)
            ).distinct()

        if content_type in ['all', 'blogs']:
            blog_results = BlogPost.objects.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(author__username__icontains=query) |
                Q(category__name__icontains=query)
            ).distinct()

        # Sort results
        if sort_by == 'newest':
            if track_results: track_results = track_results.order_by('-created_at')
            if album_results: album_results = album_results.order_by('-created_at')
            if blog_results: blog_results = blog_results.order_by('-created_at')
        elif sort_by == 'popular':
            if track_results: track_results = track_results.order_by('-downloads')
            if album_results: album_results = album_results.order_by('-downloads')
            if blog_results: blog_results = blog_results.order_by('-views')
        else:  # relevance
            if track_results: track_results = track_results.order_by('-downloads', '-created_at')
            if album_results: album_results = album_results.order_by('-downloads', '-created_at')
            if blog_results: blog_results = blog_results.order_by('-views', '-created_at')

    total_results = sum(qs.count() for qs in [track_results, album_results, blog_results] if qs is not None)

    context = {
        'track_results': track_results or Track.objects.none(),
        'album_results': album_results or Album.objects.none(),
        'blog_results': blog_results or BlogPost.objects.none(),
        'query': query,
        'content_type': content_type,
        'sort_by': sort_by,
        'total_results': total_results,
    }
    return render(request, 'search.html', context)

def blog_list(request):
    context = {
        'posts': BlogPost.objects.all().order_by('-created_at'),
        'categories': BlogCategory.objects.all(),
    }
    return render(request, 'blog_list.html', context)

def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug)
    post.views += 1
    post.save()
    return render(request, 'blog_detail.html', {'post': post})

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('index')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('admin_dashboard' if user.is_superuser else request.GET.get('next', 'index'))
        messages.error(request, 'Invalid username/email or password.')
    else:
        form = CustomAuthenticationForm()
    return render(request, 'login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('index')

@login_required
def profile_view(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')

    user_form = UserUpdateForm(instance=request.user)
    profile_form = ProfileUpdateForm(instance=request.user.profile)

    # Consolidated stats query
    stats = Track.objects.filter(uploader=request.user).aggregate(
        total_downloads=Sum('downloads'),
        total_likes=Count('likes'),
        total_tracks=Count('id')
    )
    total_albums = Album.objects.filter(uploader=request.user).count()

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'total_albums': total_albums,
        'total_tracks': stats['total_tracks'] or 0,
        'total_downloads': stats['total_downloads'] or 0,
        'total_likes': stats['total_likes'] or 0,
        'total_uploads': total_albums + (stats['total_tracks'] or 0),
    }
    return render(request, 'profile.html', context)

@login_required
def my_uploads_view(request):
    user_albums = Album.objects.filter(uploader=request.user).order_by('-created_at')
    user_tracks = Track.objects.filter(uploader=request.user, album__isnull=True).order_by('-created_at')

    stats = Track.objects.filter(uploader=request.user).aggregate(
        total_downloads=Sum('downloads'),
        total_likes=Count('likes')
    )

    context = {
        'user_albums': user_albums,
        'user_tracks': user_tracks,
        'total_albums': user_albums.count(),
        'total_tracks': user_tracks.count(),
        'total_downloads': stats['total_downloads'] or 0,
        'total_likes': stats['total_likes'] or 0,
    }
    return render(request, 'my_uploads.html', context)

@login_required
def user_profile_view(request, username):
    user = get_object_or_404(User, username=username)
    context = {
        'profile_user': user,
        'user_albums': Album.objects.filter(uploader=user).order_by('-created_at')[:6],
        'user_tracks': Track.objects.filter(uploader=user, album__isnull=True).order_by('-created_at')[:10],
    }
    return render(request, 'user_profile.html', context)

@login_required
def edit_album(request, slug):
    album = get_object_or_404(Album, slug=slug)
    if album.uploader != request.user:
        return HttpResponseForbidden("You don't have permission to edit this album.")

    if request.method == 'POST':
        form = AlbumForm(request.POST, request.FILES, instance=album)
        if form.is_valid():
            form.save()
            messages.success(request, 'Album updated successfully!')
            return redirect('album_detail', slug=album.slug)
    
    form = AlbumForm(instance=album)
    context = {
        'form': form,
        'album': album,
        'editing': True,
    }
    return render(request, 'album_form.html', context)

@login_required
def edit_track(request, slug):
    track = get_object_or_404(Track, slug=slug)
    if track.uploader != request.user:
        return HttpResponseForbidden("You don't have permission to edit this track.")

    if request.method == 'POST':
        form = TrackForm(request.POST, request.FILES, instance=track)
        if form.is_valid():
            form.save()
            messages.success(request, 'Track updated successfully!')
            return redirect('track_detail', slug=track.slug)
    
    form = TrackForm(instance=track)
    context = {
        'form': form,
        'track': track,
        'editing': True,
    }
    return render(request, 'track_form.html', context)

@login_required
def delete_album(request, slug):
    album = get_object_or_404(Album, slug=slug)
    if album.uploader != request.user:
        return HttpResponseForbidden("You don't have permission to delete this album.")

    if request.method == 'POST':
        album.delete()
        messages.success(request, 'Album deleted successfully!')
        return redirect('my_uploads')

    return render(request, 'delete_album.html', {'album': album})

@login_required
def delete_track(request, slug):
    track = get_object_or_404(Track, slug=slug)
    if track.uploader != request.user:
        return HttpResponseForbidden("You don't have permission to delete this track.")

    if request.method == 'POST':
        track.delete()
        messages.success(request, 'Track deleted successfully!')
        return redirect('my_uploads')

    return render(request, 'delete_track.html', {'track': track})

@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if request.user != comment.user and request.user not in (getattr(comment.track, 'uploader', None), getattr(comment.album, 'uploader', None)):
        return HttpResponseForbidden("You don't have permission to delete this comment.")

    redirect_url = redirect('track_detail', slug=comment.track.slug) if comment.track else redirect('album_detail', slug=comment.album.slug)
    comment.delete()
    messages.success(request, 'Comment deleted successfully.')
    return redirect_url

@login_required
def distribution_request(request):
    user_tracks = Track.objects.filter(uploader=request.user)
    if not user_tracks.exists():
        messages.warning(request, "You don't have any tracks uploaded yet. Please upload music first.")
        return redirect('upload')

    if request.method == 'POST':
        form = DistributionRequestForm(request.POST, user=request.user)
        if form.is_valid():
            distribution_request = form.save(commit=False)
            distribution_request.artist = request.user
            distribution_request.status = 'pending'
            distribution_request.total_amount = len(form.cleaned_data['tracks']) * 1666.67
            distribution_request.save()
            form.save_m2m()
            messages.success(request, 'Distribution request created successfully! Please proceed to payment.')
            return redirect('distribution_payment', request_id=distribution_request.id)

    form = DistributionRequestForm(user=request.user)
    context = {
        'form': form,
        'platforms': DistributionPlatform.objects.filter(is_active=True),
        'base_price_per_track': 1666.67,
        'user_has_tracks': user_tracks.exists(),
    }
    return render(request, 'distribution/request.html', context)

@login_required
def distribution_payment(request, request_id):
    distribution_request = get_object_or_404(DistributionRequest, id=request_id, artist=request.user)
    if distribution_request.status != 'pending':
        messages.warning(request, 'This request has already been processed.')
        return redirect('distribution_status', request_id=request_id)

    if request.method == 'POST':
        distribution_request.status = 'paid'
        distribution_request.payment_reference = f"PMT{distribution_request.id}{request.user.id}"
        distribution_request.save()
        messages.success(request, 'Payment successful! Your distribution request is being processed.')
        return redirect('distribution_status', request_id=request_id)

    context = {
        'distribution_request': distribution_request,
        'track_count': distribution_request.get_track_count(),
        'total_amount': distribution_request.total_amount,
    }
    return render(request, 'distribution/payment.html', context)

@login_required
def distribution_status(request, request_id):
    distribution_request = get_object_or_404(DistributionRequest, id=request_id, artist=request.user)
    return render(request, 'distribution/status.html', {'distribution_request': distribution_request})

@login_required
def distribution_history(request):
    distribution_requests = DistributionRequest.objects.filter(artist=request.user).order_by('-requested_at')
    return render(request, 'distribution/history.html', {'distribution_requests': distribution_requests})

@login_required
def admin_distribution_requests(request):
    if not request.user.is_staff:
        return redirect('index')

    distribution_requests = DistributionRequest.objects.all().order_by('-requested_at')
    if status_filter := request.GET.get('status'):
        distribution_requests = distribution_requests.filter(status=status_filter)

    context = {
        'distribution_requests': distribution_requests,
        'status_choices': DistributionRequest.STATUS_CHOICES,
    }
    return render(request, 'distribution/admin_requests.html', context)

@login_required
def admin_update_status(request, request_id):
    if not request.user.is_staff:
        return redirect('index')

    distribution_request = get_object_or_404(DistributionRequest, id=request_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(DistributionRequest.STATUS_CHOICES):
            distribution_request.status = new_status
            distribution_request.save()
            messages.success(request, f'Status updated to {new_status}.')
    return redirect('admin_distribution_requests')

@login_required
def settings_view(request):
    return render(request, 'settings.html')

@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('settings')
        messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', {'form': form})

@login_required
def delete_account_view(request):
    if request.method == 'POST':
        if authenticate(username=request.user.username, password=request.POST.get('password')):
            request.user.delete()
            messages.success(request, 'Your account has been deleted successfully.')
            return redirect('index')
        messages.error(request, 'Invalid password. Account deletion failed.')
    return render(request, 'delete_account.html')

@login_required
def account_stats_view(request):
    stats = Track.objects.filter(uploader=request.user).aggregate(
        total_downloads=Sum('downloads'),
        total_likes=Count('likes'),
        total_tracks=Count('id')
    )
    context = {
        'total_albums': Album.objects.filter(uploader=request.user).count(),
        'total_tracks': stats['total_tracks'] or 0,
        'total_downloads': stats['total_downloads'] or 0,
        'total_likes': stats['total_likes'] or 0,
    }
    return render(request, 'account_stats.html', context)