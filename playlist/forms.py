from django import forms
from .models import Playlist

class PlaylistForm(forms.ModelForm):
    class Meta:
        model = Playlist
        fields = ['name', 'description', 'tracks']
        widgets = {
            'tracks': forms.CheckboxSelectMultiple,  # lets you tick tracks to add
        }
