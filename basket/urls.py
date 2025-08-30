from django.urls import path
from . import views

urlpatterns = [
    path('', views.view_basket, name='view_basket'),
    path('add/<int:plan_id>/', views.add_to_basket, name='add_to_basket'),
    path('remove/<int:plan_id>/', views.remove_from_basket, name='remove_from_basket'),
    path("increment/<int:plan_id>/", views.increment_basket, name="increment_basket"),
    path("decrement/<int:plan_id>/", views.decrement_basket, name="decrement_basket"),
]
