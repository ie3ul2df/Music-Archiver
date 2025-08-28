from django.urls import path
from . import views

urlpatterns = [
    path('', views.track_list, name='track_list'),
    path('add/', views.track_create, name='track_create'),
    path('<int:pk>/edit/', views.track_update, name='track_update'),
    path('<int:pk>/delete/', views.track_delete, name='track_delete'),
]
