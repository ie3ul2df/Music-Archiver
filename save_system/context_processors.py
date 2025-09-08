from album.models import Album

def user_albums_for_save(request):
    if request.user.is_authenticated:
        return {
            "user_albums": Album.objects.filter(owner=request.user).order_by("name")
        }
    return {"user_albums": []}
