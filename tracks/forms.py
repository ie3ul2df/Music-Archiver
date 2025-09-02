from django import forms
from .models import Track

class TrackForm(forms.ModelForm):
    class Meta:
        model = Track
        fields = ["name", "source_url", "audio_file"]

    def clean(self):
        data = super().clean()
        if not data.get("source_url") and not data.get("audio_file"):
            raise forms.ValidationError("Provide a link OR upload a file.")
        if data.get("source_url") and data.get("audio_file"):
            raise forms.ValidationError("Choose either a link or an upload, not both.")
        return data
