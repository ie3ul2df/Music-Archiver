from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home_page.urls')),
    path('tracks/', include('tracks.urls')),
    path('playlist/', include('playlist.urls')),
    path('plans/', include('plans.urls')),
    path('basket/', include('basket.urls')),
    path('accounts/', include('allauth.urls')),
    path('profile/', include('profile_page.urls')),
    path('checkout/', include('checkout.urls')),
]
