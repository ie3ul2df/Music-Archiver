# //--------------------------- music_project/urls.py ---------------------------//
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Local apps
    path("", include("home_page.urls")),             # homepage / index
    path("tracks/", include("tracks.urls")),         # music tracks
    path("albums/", include("album.urls", namespace="album")),  # ✅ album routes
    path("plans/", include("plans.urls")),           # subscription plans
    path("basket/", include("basket.urls")),         # shopping basket
    path("profile/", include("profile_page.urls")),  # user profile
    path("checkout/", include("checkout.urls")),     # checkout flow

    # Third-party
    path("accounts/", include("allauth.urls")),      # login / signup / logout
]
