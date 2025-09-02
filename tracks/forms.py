# tracks/forms.py
from django import forms
from .models import Track
from album.models import Album
from plans.utils import user_has_storage_plan

class TrackForm(forms.ModelForm):
    class Meta:
        model = Track
        fields = ["name", "source_url", "audio_file", "album"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            # Album dropdown only if they have albums; otherwise we’ll auto-assign Default.
            albums = Album.objects.filter(user=user)
            if albums.exists():
                self.fields["album"].queryset = albums
            else:
                self.fields.pop("album")

            # Only show upload if user has a storage plan
            if not user_has_storage_plan(user):
                self.fields.pop("audio_file")

    def clean(self):
        data = super().clean()
        # Must provide either a link or a file (if file field exists)
        has_file = "audio_file" in self.fields and data.get("audio_file")
        has_link = bool(data.get("source_url"))
        if not has_file and not has_link:
            raise forms.ValidationError("Provide a link or upload an audio file.")
        if has_file and has_link:
            raise forms.ValidationError("Choose either a link or an upload, not both.")
        return data
