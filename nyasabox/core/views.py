from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Sum, Count
from .models import Album, Track, Artist, Genre, Comment
from .forms import AlbumForm, TrackForm, CommentForm

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Count, Sum  # Added Count and Sum imports
from django.contrib import messages
import json  # Added json import
from .models import Album, Track, Comment
from .forms import AlbumForm, TrackForm, CommentForm

def index(request):
    # Get latest albums with their tracks count
    latest_albums = Album.objects.all().order_by('-created_at')[:8].annotate(
        track_count=Count('tracks')
    )
    
    # Get latest single tracks (not part of albums)
    latest_tracks = Track.objects.filter(album__isnull=True).order_by('-created_at')[:12]
    
    # Get popular tracks by downloads
    popular_tracks = Track.objects.all().order_by('-downloads')[:10]
    
    # Get popular albums by total downloads of their tracks
    popular_albums = Album.objects.annotate(
        total_downloads=Sum('tracks__downloads')
    ).order_by('-total_downloads')[:6]
    
    # Get top artists by track count and total downloads
    top_artists_data = Track.objects.values('artist').annotate(
        track_count=Count('id'),
        total_downloads=Sum('downloads')
    ).order_by('-track_count')[:8]
    
    # Format artist data
    artists_with_data = []
    for artist in top_artists_data:
        # Get a sample track for the artist
        sample_track = Track.objects.filter(artist=artist['artist']).first()
        artists_with_data.append({
            'name': artist['artist'],
            'track_count': artist['track_count'],
            'total_downloads': artist['total_downloads'] or 0,
            'sample_track': sample_track
        })
    
    
    # Prepare tracks data for JavaScript player - ensure all fields are properly formatted
    tracks_data = []
    all_tracks = list(latest_tracks) + list(popular_tracks)
    
    for track in all_tracks:
        # Get cover image URL if available
        cover_url = ''
        if track.album and track.album.cover_art:
            cover_url = track.album.cover_art.url
        elif hasattr(track, 'cover_art') and track.cover_art:
            cover_url = track.cover_art.url
            
        # Get audio file URL
        audio_url = track.audio_file.url if track.audio_file else ''
        
        tracks_data.append({
            'id': track.id,
            'title': track.title,
            'artist': track.artist,
            'url': audio_url,
            'cover_image': cover_url,
            'duration': track.get_formatted_duration() if hasattr(track, 'get_formatted_duration') and track.duration else '0:00'
        })
    
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
    
    # Get similar tracks (same genre, same artist, or same album)
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
            messages.success(request, 'Your comment has been posted!')
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
    if track.likes.filter(id=request.user.id).exists():
        track.likes.remove(request.user)
        liked = False
    else:
        track.likes.add(request.user)
        liked = True
    
    return JsonResponse({'liked': liked, 'likes_count': track.likes.count()})

def download_track(request, slug):
    track = get_object_or_404(Track, slug=slug)
    track.downloads += 1
    track.save()
    
    # In a real implementation, you would serve the file here
    # For now, we'll just redirect to the file URL
    return redirect(track.audio_file.url)

@login_required
def upload_music(request):
    if request.method == 'POST':
        # Check which form was submitted
        if 'form_type' in request.POST and request.POST['form_type'] == 'album':
            album_form = AlbumForm(request.POST, request.FILES)
            if album_form.is_valid():
                album = album_form.save(commit=False)
                album.uploader = request.user
                album.save()
                
                # Process track files
                track_files = request.FILES.getlist('track_files[]')
                track_numbers = request.POST.getlist('track_numbers[]')
                track_titles = request.POST.getlist('track_titles[]')
                
                for i, (track_file, track_number, track_title) in enumerate(zip(track_files, track_numbers, track_titles)):
                    if track_file and track_title:  # Ensure we have both file and title
                        track = Track(
                            title=track_title,
                            album=album,
                            artist=album.artist,  # Use album artist
                            genre=album.genre,    # Use album genre
                            audio_file=track_file,
                            track_number=track_number,
                            uploader=request.user
                        )
                        track.save()
                
                messages.success(request, f'Album "{album.title}" uploaded successfully with {len(track_files)} tracks!')
                return redirect('album_detail', slug=album.slug)
        
        elif 'form_type' in request.POST and request.POST['form_type'] == 'track':
            track_form = TrackForm(request.POST, request.FILES, initial={'user': request.user})
            if track_form.is_valid():
                track = track_form.save(commit=False)
                track.uploader = request.user
                
                # If no genre is selected but album is selected, use album's genre
                if not track.genre and track.album:
                    track.genre = track.album.genre
                
                track.save()
                messages.success(request, f'Track "{track.title}" uploaded successfully!')
                return redirect('track_detail', slug=track.slug)
    
    else:
        album_form = AlbumForm()
        track_form = TrackForm(initial={'user': request.user})
    
    context = {
        'album_form': album_form,
        'track_form': track_form,
    }
    return render(request, 'upload.html', context)
