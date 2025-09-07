from django.urls import path
from . import views, admin_views

urlpatterns = [
    # Public routes
    path('', views.index, name='index'),
    path('search/', views.search, name='search'),
    

    # Authentication routes
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-otp/<int:user_id>/', views.verify_otp, name='verify_otp'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<int:user_id>/', views.reset_password, name='reset_password'),
    path('become-artist/', views.become_artist, name='become_artist'),

    # User routes
    path('profile/', views.profile_view, name='profile'),
    path('profile/stats/', views.account_stats_view, name='account_stats'),
    path('profile/change-password/', views.change_password_view, name='change_password'),
    path('profile/delete-account/', views.delete_account_view, name='delete_account'),
    path('settings/', views.settings_view, name='settings'),
    path('uploads/', views.my_uploads_view, name='my_uploads'),
    path('user/<str:username>/', views.user_profile_view, name='user_profile'),

    # Music routes
    path('upload/', views.upload_music, name='upload'),
    path('album/<slug:slug>/', views.album_detail, name='album_detail'),
    path('album/<slug:slug>/edit/', views.edit_album, name='edit_album'),
    path('album/<slug:slug>/delete/', views.delete_album, name='delete_album'),
    path('track/<slug:slug>/', views.track_detail, name='track_detail'),
    path('track/<slug:slug>/edit/', views.edit_track, name='edit_track'),
    path('track/<slug:slug>/delete/', views.delete_track, name='delete_track'),
    path('track/<slug:slug>/like/', views.like_track, name='like_track'),
    path('track/<slug:slug>/download/', views.download_track, name='download_track'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),

    # Distribution routes
    path('request/', views.distribution_request, name='distribution_request'),
    path('payment/<int:request_id>/', views.distribution_payment, name='distribution_payment'),
    path('status/<int:request_id>/', views.distribution_status, name='distribution_status'),
    path('history/', views.distribution_history, name='distribution_history'),

    # Admin routes
    path('admin/dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/users/', admin_views.admin_users, name='admin_users'),
    path('admin/albums/', admin_views.admin_albums, name='admin_albums'),
    path('admin/tracks/', admin_views.admin_tracks, name='admin_tracks'),
    path('admin/distribution-requests/', views.admin_distribution_requests, name='admin_distribution_requests'),
    path('admin/update-status/<int:request_id>/', views.admin_update_status, name='admin_update_status'),
    path('admin/upload-content/', admin_views.admin_upload_content, name='admin_upload_content'),
    path('admin/blog-management/', admin_views.admin_blog_management, name='admin_blog_management'),
    path('admin/blog-create/', admin_views.admin_create_blog, name='create_blog'),
    path('admin/revenue/', admin_views.admin_revenue, name='admin_revenue'),
    path('admin/edit-blog/<int:post_id>/', admin_views.admin_edit_blog, name='admin_edit_blog'),
    path('admin/create-blog-preview/', admin_views.admin_create_blog_preview, name='admin_create_blog_preview'),

    # blog routes
    path('blogs/', views.blog_list, name='blog_list'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
]