from album.models import Album


def user_albums_for_save(request):
    if not request.user.is_authenticated:
        return {"save_albums": [], "user_albums": []}
    qs = Album.objects.filter(owner=request.user).only("id", "name").order_by("name")
    return {"save_albums": qs, "user_albums": qs}
