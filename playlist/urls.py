from django.urls import path
from . import views

urlpatterns = [
    path('', views.playlist_list, name='playlist_list'),
    path('add/', views.playlist_create, name='playlist_create'),
    path('<int:pk>/edit/', views.playlist_update, name='playlist_update'),
    path('<int:pk>/delete/', views.playlist_delete, name='playlist_delete'),
]
