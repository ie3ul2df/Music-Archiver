from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Plan, UserSubscription

def plan_list(request):
    """Show all available subscription plans"""
    plans = Plan.objects.all()
    return render(request, 'plans/plan_list.html', {'plans': plans})


@login_required
def subscribe(request, plan_id):
    """Subscribe current user to a plan"""
    plan = get_object_or_404(Plan, id=plan_id)
    subscription, created = UserSubscription.objects.get_or_create(user=request.user)
    subscription.plan = plan
    subscription.active = True
    subscription.save()
    messages.success(request, f"You are now subscribed to {plan.name}")
    return redirect('plan_list')
