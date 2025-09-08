# profile_page/views.py
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Count
from django.contrib.auth.models import User
from .models import UserProfile
from .forms import UserForm, UserProfileForm, ProfileDefaultDeliveryForm
from checkout.models import Order
from ratings.utils import annotate_albums, annotate_tracks
from album.models import Album 
from tracks.models import Track
from follow_system.models import Follow

@login_required
def profile_view(request):
    """
    Display and update the logged-in user's profile.
    Includes:
      - Account details (User model)
      - Extra profile fields (UserProfile model)
      - Default delivery info
      - Order history (plans purchased)
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        user_form     = UserForm(request.POST, instance=request.user)
        profile_form  = UserProfileForm(request.POST, request.FILES, instance=profile)
        defaults_form = ProfileDefaultDeliveryForm(request.POST, instance=profile)

        if user_form.is_valid() and profile_form.is_valid() and defaults_form.is_valid():
            user_form.save()
            profile_form.save()
            defaults_form.save()
            messages.success(request, "Your profile was updated successfully!")
            return redirect("profile:profile")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        user_form     = UserForm(instance=request.user)
        profile_form  = UserProfileForm(instance=profile)
        defaults_form = ProfileDefaultDeliveryForm(instance=profile)

    # Prefer orders attached to profile, fall back to user (compatibility)
    orders = Order.objects.filter(
        Q(user_profile=profile) | Q(user=request.user)
    ).order_by("-date").prefetch_related("items", "items__plan")

    following = (
        User.objects
        .filter(follower_relations__follower=request.user)
        .select_related("userprofile")
        .distinct()
        .order_by("username")
    )

    # Followers: users that follow *me* (request.user is the following)
    followers = (
        User.objects
        .filter(following_relations__following=request.user)
        .select_related("userprofile")
        .distinct()
        .order_by("username")
    )

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
        "defaults_form": defaults_form,
        "profile": profile,     # your UserProfile instance
        "orders": orders,       # your order queryset
        "following": following,
        "followers": followers,
    }
    return render(request, "profile_page/profile.html", context)


@login_required
def order_history(request, order_number):
    """
    Allow users to click into past orders from their profile.
    Reuses the checkout success template for display.
    """
    order = get_object_or_404(Order, order_number=order_number)

    messages.info(
        request,
        f"This is a past confirmation for order number {order_number}.",
    )

    return render(
        request,
        "checkout/checkout_success.html",
        {
            "order": order,
            "from_profile": True,  # lets template hide payment form
        },
    )



def public_profile(request, username: str):
    """
    Public-facing profile page for a given user (no login required).
    Shows the user's public profile info, public albums, and tracks
    (tracks that appear in at least one public album).
    """
    view_user = get_object_or_404(User, username=username)
    profile = UserProfile.objects.filter(user=view_user).first()
    followers_count = Follow.objects.filter(following=view_user).count()
    following_count = Follow.objects.filter(follower=view_user).count()
    is_following = False
    if request.user.is_authenticated and request.user != view_user:
        is_following = Follow.objects.filter(follower=request.user, following=view_user).exists()


    public_albums = (
        annotate_albums(
            Album.objects.filter(owner=view_user, is_public=True)
                         .annotate(track_count=Count("album_tracks", distinct=True))
        )
        .order_by("-created_at")
    )

    public_tracks = (
        annotate_tracks(
            Track.objects.filter(
                track_albums__album__owner=view_user,
                track_albums__album__is_public=True,
            ).distinct()
        )
        .order_by("-created_at")
    )

    return render(request, "profile_page/public_profile.html", {
        "view_user": view_user,
        "profile": profile,
        "public_albums": public_albums,
        "public_tracks": public_tracks,
        "followers_count": followers_count,
        "following_count": following_count,
        "is_following": is_following,
    })