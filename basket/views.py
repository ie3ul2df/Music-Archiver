from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from plans.models import Plan

def view_basket(request):
    """Show basket contents"""
    basket = request.session.get('basket', {})
    plans = []
    total = 0

    for plan_id in basket.keys():
        plan = get_object_or_404(Plan, id=plan_id)
        plans.append(plan)
        total += float(plan.price)

    context = {
        'plans': plans,
        'total': total,
    }
    return render(request, 'basket/basket.html', context)


def add_to_basket(request, plan_id):
    """Add a plan to basket"""
    basket = request.session.get('basket', {})
    basket[str(plan_id)] = 1   # store plan ID, value doesn’t matter
    request.session['basket'] = basket

    plan = get_object_or_404(Plan, id=plan_id)
    messages.success(request, f"Added {plan.name} to your basket")
    return redirect('plan_list')


def remove_from_basket(request, plan_id):
    """Remove a plan from basket"""
    basket = request.session.get('basket', {})
    if str(plan_id) in basket:
        basket.pop(str(plan_id))
        request.session['basket'] = basket
        plan = get_object_or_404(Plan, id=plan_id)
        messages.success(request, f"Removed {plan.name} from your basket")
    return redirect('view_basket')
