# basket/views.py
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from plans.models import Plan


def _build_basket_summary(basket: dict):
    """
    Build a list of items for the template and calculate the Decimal total.
    Session basket format: { "<plan_id>": qty }
    """
    items = []
    total = Decimal("0.00")

    for plan_id, qty in basket.items():
        plan = get_object_or_404(Plan, id=int(plan_id))
        qty = int(qty)
        subtotal = plan.price * qty  # plan.price should be Decimal
        items.append({"plan": plan, "qty": qty, "subtotal": subtotal})
        total += subtotal

    return items, total


def view_basket(request):
    """Show basket contents with plan objects and quantities."""
    basket = request.session.get("basket", {})
    basket_plans, basket_total = _build_basket_summary(basket)

    context = {
        "basket_plans": basket_plans,
        "basket_total": basket_total,
    }
    return render(request, "basket/basket.html", context)


def add_to_basket(request, plan_id):
    """Add a plan to the basket. 4-Years plans can be multiple; others only once."""
    plan = get_object_or_404(Plan, id=plan_id)
    basket = request.session.get("basket", {})

    key = str(plan.id)

    if plan.period == "4-Years":
        # allow multiples
        basket[key] = int(basket.get(key, 0)) + 1
        messages.success(request, f"Added {plan.name} (x{basket[key]}) to basket.")
    else:
        # Premium/Unlimited — only once
        if key in basket:
            messages.warning(request, f"{plan.name} is already in your basket.")
            request.session["basket"] = basket
            return redirect("plan_list")
        basket[key] = 1
        messages.success(request, f"Added {plan.name} to basket.")

    request.session["basket"] = basket
    return redirect("plan_list")  # or redirect("view_basket") if you prefer


def remove_from_basket(request, plan_id):
    """Remove a plan entirely from the basket."""
    basket = request.session.get("basket", {})
    key = str(plan_id)

    if key in basket:
        plan = get_object_or_404(Plan, id=plan_id)
        basket.pop(key)
        request.session["basket"] = basket
        messages.success(request, f"Removed {plan.name} from your basket.")
    else:
        messages.info(request, "That plan is not in your basket.")

    return redirect("view_basket")


@login_required
def increment_basket(request, plan_id):
    """Increase quantity of 4-Year plan."""
    basket = request.session.get("basket", {})
    key = str(plan_id)

    if key not in basket:
        messages.info(request, "That plan is not in your basket.")
        return redirect("view_basket")

    plan = get_object_or_404(Plan, id=plan_id)
    if plan.period == "4-Years":
        basket[key] = int(basket.get(key, 0)) + 1
        messages.success(request, f"Increased {plan.name} to x{basket[key]}.")
    else:
        messages.warning(request, f"{plan.name} cannot have multiple quantities.")

    request.session["basket"] = basket
    return redirect("view_basket")


@login_required
def decrement_basket(request, plan_id):
    """Decrease quantity of 4-Year plan (remove if reaches zero)."""
    basket = request.session.get("basket", {})
    key = str(plan_id)

    if key not in basket:
        messages.info(request, "That plan is not in your basket.")
        return redirect("view_basket")

    plan = get_object_or_404(Plan, id=plan_id)
    if plan.period == "4-Years":
        basket[key] = int(basket.get(key, 0)) - 1
        if basket[key] <= 0:
            basket.pop(key)
            messages.info(request, f"Removed {plan.name} from your basket.")
        else:
            messages.success(request, f"Decreased {plan.name} to x{basket[key]}.")
    else:
        # Non-multiple plans are removed on decrement
        basket.pop(key)
        messages.info(request, f"Removed {plan.name} from your basket.")

    request.session["basket"] = basket
    return redirect("view_basket")
