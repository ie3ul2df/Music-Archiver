# profile_page/forms.py
from django import forms
from django.contrib.auth.models import User
from django_countries import countries

from .models import UserProfile

# Eager, concrete choices list (no lazy iterators)
COUNTRY_CHOICES = [("", "(select country)")] + list(countries)


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
        }


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["profile_image", "bio", "contact_number", "website"]
        widgets = {
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "contact_number": forms.TextInput(attrs={"class": "form-control"}),
            "website": forms.URLInput(attrs={"class": "form-control"}),
        }


class ProfileDefaultDeliveryForm(forms.ModelForm):
    # OVERRIDE the model field with a concrete ChoiceField (avoids lazy choices)
    default_country = forms.ChoiceField(
        choices=COUNTRY_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = UserProfile
        fields = (
            "default_phone_number",
            "default_country",
            "default_postcode",
            "default_town_or_city",
            "default_street_address1",
            "default_street_address2",
            "default_county",
        )
        widgets = {
            "default_phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "default_postcode": forms.TextInput(attrs={"class": "form-control"}),
            "default_town_or_city": forms.TextInput(attrs={"class": "form-control"}),
            "default_street_address1": forms.TextInput(attrs={"class": "form-control"}),
            "default_street_address2": forms.TextInput(attrs={"class": "form-control"}),
            "default_county": forms.TextInput(attrs={"class": "form-control"}),
        }
