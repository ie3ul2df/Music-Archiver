from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Follow

User = get_user_model()

def _counts_for(user):
    return {
        "followers": Follow.objects.filter(following=user).count(),
        "following": Follow.objects.filter(follower=user).count(),
    }

@login_required
@require_POST
def toggle_follow(request, username):
    target = get_object_or_404(User, username=username)
    if target == request.user:
        return JsonResponse({"ok": False, "error": "You cannot follow yourself."}, status=400)

    rel, created = Follow.objects.get_or_create(follower=request.user, following=target)
    if not created:
        # already following -> unfollow
        rel.delete()
        state = "unfollowed"
        is_following = False
    else:
        state = "followed"
        is_following = True

    counts = _counts_for(target)
    return JsonResponse({"ok": True, "state": state, "is_following": is_following, **counts})

@login_required
@require_POST
def follow_user(request, username):
    target = get_object_or_404(User, username=username)
    if target == request.user:
        return JsonResponse({"ok": False, "error": "You cannot follow yourself."}, status=400)
    _, created = Follow.objects.get_or_create(follower=request.user, following=target)
    counts = _counts_for(target)
    return JsonResponse({"ok": True, "created": created, "is_following": True, **counts})

@login_required
@require_POST
def unfollow_user(request, username):
    target = get_object_or_404(User, username=username)
    if target == request.user:
        return JsonResponse({"ok": False, "error": "You cannot unfollow yourself."}, status=400)
    Follow.objects.filter(follower=request.user, following=target).delete()
    counts = _counts_for(target)
    return JsonResponse({"ok": True, "is_following": False, **counts})

# (Optional) public lists
def followers_list(request, username):
    target = get_object_or_404(User, username=username)
    qs = User.objects.filter(following_relations__following=target).order_by("username")
    return render(request, "follow_system/followers_list.html", {"view_user": target, "followers": qs})

def following_list(request, username):
    target = get_object_or_404(User, username=username)
    qs = User.objects.filter(follower_relations__follower=target).order_by("username")
    return render(request, "follow_system/following_list.html", {"view_user": target, "following": qs})
