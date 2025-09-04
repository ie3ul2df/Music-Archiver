# //--------------------------- profile_page\context_processors.py ---------------------------//
from .models import UserProfile

def user_profile(request):
    if request.user.is_authenticated:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return {"profile": profile}
    return {}