def search(request):
    query = request.GET.get('q')
    track_results = []
    album_results = []
    
    if query:
        # Search tracks
        track_results = Track.objects.filter(
            Q(title__icontains=query) |
            Q(artist__icontains=query) |
            Q(album__title__icontains=query)
        ).distinct()
        
        # Search albums
        album_results = Album.objects.filter(
            Q(title__icontains=query) |
            Q(artist__icontains=query) |
            Q(description__icontains=query)
        ).distinct()
    
    total_results = len(track_results) + len(album_results)
    
    context = {
        'track_results': track_results,
        'album_results': album_results,
        'query': query,
        'total_results': total_results,
    }
    return render(request, 'search.html', context)


from django.shortcuts import render, get_object_or_404
from .models import BlogPost, BlogCategory

def blog_list(request):
    posts = BlogPost.objects.all().order_by('-created_at')
    categories = BlogCategory.objects.all()
    
    context = {
        'posts': posts,
        'categories': categories,
    }
    return render(request, 'blog_list.html', context)

def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug)
    post.views += 1
    post.save()
    
    context = {
        'post': post,
    }
    return render(request, 'blog_detail.html', context)


from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, CustomAuthenticationForm

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('index')
        else:
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
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                
                # Redirect admins to admin dashboard
                if user.is_superuser:
                    return redirect('admin_dashboard')
                
                next_url = request.GET.get('next', 'index')
                return redirect(next_url)
        else:
            messages.error(request, 'Invalid username/email or password.')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('index')


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import UserUpdateForm, ProfileUpdateForm


# ... existing register, login, logout views ...

