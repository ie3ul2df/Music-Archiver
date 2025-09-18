# ----------------------- tracks/forms.py ----------------------- #
from django import forms

from album.models import Album, AlbumTrack

from .models import Track


class TrackForm(forms.ModelForm):
    # Extra field: choose an album to drop this track into
    album = forms.ModelChoiceField(
        queryset=Album.objects.none(), required=False, label="Add to album"
    )

    class Meta:
        model = Track
        fields = ["name", "audio_file", "source_url"]

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner
        if owner:
            self.fields["album"].queryset = Album.objects.filter(owner=owner).order_by(
                "-created_at"
            )

    def clean_source_url(self):
        url = (self.cleaned_data.get("source_url") or "").strip()
        if url and not (url.startswith("http://") or url.startswith("https://")):
            raise forms.ValidationError("Enter a valid http(s) URL.")
        return url

    def save(self, commit=True):
        track = super().save(commit=False)
        track.owner = self.owner
        if commit:
            track.save()
            chosen_album = self.cleaned_data.get("album")
            if (
                chosen_album
                and not AlbumTrack.objects.filter(
                    album=chosen_album, track=track
                ).exists()
            ):
                last = (
                    AlbumTrack.objects.filter(album=chosen_album)
                    .order_by("-position")
                    .first()
                )
                pos = (last.position if last else 0) + 1
                AlbumTrack.objects.create(album=chosen_album, track=track, position=pos)
        return track
