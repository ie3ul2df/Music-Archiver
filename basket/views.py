from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from plans.models import Plan


def view_basket(request):
    """Show basket contents with plan objects and quantities"""
    basket = request.session.get("basket", {})
    basket_plans = []
    total = 0

    for plan_id, qty in basket.items():
        plan = get_object_or_404(Plan, id=plan_id)
        subtotal = plan.price * qty
        total += subtotal
        basket_plans.append({
            "plan": plan,
            "qty": qty,
            "subtotal": subtotal
        })

    context = {
        "basket_plans": basket_plans,
        "basket_total": total,
    }
    return render(request, "basket/basket.html", context)


def add_to_basket(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)
    basket = request.session.get("basket", {})

    if plan.period == "4-Years":
        # allow multiples
        basket[str(plan.id)] = int(basket.get(str(plan.id), 0)) + 1
        messages.success(request, f"Added {plan.name} (x{basket[str(plan.id)]}) to basket.")
    else:
        # Premium / Unlimited — only once
        if str(plan.id) in basket:
            messages.warning(request, f"{plan.name} is already in your basket.")
            return redirect("plan_list")
        basket[str(plan.id)] = 1  # ✅ force integer not boolean

    request.session["basket"] = basket
    return redirect("plan_list")



def remove_from_basket(request, plan_id):
    """Remove a plan entirely from basket"""
    basket = request.session.get("basket", {})
    if str(plan_id) in basket:
        plan = get_object_or_404(Plan, id=plan_id)
        basket.pop(str(plan_id))
        request.session["basket"] = basket
        messages.success(request, f"Removed {plan.name} from your basket.")
    return redirect("view_basket")


@login_required
def increment_basket(request, plan_id):
    """Increase quantity of 4-Year plan"""
    basket = request.session.get("basket", {})
    if str(plan_id) in basket:
        plan = get_object_or_404(Plan, id=plan_id)
        if plan.period == "4-Years":
            basket[str(plan_id)] += 1
            messages.success(request, f"Increased {plan.name} to x{basket[str(plan_id)]}.")
        else:
            messages.warning(request, f"{plan.name} cannot have multiple quantities.")
    request.session["basket"] = basket
    return redirect("view_basket")


@login_required
def decrement_basket(request, plan_id):
    """Decrease quantity of 4-Year plan"""
    basket = request.session.get("basket", {})
    if str(plan_id) in basket:
        plan = get_object_or_404(Plan, id=plan_id)
        if plan.period == "4-Years":
            basket[str(plan_id)] -= 1
            if basket[str(plan_id)] <= 0:
                del basket[str(plan_id)]
                messages.info(request, f"Removed {plan.name} from your basket.")
            else:
                messages.success(request, f"Decreased {plan.name} to x{basket[str(plan_id)]}.")
        else:
            # Premium/unlimited plans → always single
            del basket[str(plan_id)]
            messages.info(request, f"Removed {plan.name} from your basket.")
    request.session["basket"] = basket
    return redirect("view_basket")