@login_required
def profile_view(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(
            request.POST, 
            request.FILES, 
            instance=request.user.profile
        )
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    return render(request, 'profile.html', context)

@login_required
def my_uploads_view(request):
    # Get user's albums and tracks
    user_albums = Album.objects.filter(uploader=request.user).order_by('-created_at')
    user_tracks = Track.objects.filter(uploader=request.user, album__isnull=True).order_by('-created_at')
    
    # Get total stats
    total_albums = user_albums.count()
    total_tracks = user_tracks.count()
    total_downloads = sum(track.downloads for track in Track.objects.filter(uploader=request.user))
    
    context = {
        'user_albums': user_albums,
        'user_tracks': user_tracks,
        'total_albums': total_albums,
        'total_tracks': total_tracks,
        'total_downloads': total_downloads,
    }
    return render(request, 'my_uploads.html', context)

@login_required
def user_profile_view(request, username):
    user = get_object_or_404(User, username=username)
    user_albums = Album.objects.filter(uploader=user).order_by('-created_at')[:6]
    user_tracks = Track.objects.filter(uploader=user, album__isnull=True).order_by('-created_at')[:10]
    
    context = {
        'profile_user': user,
        'user_albums': user_albums,
        'user_tracks': user_tracks,
    }
    return render(request, 'user_profile.html', context)



from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q
from django.contrib import messages
from .models import Album, Track, Artist, Genre, Comment
from .forms import AlbumForm, TrackForm, CommentForm

# ... existing views ...

@login_required
def edit_album(request, slug):
    album = get_object_or_404(Album, slug=slug)
    
    # Check if user owns the album
    if album.uploader != request.user:
        return HttpResponseForbidden("You don't have permission to edit this album.")
    
    if request.method == 'POST':
        form = AlbumForm(request.POST, request.FILES, instance=album)
        if form.is_valid():
            form.save()
            messages.success(request, 'Album updated successfully!')
            return redirect('album_detail', slug=album.slug)
    else:
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
    
    # Check if user owns the track
    if track.uploader != request.user:
        return HttpResponseForbidden("You don't have permission to edit this track.")
    
    if request.method == 'POST':
        form = TrackForm(request.POST, request.FILES, instance=track)
        if form.is_valid():
            form.save()
            messages.success(request, 'Track updated successfully!')
            return redirect('track_detail', slug=track.slug)
    else:
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
    
    # Check if user owns the album
    if album.uploader != request.user:
        return HttpResponseForbidden("You don't have permission to delete this album.")
    
    if request.method == 'POST':
        album.delete()
        messages.success(request, 'Album deleted successfully!')
        return redirect('my_uploads')
    
    context = {
        'album': album,
    }
    return render(request, 'delete_album.html', context)

@login_required
def delete_track(request, slug):
    track = get_object_or_404(Track, slug=slug)
    
    # Check if user owns the track
    if track.uploader != request.user:
        return HttpResponseForbidden("You don't have permission to delete this track.")
    
    if request.method == 'POST':
        track.delete()
        messages.success(request, 'Track deleted successfully!')
        return redirect('my_uploads')
    
    context = {
        'track': track,
    }
    return render(request, 'delete_track.html', context)



from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from .forms import UserUpdateForm, ProfileUpdateForm





@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Check if user owns the comment or is the track/album uploader
    if request.user != comment.user and request.user != comment.track.uploader and request.user != comment.album.uploader:
        return HttpResponseForbidden("You don't have permission to delete this comment.")
    
    # Store the redirect URL before deleting
    if comment.track:
        redirect_url = redirect('track_detail', slug=comment.track.slug)
    else:
        redirect_url = redirect('album_detail', slug=comment.album.slug)
    
    comment.delete()
    messages.success(request, 'Comment deleted successfully.')
    return redirect_url


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from .models import DistributionRequest, DistributionPlatform
from .forms import DistributionRequestForm
from .models import Track
import requests
import json

@login_required
def distribution_request(request):
    user_tracks = Track.objects.filter(uploader=request.user)
    
    if not user_tracks.exists():
        messages.warning(request, "You don't have any tracks uploaded yet. Please upload music first.")
        return redirect('upload')
    
    if request.method == 'POST':
        form = DistributionRequestForm(request.POST, user=request.user)
        if form.is_valid():
            # First save the distribution request without committing (no many-to-many)
            distribution_request = form.save(commit=False)
            distribution_request.artist = request.user
            distribution_request.status = 'pending'
            
            # Calculate total amount
            selected_tracks = form.cleaned_data['tracks']
            base_price_per_track = 1666.67
            distribution_request.total_amount = len(selected_tracks) * base_price_per_track
            
            # Save the distribution request to get an ID
            distribution_request.save()
            
            # Now save the many-to-many relationships using form.save_m2m()
            form.save_m2m()
            
            messages.success(request, 'Distribution request created successfully! Please proceed to payment.')
            return redirect('distribution_payment', request_id=distribution_request.id)
    else:
        form = DistributionRequestForm(user=request.user)
    
    # Calculate pricing information
    base_price_per_track = 1666.67
    platforms = DistributionPlatform.objects.filter(is_active=True)
    
    context = {
        'form': form,
        'platforms': platforms,
        'base_price_per_track': base_price_per_track,
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
        # Simulate payment processing (in real implementation, integrate with Airtel Money/TNM API)
        payment_method = request.POST.get('payment_method')
        phone_number = request.POST.get('phone_number')
        
        # Here you would integrate with actual payment gateway
        # For now, we'll simulate successful payment
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
    
    context = {
        'distribution_request': distribution_request,
    }
    return render(request, 'distribution/status.html', context)

@login_required
def distribution_history(request):
    distribution_requests = DistributionRequest.objects.filter(artist=request.user).order_by('-requested_at')
    
    context = {
        'distribution_requests': distribution_requests,
    }
    return render(request, 'distribution/history.html', context)

# Admin views
@login_required
def admin_distribution_requests(request):
    if not request.user.is_staff:
        return redirect('index')
    
    distribution_requests = DistributionRequest.objects.all().order_by('-requested_at')
    status_filter = request.GET.get('status')
    
    if status_filter:
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


from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden
from .forms import UserUpdateForm, ProfileUpdateForm
from .models import Album, Track

@login_required
def settings_view(request):
    return render(request, 'settings.html')

@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important to keep user logged in
            messages.success(request, 'Your password was successfully updated!')
            return redirect('settings')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'change_password.html', {'form': form})

@login_required
def delete_account_view(request):
    if request.method == 'POST':
        # Verify password
        password = request.POST.get('password')
        user = authenticate(username=request.user.username, password=password)
        
        if user is not None:
            # Delete user account and all associated data
            user.delete()
            messages.success(request, 'Your account has been deleted successfully.')
            return redirect('index')
        else:
            messages.error(request, 'Invalid password. Account deletion failed.')
    
    return render(request, 'delete_account.html')

@login_required
def account_stats_view(request):
    # Get user statistics
    total_albums = Album.objects.filter(uploader=request.user).count()
    total_tracks = Track.objects.filter(uploader=request.user).count()
    total_downloads = sum(track.downloads for track in Track.objects.filter(uploader=request.user))
    total_likes = sum(track.likes.count() for track in Track.objects.filter(uploader=request.user))
    
    context = {
        'total_albums': total_albums,
        'total_tracks': total_tracks,
        'total_downloads': total_downloads,
        'total_likes': total_likes,
    }
    return render(request, 'account_stats.html', context)