from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import UserProfile
from .forms import UserForm, UserProfileForm
from checkout.models import OrderItem


@login_required
def profile_view(request):
    """
    Display and update the logged-in user's profile.
    Includes both account details (User model)
    and extra profile details (UserProfile model).
    Also shows purchased plans from checkout.
    """
    # Ensure profile exists for this user
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(
            request.POST, request.FILES, instance=profile
        )

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your profile was updated successfully!")
            return redirect("profile")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=profile)

    # Purchased plans (order history)
    purchased_items = OrderItem.objects.filter(order__user=request.user)

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
        "profile": profile,
        "purchased_items": purchased_items,
    }
    return render(request, "profile_page/profile.html", context)
