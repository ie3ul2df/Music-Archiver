# //--------------------------- home_page/views.py ---------------------------//
from django.shortcuts import render
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from album.models import Album, AlbumTrack
from tracks.models import Track
from django.http import JsonResponse
from django.template.loader import render_to_string


def index(request):
    public_albums = (
        Album.objects.filter(is_public=True)
        .select_related("owner")
        .annotate(track_count=Count("album_tracks", distinct=True))
        .order_by("-created_at")[:12]
    )
    return render(request, "home_page/index.html", {"public_albums": public_albums})


def search(request):
    q = (request.GET.get("q") or "").strip()
    scope = (request.GET.get("t") or "all").lower()
    User = get_user_model()

    albums = tracks = users = []
    total = 0

    if q:
        if scope in ("all", "albums"):
            albums = list(
                Album.objects.filter(is_public=True)
                .select_related("owner")
                .annotate(track_count=Count("album_tracks", distinct=True))  
                .filter(
                    Q(name__icontains=q)
                    | Q(description__icontains=q)
                    | Q(owner__username__icontains=q)
                    | Q(owner__first_name__icontains=q)
                    | Q(owner__last_name__icontains=q)
                )
                .order_by("-created_at")[:50]
            )
            total += len(albums)

        if scope in ("all", "tracks"):
            tracks = list(
                Track.objects.filter(
                    track_albums__album__is_public=True  # ✅ correct
                )
                .filter(
                    Q(name__icontains=q) | Q(source_url__icontains=q)
                )
                .select_related("owner")
                .distinct()
                .order_by("-created_at")[:50]
            )
            total += len(tracks)

        if scope in ("all", "users"):
            users = list(
                User.objects.filter(albums__is_public=True)
                .filter(
                    Q(username__icontains=q)
                    | Q(first_name__icontains=q)
                    | Q(last_name__icontains=q)
                )
                .annotate(
                    public_album_count=Count(
                        "albums", filter=Q(albums__is_public=True), distinct=True
                    )
                )
                .distinct()
                .order_by("-public_album_count", "username")[:50]
            )
            total += len(users)

    context = {"q": q, "scope": scope, "albums": albums, "tracks": tracks, "users": users, "total": total}

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = {
            "albums": render_to_string("home_page/partials/_search_albums.html", context, request=request),
            "tracks": render_to_string("home_page/partials/_search_tracks.html", context, request=request),
            "users": render_to_string("home_page/partials/_search_users.html", context, request=request),
            "summary": render_to_string("home_page/partials/_search_summary.html", context, request=request),
            "empty": render_to_string("home_page/partials/_search_empty.html", context, request=request),
        }
        return JsonResponse({"q": q, "scope": scope, "total": total, "html": html})

    return render(request, "home_page/search.html", context)