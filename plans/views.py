from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Plan, UserSubscription
from checkout.models import OrderItem


def plan_list(request):
    plans = Plan.objects.all()

    if request.user.is_authenticated:
        # Find the most recent purchased OrderItem (non 4-Years)
        last_purchase = (
            OrderItem.objects.filter(order__user=request.user)
            .exclude(plan__period="4-Years")
            .order_by("-order__date")  # latest order first
            .first()
        )

        if last_purchase:
            # Hide only the last purchased non-storage plan
            plans = plans.exclude(id=last_purchase.plan.id)

        # If Premium is bought OR in basket → hide unlimited tracks/playlists
        basket = request.session.get("basket", {})
        premium_bought = OrderItem.objects.filter(
            order__user=request.user,
            plan__is_unlimited_tracks=True,
            plan__is_unlimited_playlists=True,
        ).exists()
        premium_in_basket = any(
            Plan.objects.filter(
                id=int(pid),
                is_unlimited_tracks=True,
                is_unlimited_playlists=True,
            ).exists()
            for pid in basket.keys()
        )

        if premium_bought or premium_in_basket:
            plans = plans.exclude(is_unlimited_tracks=True, is_unlimited_playlists=False)
            plans = plans.exclude(is_unlimited_playlists=True, is_unlimited_tracks=False)

    return render(request, "plans/plan_list.html", {"plans": plans})


@login_required
def subscribe(request, plan_id):
    """Manually subscribe current user to a plan (bypasses checkout)"""
    plan = get_object_or_404(Plan, id=plan_id)
    subscription, _ = UserSubscription.objects.get_or_create(user=request.user)
    subscription.plan = plan
    subscription.active = True
    subscription.save()

    messages.success(request, f"You are now subscribed to {plan.name}")
    return redirect("plan_list")
