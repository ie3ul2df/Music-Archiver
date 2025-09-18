# checkout/views.py
import json
from decimal import Decimal

import stripe
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from plans.models import Plan

from .forms import OrderForm
from .models import Order, OrderItem


def _build_basket_summary(session_basket):
    """
    Build a list of items for the template and calculate the Decimal total.
    `session_basket` is stored as {plan_id: qty} (plan_id is likely a string).
    """
    items = []
    total = Decimal("0.00")

    for plan_id, qty in session_basket.items():
        plan = get_object_or_404(Plan, id=int(plan_id))
        qty = int(qty)
        subtotal = plan.price * qty  # plan.price is Decimal
        total += subtotal
        items.append(
            {
                "plan": plan,
                "qty": qty,
                "subtotal": subtotal,
            }
        )
    return items, total


def checkout(request):
    basket = request.session.get("basket", {})
    if not basket:
        messages.error(request, "Your basket is empty.")
        return redirect("plan_list")

    # Build summary for template + amount for Stripe
    basket_items, basket_total = _build_basket_summary(basket)

    # Create PaymentIntent in pennies
    stripe.api_key = settings.STRIPE_SECRET_KEY
    amount_pennies = int((basket_total * Decimal("100")).quantize(Decimal("1")))
    intent = stripe.PaymentIntent.create(amount=amount_pennies, currency="gbp")

    if request.method == "POST":
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)

            # Attach Stripe PID and basket snapshot
            client_secret = request.POST.get("client_secret")
            if client_secret:
                order.stripe_pid = client_secret.split("_secret")[0]
            order.original_basket = json.dumps(basket)

            if request.user.is_authenticated:
                order.user = request.user
                # NEW: attach profile
                order.user_profile = getattr(request.user, "userprofile", None)

            order.save()

            # Create OrderItems
            for plan_id, qty in basket.items():
                plan = get_object_or_404(Plan, id=int(plan_id))
                OrderItem.objects.create(
                    order=order,
                    plan=plan,
                    quantity=int(qty),
                    price=plan.price,
                )

            order.refresh_from_db()

            # NEW: Save info to profile if requested
            if request.user.is_authenticated and request.POST.get("save_info"):
                profile = request.user.userprofile
                profile.default_phone_number = order.phone_number
                profile.default_country = order.country
                profile.default_postcode = order.postcode
                profile.default_town_or_city = order.town_or_city
                profile.default_street_address1 = order.street_address1
                profile.default_street_address2 = order.street_address2
                profile.default_county = order.county
                profile.save()

            return redirect("checkout_success", order_number=order.order_number)
        else:
            messages.error(
                request,
                (
                    "There was an issue with your order details. "
                    "Please review and try again."
                ),
            )
    else:
        # NEW: Pre-fill from profile
        initial = {}
        if request.user.is_authenticated:
            u = request.user
            p = getattr(u, "userprofile", None)
            initial.update(
                {
                    "full_name": (u.get_full_name() or u.username),
                    "email": u.email,
                }
            )
            if p:
                initial.update(
                    {
                        "phone_number": p.default_phone_number,
                        "country": p.default_country,
                        "postcode": p.default_postcode,
                        "town_or_city": p.default_town_or_city,
                        "street_address1": p.default_street_address1,
                        "street_address2": p.default_street_address2,
                        "county": p.default_county,
                    }
                )
        form = OrderForm(initial=initial)

    context = {
        "form": form,
        "basket_items": basket_items,
        "basket_total": basket_total,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
        "client_secret": intent.client_secret,
        "cache_checkout_url": reverse("cache_checkout_data"),
    }
    return render(request, "checkout/checkout.html", context)


def checkout_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)

    messages.success(request, f"Order processed! Your order number is {order_number}. ")

    # Clear basket
    if "basket" in request.session:
        del request.session["basket"]

    return render(request, "checkout/checkout_success.html", {"order": order})


@require_POST
def cache_checkout_data(request):
    """
    Store basket/save_info/username into PaymentIntent metadata before confirmation.
    Called by JS just before stripe.confirmCardPayment().
    """
    try:
        client_secret = request.POST.get("client_secret")
        pid = client_secret.split("_secret")[0]

        stripe.api_key = settings.STRIPE_SECRET_KEY
        stripe.PaymentIntent.modify(
            pid,
            metadata={
                "basket": json.dumps(request.session.get("basket", {})),
                "save_info": request.POST.get("save_info", "false"),
                "username": (
                    str(request.user) if request.user.is_authenticated else "anonymous"
                ),
            },
        )
        return HttpResponse(status=200)
    except Exception as e:
        return HttpResponse(content=str(e), status=400)
