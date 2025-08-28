from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('tracks/', include('tracks.urls')),
    path('playlist/', include('playlist.urls')),
]
