from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Album, Track, DistributionRequest, DistributionPlatform
from .models import BlogPost, BlogCategory
from django.db.models import Sum, Count, Q  # Add Q import
from django.utils import timezone
from datetime import timedelta
from django import forms  # Add forms import
from django.db import models  # Add models import

# Check if user is peza/superuser
def is_admin(user):
    return user.is_authenticated and user.is_superuser

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    # Statistics
    total_users = User.objects.count()
    total_albums = Album.objects.count()
    total_tracks = Track.objects.count()
    total_blogs = BlogPost.objects.count()
    
    # Distribution stats
    distribution_stats = DistributionRequest.objects.aggregate(
        total_requests=Count('id'),
        total_revenue=Sum('total_amount'),
        pending_requests=Count('id', filter=Q(status='pending')),
        paid_requests=Count('id', filter=Q(status='paid'))
    )
    
    # Recent activity
    recent_users = User.objects.order_by('-date_joined')[:5]
    recent_distributions = DistributionRequest.objects.select_related('artist').order_by('-requested_at')[:5]
    
    context = {
        'total_users': total_users,
        'total_albums': total_albums,
        'total_tracks': total_tracks,
        'total_blogs': total_blogs,
        'distribution_stats': distribution_stats,
        'recent_users': recent_users,
        'recent_distributions': recent_distributions,
    }
    return render(request, 'peza/dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def admin_users(request):
    users = User.objects.all().order_by('-date_joined')
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        user = get_object_or_404(User, id=user_id)
        
        if action == 'toggle_active':
            user.is_active = not user.is_active
            user.save()
            status = "activated" if user.is_active else "deactivated"
            messages.success(request, f'User {user.username} has been {status}.')
        elif action == 'delete':
            user.delete()
            messages.success(request, f'User {user.username} has been deleted.')
    
    return render(request, 'peza/users.html', {'users': users})

@login_required
@user_passes_test(is_admin)
def admin_albums(request):
    albums = Album.objects.select_related('uploader').order_by('-created_at')
    return render(request, 'peza/albums.html', {'albums': albums})

@login_required
@user_passes_test(is_admin)
def admin_tracks(request):
    tracks = Track.objects.select_related('uploader', 'album').order_by('-created_at')
    return render(request, 'peza/tracks.html', {'tracks': tracks})

@login_required
@user_passes_test(is_admin)
def admin_distribution_requests(request):
    status_filter = request.GET.get('status')
    
    distribution_requests = DistributionRequest.objects.select_related(
        'artist'
    ).prefetch_related(
        'tracks', 'platforms'
    ).order_by('-requested_at')
    
    if status_filter:
        distribution_requests = distribution_requests.filter(status=status_filter)
    
    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        new_status = request.POST.get('status')
        distribution_request = get_object_or_404(DistributionRequest, id=request_id)
        
        if new_status in dict(DistributionRequest.STATUS_CHOICES):
            distribution_request.status = new_status
            if new_status == 'distributed':
                distribution_request.distributed_date = timezone.now()
            distribution_request.save()
            messages.success(request, f'Distribution request status updated to {new_status}.')
    
    return render(request, 'peza/distribution_requests.html', {
        'distribution_requests': distribution_requests,
        'status_choices': DistributionRequest.STATUS_CHOICES,
    })

@login_required
@user_passes_test(is_admin)
def admin_upload_content(request):
    if request.method == 'POST':
        # Handle manual content upload by admin
        # This would need a form similar to the user upload form but with more capabilities
        messages.success(request, 'Content uploaded successfully!')
        return redirect('admin_upload_content')
    
    return render(request, 'peza/upload_content.html')

@login_required
@user_passes_test(is_admin)
def admin_blog_management(request):
    blog_posts = BlogPost.objects.select_related('author', 'category').order_by('-created_at')
    categories = BlogCategory.objects.all()
    
    if request.method == 'POST':
        post_id = request.POST.get('post_id')
        action = request.POST.get('action')
        
        if action == 'delete':
            post = get_object_or_404(BlogPost, id=post_id)
            post.delete()
            messages.success(request, 'Blog post deleted successfully!')
    
    return render(request, 'peza/blog_management.html', {
        'blog_posts': blog_posts,
        'categories': categories,
    })

@login_required
@user_passes_test(is_admin)
def admin_revenue(request):
    # Revenue statistics
    revenue_stats = DistributionRequest.objects.filter(status='paid').aggregate(
        total_revenue=Sum('total_amount'),
        total_requests=Count('id')
    )
    
    # Monthly revenue
    thirty_days_ago = timezone.now() - timedelta(days=30)
    monthly_revenue = DistributionRequest.objects.filter(
        status='paid',
        payment_date__gte=thirty_days_ago
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Revenue by platform
    revenue_by_platform = DistributionPlatform.objects.annotate(
        total_revenue=Sum('distribution_requests__total_amount', 
                         filter=Q(distribution_requests__status='paid')),
        request_count=Count('distribution_requests', 
                           filter=Q(distribution_requests__status='paid'))
    )
    
    context = {
        'revenue_stats': revenue_stats,
        'monthly_revenue': monthly_revenue,
        'revenue_by_platform': revenue_by_platform,
    }
    return render(request, 'peza/revenue.html', context)

@login_required
@user_passes_test(is_admin)
def admin_create_blog(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        category_id = request.POST.get('category')
        featured_image = request.FILES.get('featured_image')
        is_published = request.POST.get('is_published') == 'on'
        is_featured = request.POST.get('featured_post') == 'on'
        excerpt = request.POST.get('excerpt', '')[:200]  # Limit to 200 chars
        tags = request.POST.get('tags', '')
        
        if title and content:
            category = None
            if category_id:
                category = get_object_or_404(BlogCategory, id=category_id)
            
            blog_post = BlogPost(
                title=title,
                content=content,
                category=category,
                author=request.user,
                is_published=is_published,
                is_featured=is_featured,
                excerpt=excerpt,
                tags=tags
            )
            
            if featured_image:
                blog_post.featured_image = featured_image
                
            blog_post.save()
            messages.success(request, 'Blog post created successfully!')
            return redirect('admin_blog_management')
        else:
            messages.error(request, 'Please fill in all required fields (title and content).')
    
    categories = BlogCategory.objects.all()
    return render(request, 'peza/create_blog.html', {'categories': categories})

# Optional: Add a preview function
@login_required
@user_passes_test(is_admin)
def admin_create_blog_preview(request):
    if request.method == 'POST':
        title = request.POST.get('title', 'Preview Title')
        content = request.POST.get('content', 'Preview content goes here...')
        
        context = {
            'preview_title': title,
            'preview_content': content,
            'is_preview': True
        }
        return render(request, 'blog/blog_preview.html', context)
    
    return redirect('admin_create_blog')

@login_required
@user_passes_test(is_admin)
def admin_edit_blog(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)
    
    if request.method == 'POST':
        post.title = request.POST.get('title')
        post.content = request.POST.get('content')
        category_id = request.POST.get('category')
        
        if category_id:
            post.category = get_object_or_404(BlogCategory, id=category_id)
        else:
            post.category = None
            
        if 'featured_image' in request.FILES:
            post.featured_image = request.FILES['featured_image']
            
        post.save()
        messages.success(request, 'Blog post updated successfully!')
        return redirect('admin_blog_management')
    
    categories = BlogCategory.objects.all()
    return render(request, 'peza/edit_blog.html', {
        'post': post,
        'categories': categories,
    })