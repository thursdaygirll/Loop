from django.urls import path
from . import views


urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('dashboard/', views.dashboard_view),
    path('habits/', views.habits_view, name='habits'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile_view, name='profile'),
    path('upload_profile_picture/', views.upload_profile_picture, name='upload_profile_picture'),
    path('update_profile/', views.update_profile, name='update_profile'),
    path('get_profile/<str:user_id>/', views.get_profile, name='get_profile'),
    path('auth/google/', views.google_login, name='google_login'),
    path('auth/google/callback/', views.google_callback, name='google_callback'),
    path('logout/', views.logout_view, name='logout'),
    path('login-firebase/', views.login_firebase_view, name='login_firebase'),
    path('auth/firebase-google/', views.firebase_google_auth, name='firebase_google_auth'),
]
