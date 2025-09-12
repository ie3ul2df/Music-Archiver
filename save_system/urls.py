from django.urls import path
from . import views

app_name = "save_system"

urlpatterns = [
    path("album/<int:pk>/save/", views.save_album, name="save_album"),
    path("tracks/<int:pk>/save/", views.save_track, name="save_track"),
    path("tracks/bulk-save/", views.bulk_save_tracks, name="bulk_save_tracks"),
]
