from django import forms

from .models import Album


class AlbumForm(forms.ModelForm):
    class Meta:
        model = Album
        fields = ["name", "description"]
        widgets = {
            "tracks": forms.CheckboxSelectMultiple,  # lets you tick tracks to add
        }
