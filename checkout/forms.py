# checkout/forms.py
from django import forms
from django_countries import countries
from .models import Order

COUNTRY_CHOICES = [("", "(select country)")] + list(countries)

class OrderForm(forms.ModelForm):
    country = forms.ChoiceField(
        choices=COUNTRY_CHOICES, required=False, widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = Order
        fields = (
            "full_name", "email",
            "phone_number", "country", "postcode", "town_or_city",
            "street_address1", "street_address2", "county",
        )
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "postcode": forms.TextInput(attrs={"class": "form-control"}),
            "town_or_city": forms.TextInput(attrs={"class": "form-control"}),
            "street_address1": forms.TextInput(attrs={"class": "form-control"}),
            "street_address2": forms.TextInput(attrs={"class": "form-control"}),
            "county": forms.TextInput(attrs={"class": "form-control"}),
        }
