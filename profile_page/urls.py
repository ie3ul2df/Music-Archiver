from django.urls import path
from . import views

urlpatterns = [
    path('', views.profile_view, name='profile'),
    path('order_history/<order_number>/', views.order_history, name='order_history'),
    path("u/<str:username>/", views.public_profile, name="public_profile"),
]
