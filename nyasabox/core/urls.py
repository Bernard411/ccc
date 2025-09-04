from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('upload/', views.upload_music, name='upload'),
    path('album/<slug:slug>/', views.album_detail, name='album_detail'),
    path('track/<slug:slug>/', views.track_detail, name='track_detail'),
    path('track/<slug:slug>/like/', views.like_track, name='like_track'),
    
    path('album/<slug:slug>/edit/', views.edit_album, name='edit_album'),
    path('album/<slug:slug>/delete/', views.delete_album, name='delete_album'),

    path('track/<slug:slug>/edit/', views.edit_track, name='edit_track'),
    path('track/<slug:slug>/delete/', views.delete_track, name='delete_track'),
 
    path('track/<slug:slug>/download/', views.download_track, name='download_track'),

    path('search/', views.search, name='search'),
    path('blogs/', views.blog_list, name='blog_list'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ✅ Place profile and user paths BEFORE the catch-all <slug:slug>
    path('profile/', views.profile_view, name='profile'),
    path('uploads/', views.my_uploads_view, name='my_uploads'),
    path('user/<str:username>/', views.user_profile_view, name='user_profile'),
    path('profile/change-password/', views.change_password_view, name='change_password'),
    path('profile/delete-account/', views.delete_account_view, name='delete_account'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    

    path('request/', views.distribution_request, name='distribution_request'),
    path('payment/<int:request_id>/', views.distribution_payment, name='distribution_payment'),
    path('status/<int:request_id>/', views.distribution_status, name='distribution_status'),
    path('history/', views.distribution_history, name='distribution_history'),
    path('admin/requests/', views.admin_distribution_requests, name='admin_distribution_requests'),
    path('admin/update-status/<int:request_id>/', views.admin_update_status, name='admin_update_status'),


    # Generic slug should always come LAST
    path('<slug:slug>/', views.blog_detail, name='blog_detail'),
    
    

 
  

]
    


  

