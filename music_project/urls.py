# //--------------------------- music_project/urls.py ---------------------------//
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Local apps
    path("", include("home_page.urls")),             # homepage / index
    path("tracks/", include("tracks.urls")),         # music tracks
    path("album/", include(("album.urls", "album"), namespace="album")),  # album routes
    path("plans/", include("plans.urls")),           # subscription plans
    path("basket/", include("basket.urls")),         # shopping basket
    path("profile/", include(("profile_page.urls", "profile"), namespace="profile")),  # user profile
    path("checkout/", include("checkout.urls")),     # checkout flow
    path("ratings/", include("ratings.urls")),       # rating system
    path("save/", include("save_system.urls")),      # save system

    # Third-party
    path("accounts/", include("allauth.urls")),      # login / signup / logout
]
