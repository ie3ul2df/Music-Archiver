# cloud_connect/urls.py
from django.urls import path

from . import views

app_name = "cloud"

urlpatterns = [
    path("connect/<str:provider>/", views.connect, name="connect"),
    path("callback/<str:provider>/", views.callback, name="callback"),
    path(
        "link_album_folder/<int:album_id>/",
        views.link_album_folder,
        name="link_album_folder",
    ),
    path("sync_album/<int:album_id>/", views.sync_album, name="sync_album"),
    path("stream/<str:provider>/<str:file_id>/", views.stream_file, name="stream"),
]
