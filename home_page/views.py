# //--------------------------- home_page/views.py ---------------------------//
from django.shortcuts import render, redirect
from django.db.models import Avg, Count, Exists, OuterRef, FloatField, F, ExpressionWrapper, Q
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils.http import urlencode

from album.models import Album, AlbumTrack
from tracks.models import Track
from ratings.utils import annotate_albums, annotate_tracks
from save_system.models import SavedTrack

SEARCH_LIMIT = 50


def _is_ajax(request) -> bool:
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def index(request):
    """
    Homepage: hero + latest public albums + top 10 albums & tracks by weighted score.
    """

    # ---------------- Latest 12 public albums (for grid) ---------------- #
    public_albums = (
        annotate_albums(
            Album.objects.filter(is_public=True).select_related("owner")
        )
        .annotate(track_count=Count("album_tracks", distinct=True))
        .order_by("-created_at")[:12]
    )

    # ---------------- Top 10 Albums (weighted: avg * count) ---------------- #
    albums_top = (
        annotate_albums(Album.objects.filter(is_public=True))
        .filter(rating_count__gt=0)  # only those with votes
        .annotate(
            rating_score=ExpressionWrapper(
                F("rating_avg") * F("rating_count"),
                output_field=FloatField(),
            )
        )
        .order_by("-rating_score", "-rating_count", "-rating_avg", "-created_at")[:10]
    )

    # ---------------- Top 10 Tracks (must belong to a public album) ---------------- #
    in_public_album = AlbumTrack.objects.filter(
        track_id=OuterRef("pk"), album__is_public=True
    )

    tracks_top = (
        annotate_tracks(Track.objects.filter(Exists(in_public_album)))
        .filter(rating_count__gt=0)
        .annotate(
            rating_score=ExpressionWrapper(
                F("rating_avg") * F("rating_count"),
                output_field=FloatField(),
            )
        )
        .order_by("-rating_score", "-rating_count", "-rating_avg", "-created_at")[:10]
    )

    # ---------------- Mark which tracks are already saved by this user ---------------- #
    if request.user.is_authenticated:
        saved_ids = set(
            SavedTrack.objects.filter(owner=request.user, original_track__in=tracks_top)
            .values_list("original_track_id", flat=True)
        )
        for t in tracks_top:
            t.is_in_my_albums = t.id in saved_ids
    else:
        for t in tracks_top:
            t.is_in_my_albums = False

    return render(
        request,
        "home_page/index.html",
        {
            "public_albums": public_albums,
            "albums_top": albums_top,
            "tracks_top": tracks_top,
        },
    )




def search(request):
    """
    Global search endpoint for AJAX.
    Accepts:
      - q: query string
      - t: scope ('all' | 'albums' | 'tracks' | 'users')
    Returns JSON with rendered HTML fragments.
    """
    if not _is_ajax(request):
        # Keep everything on the home page as requested.
        params = {}
        if request.GET.get("q"):
            params["q"] = request.GET["q"].strip()
        if request.GET.get("t"):
            params["t"] = request.GET["t"].lower()
        return redirect("/" + (f"?{urlencode(params)}" if params else ""))

    q = (request.GET.get("q") or "").strip()
    scope = (request.GET.get("t") or "all").lower()
    User = get_user_model()

    albums = []
    tracks = []
    users = []
    total = 0

    if q:
        if scope in ("all", "albums"):
            albums_qs = annotate_albums(
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
            ).order_by("-created_at")[:SEARCH_LIMIT]
            albums = list(albums_qs)
            total += len(albums)

        if scope in ("all", "tracks"):
            tracks_qs = annotate_tracks(
                Track.objects.filter(track_albums__album__is_public=True)
                .select_related("owner")
                .filter(Q(name__icontains=q) | Q(source_url__icontains=q))
                .distinct()
            ).order_by("-created_at")[:SEARCH_LIMIT]
            tracks = list(tracks_qs)
            total += len(tracks)

        if scope in ("all", "users"):
            users_qs = (
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
                .order_by("-public_album_count", "username")[:SEARCH_LIMIT]
            )
            users = list(users_qs)
            total += len(users)

    context = {
        "q": q,
        "scope": scope,
        "albums": albums,
        "tracks": tracks,
        "users": users,
        "total": total,
    }

    html = {
        "albums": render_to_string(
            "home_page/partials/_search_albums.html", context, request=request
        ),
        "tracks": render_to_string(
            "home_page/partials/_search_tracks.html", context, request=request
        ),
        "users": render_to_string(
            "home_page/partials/_search_users.html", context, request=request
        ),
        "summary": render_to_string(
            "home_page/partials/_search_summary.html", context, request=request
        ),
        "empty": render_to_string(
            "home_page/partials/_search_empty.html", context, request=request
        ),
    }
    return JsonResponse({"q": q, "scope": scope, "total": total, "html": html})
