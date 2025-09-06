# profile_page/views.py
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q

from .models import UserProfile
from .forms import UserForm, UserProfileForm, ProfileDefaultDeliveryForm
from checkout.models import Order


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
            return redirect("profile")
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

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
        "defaults_form": defaults_form,
        "profile": profile,
        "orders": orders,
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
