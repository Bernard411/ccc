from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q, Count, Sum
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
import json
from .models import Album, Track, Comment, BlogPost, BlogCategory, DistributionRequest, DistributionPlatform, OTP, Profile
from .forms import AlbumForm, TrackForm, CommentForm, CustomUserCreationForm, CustomAuthenticationForm, UserUpdateForm, ProfileUpdateForm, DistributionRequestForm, OTPVerificationForm, ArtistUpgradeForm, PasswordResetRequestForm, PasswordResetConfirmForm
from functools import wraps
from django.utils import timezone
from django.template.loader import render_to_string


def artist_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to access this page.")
            return redirect('login')
        if not request.user.profile.is_artist or request.user.profile.artist_status != 'verified':
            messages.error(request, "You need a verified artist account to access this feature.")
            return redirect('become_artist')
        return view_func(request, *args, **kwargs)
    return wrapper

def index(request):
    # Existing code remains the same
    latest_albums = Album.objects.all().order_by('-created_at')[:8].annotate(track_count=Count('tracks'))

    latest_tracks = Track.objects.filter(album__isnull=True).order_by('-created_at')[:12]

    popular_tracks = Track.objects.all().order_by('-downloads')[:10]

    popular_albums = Album.objects.annotate(
        total_downloads=Sum('tracks__downloads')
    ).order_by('-total_downloads')[:6]

    top_artists_data = Track.objects.values('artist').annotate(
        track_count=Count('id'),
        total_downloads=Sum('downloads')
    ).order_by('-track_count')[:8]

    artists_with_data = []
    for artist in top_artists_data:
        sample_track = Track.objects.filter(artist=artist['artist']).first()
        artists_with_data.append({
            'name': artist['artist'],
            'track_count': artist['track_count'],
            'total_downloads': artist['total_downloads'] or 0,
            'sample_track': sample_track
        })

    tracks_data = []
    all_tracks = list(latest_tracks) + list(popular_tracks)

    for track in all_tracks:
        cover_url = ''
        if track.album and track.album.cover_art:
            cover_url = track.album.cover_art.url
        elif hasattr(track, 'cover_art') and track.cover_art:
            cover_url = track.cover_art.url

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

@artist_required
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

        if sort_by == 'newest':
            if track_results: track_results = track_results.order_by('-created_at')
            if album_results: album_results = album_results.order_by('-created_at')
            if blog_results: blog_results = blog_results.order_by('-created_at')
        elif sort_by == 'popular':
            if track_results: track_results = track_results.order_by('-downloads')
            if album_results: album_results = album_results.order_by('-downloads')
            if blog_results: blog_results = blog_results.order_by('-views')
        else:
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
            user = form.save(commit=False)
            user.is_active = False  # Deactivate until email verified
            user.save()
            profile = user.profile
            profile.is_artist = form.cleaned_data['is_artist']
            if profile.is_artist:
                profile.artist_status = 'pending'
            profile.save()

            # Generate and send OTP
            otp = OTP.objects.create(user=user, purpose='email_verification' if not profile.is_artist else 'artist_verification')
            send_mail(
                'Verify Your NyasaBox Account',
                '',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=render_to_string('emails/otp_verification.html', {'otp': otp.code, 'user': user}),
            )
            messages.success(request, 'Please check your email to verify your account.')
            return redirect('verify_otp', user_id=user.id)
        messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

