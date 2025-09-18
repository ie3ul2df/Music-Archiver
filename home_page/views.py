# //--------------------------- home_page/views.py ---------------------------//
from django.contrib.auth import get_user_model
from django.db.models import (Avg, BooleanField, Count, Exists,
                              ExpressionWrapper, F, FloatField, OuterRef,
                              Prefetch, Q, Value)
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string

from album.models import Album, AlbumTrack
from playlist.models import Playlist, PlaylistItem
from ratings.utils import annotate_albums, annotate_tracks
from tracks.models import Favorite, Track
from tracks.utils import annotate_is_in_my_albums

SEARCH_LIMIT = 50


def _is_ajax(request) -> bool:
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def index(request):
    """
    Homepage: hero + latest public albums + top 10 albums & tracks by weighted score.
    """

    # ---------------- Latest 10 public albums (for grid) ---------------- #
    public_albums = (
        annotate_albums(Album.objects.filter(is_public=True).select_related("owner"))
        .annotate(track_count=Count("album_tracks", distinct=True))
        .order_by("-created_at")[:10]
    )
    # NOTE: If you ever render track lists inside `_album_card.html` for this grid too,
    # you can hydrate `public_albums` exactly like `albums_top` (same Prefetch block).

    # ---------------- Top 10 Albums (weighted: avg * count) ---------------- #
    albums_top_qs = (
        annotate_albums(Album.objects.filter(is_public=True).select_related("owner"))
        .filter(rating_count__gt=0)  # only those with votes
        .annotate(
            rating_score=ExpressionWrapper(
                F("rating_avg") * F("rating_count"),
                output_field=FloatField(),
            )
        )
        .order_by("-rating_score", "-rating_count", "-rating_avg", "-created_at")[:10]
    )

    # Prefetch album_tracks with the per-track flags needed by _track_card.html
    # - at.is_favorited (Exists subquery against tracks.Favorite)
    # - at.track_avg / at.track_count (per-track rating aggregates)
    if request.user.is_authenticated:
        fav_subq = Favorite.objects.filter(
            owner=request.user, track=OuterRef("track_id")
        )
        items_qs = (
            AlbumTrack.objects.select_related("track", "track__owner")
            .annotate(
                is_favorited=Exists(fav_subq),
                track_avg=Avg("track__ratings__stars"),
                track_count=Count("track__ratings", distinct=True),
            )
            .order_by("position", "id")
        )
    else:
        items_qs = (
            AlbumTrack.objects.select_related("track", "track__owner")
            .annotate(
                is_favorited=Value(False, output_field=BooleanField()),
                track_avg=Avg("track__ratings__stars"),
                track_count=Count("track__ratings", distinct=True),
            )
            .order_by("position", "id")
        )

    albums_top_qs = albums_top_qs.prefetch_related(
        Prefetch("album_tracks", queryset=items_qs)
    )

    # Evaluate so we can attach per-user flags like playlist and "in my albums"
    albums_top = list(albums_top_qs)

    # Build playlist membership set once (✓/➕ state)
    in_playlist_ids = set()
    if request.user.is_authenticated:
        pl = Playlist.objects.filter(owner=request.user, name="My Playlist").first()
        if pl:
            in_playlist_ids = set(
                PlaylistItem.objects.filter(playlist=pl).values_list(
                    "track_id", flat=True
                )
            )

    # Attach:
    #  - at.track.in_playlist   (for ✓/➕ button)
    #  - at.track.is_in_my_albums (🗃 vs 💾) via your helper
    for alb in albums_top:
        ats = list(alb.album_tracks.all())
        annotate_is_in_my_albums(ats, request.user, attr="track")
        for at in ats:
            at.track.in_playlist = at.track.id in in_playlist_ids

    # ---------------- Top 10 Tracks (must belong to a public album) ---------------- #
    in_public_album = AlbumTrack.objects.filter(
        track_id=OuterRef("pk"), album__is_public=True
    )

    tracks_top_qs = (
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

    # Evaluate so we can attach per-user flags
    tracks_top = list(tracks_top_qs)

    # ------- Favourites flag for current user
    # (sets .is_favorited on each track) -------
    if request.user.is_authenticated and tracks_top:
        fav_ids = set(
            Favorite.objects.filter(
                owner=request.user, track_id__in=[t.id for t in tracks_top]
            ).values_list("track_id", flat=True)
        )
        for t in tracks_top:
            t.is_favorited = t.id in fav_ids
    else:
        for t in tracks_top:
            t.is_favorited = False

    # ------- 💾/🗃️ flag (is_in_my_albums) via your existing helper -------
    annotate_is_in_my_albums(tracks_top, request.user)

    return render(
        request,
        "home_page/index.html",
        {
            "public_albums": public_albums,
            "albums_top": albums_top,  # hydrated albums with track-level flags
            "tracks_top": tracks_top,
        },
    )


def search(request):
    """
    Global search endpoint: returns JSON for AJAX, or renders a full page when not AJAX.
    Accepts:
      - q: query string
      - t: scope ('all' | 'albums' | 'tracks' | 'users')
    """
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

    if _is_ajax(request):
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

    # Non-AJAX fallback → render full results page
    return render(request, "home_page/search.html", context)