def verify_otp(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            purpose = 'email_verification' if not user.profile.is_artist else 'artist_verification'
            otp = OTP.objects.filter(user=user, code=code, purpose=purpose, expires_at__gte=timezone.now()).first()
            if otp:
                user.profile.is_email_verified = True
                user.is_active = True
                if user.profile.is_artist:
                    user.profile.artist_status = 'pending'  # Await admin approval
                else:
                    user.profile.artist_status = ''
                user.profile.save()
                user.save()
                otp.delete()
                login(request, user)
                messages.success(request, 'Account verified successfully!' if not user.profile.is_artist else 'Artist account created! Awaiting admin approval.')
                return redirect('index')
            messages.error(request, 'Invalid or expired OTP.')
    else:
        form = OTPVerificationForm()
    return render(request, 'verify_otp.html', {'form': form, 'user_id': user_id})

@login_required
def become_artist(request):
    if request.user.profile.is_artist:
        messages.info(request, 'You are already registered as an artist.')
        return redirect('profile')
    
    if request.method == 'POST':
        form = ArtistUpgradeForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.is_artist = True
            profile.artist_status = 'pending'
            profile.save()

            # Generate and send OTP
            otp = OTP.objects.create(user=request.user, purpose='artist_verification')
            send_mail(
                'Verify Your NyasaBox Artist Account',
                '',
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
                html_message=render_to_string('emails/artist_verification.html', {'otp': otp.code, 'user': request.user}),
            )
            messages.success(request, 'Please check your email to verify your artist account.')
            return redirect('verify_otp', user_id=request.user.id)
        messages.error(request, 'Please correct the errors below.')
    else:
        form = ArtistUpgradeForm(instance=request.user.profile)
    return render(request, 'become_artist.html', {'form': form})

@login_required
def admin_artist_approvals(request):
    if not request.user.is_staff:
        return redirect('index')
    pending_artists = Profile.objects.filter(is_artist=True, artist_status='pending')
    context = {
        'pending_artists': pending_artists,
    }
    return render(request, 'peza/artist_approvals.html', context)

@login_required
def admin_approve_artist(request, profile_id):
    if not request.user.is_staff:
        return redirect('index')
    profile = get_object_or_404(Profile, id=profile_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            profile.artist_status = 'verified'
            profile.save()
            send_mail(
                'NyasaBox Artist Application Approved',
                '',
                settings.DEFAULT_FROM_EMAIL,
                [profile.user.email],
                html_message=render_to_string('emails/artist_approved.html', {'user': profile.user}),
            )
            messages.success(request, f'Artist {profile.user.username} approved.')
        elif action == 'reject':
            profile.artist_status = 'rejected'
            profile.save()
            send_mail(
                'NyasaBox Artist Application Rejected',
                '',
                settings.DEFAULT_FROM_EMAIL,
                [profile.user.email],
                html_message=render_to_string('emails/artist_rejected.html', {'user': profile.user}),
            )
            messages.success(request, f'Artist {profile.user.username} rejected.')
    return redirect('admin_artist_approvals')

def forgot_password(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.get(email=email)
            otp = OTP.objects.create(user=user, purpose='password_reset')
            send_mail(
                'Reset Your NyasaBox Password',
                '',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                html_message=render_to_string('emails/password_reset.html', {'otp': otp.code, 'user': user}),
            )
            messages.success(request, 'A password reset OTP has been sent to your email.')
            return redirect('reset_password', user_id=user.id)
        messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordResetRequestForm()
    return render(request, 'forgot_password.html', {'form': form})

def reset_password(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            code = request.POST.get('code')
            otp = OTP.objects.filter(user=user, code=code, purpose='password_reset', expires_at__gte=timezone.now()).first()
            if otp:
                user.set_password(form.cleaned_data['password1'])
                user.save()
                otp.delete()
                messages.success(request, 'Your password has been reset successfully.')
                return redirect('login')
            messages.error(request, 'Invalid or expired OTP.')
    else:
        form = PasswordResetConfirmForm()
    return render(request, 'reset_password.html', {'form': form, 'user_id': user_id})

def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user:
                if not user.profile.is_email_verified:
                    messages.error(request, 'Please verify your email before logging in.')
                    return redirect('verify_otp', user_id=user.id)
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
        'is_artist': request.user.profile.is_artist,
        'artist_status': request.user.profile.artist_status,
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

@artist_required
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
            if new_status == 'rejected':
                send_mail(
                    'NyasaBox Distribution Request Update',
                    '',
                    settings.DEFAULT_FROM_EMAIL,
                    [distribution_request.artist.email],
                    html_message=render_to_string('emails/distribution_rejected.html', {'request': distribution_request}),
                )
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