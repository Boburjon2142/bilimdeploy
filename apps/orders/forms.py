from django import forms
from .models import Order


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            "full_name",
            "phone",
            "extra_phone",
            "location",
            "address",
            "latitude",
            "longitude",
            "maps_link",
            "note",
            "payment_type",
            "delivery_time_choice",
            "delivery_time",
        ]
        labels = {
            "address": "Mo'ljal",
        }
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "F.I.Sh"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "extra_phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "Qo‘shimcha raqam (ixtiyoriy)"}),
            "location": forms.TextInput(attrs={"class": "form-control", "placeholder": "Lokatsiya (shahar/tuman yoki GPS)"}),
            "address": forms.TextInput(attrs={"class": "form-control", "placeholder": "Manzil (masalan: Atlas savdo markazi)"}),
            "latitude": forms.HiddenInput(attrs={"id": "id_latitude"}),
            "longitude": forms.HiddenInput(attrs={"id": "id_longitude"}),
            "maps_link": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Google Maps havolasini kiriting (ixtiyoriy)",
                    "id": "id_maps_link",
                }
            ),
            "note": forms.Textarea(attrs={"rows": 3, "class": "form-control", "placeholder": "Izoh"}),
            "payment_type": forms.Select(attrs={"class": "form-select"}),
            "delivery_time_choice": forms.Select(attrs={"class": "form-select", "id": "delivery-time-choice"}),
            "delivery_time": forms.TimeInput(attrs={"class": "form-control", "type": "time", "id": "delivery-time"}),
        }

    def clean(self):
        cleaned = super().clean()
        lat = cleaned.get("latitude")
        lng = cleaned.get("longitude")
        if (lat and lng) or (lat is None and lng is None):
            pass
        else:
            raise forms.ValidationError("Kenglik va uzunlik birga yuborilishi kerak.")

        if lat is not None:
            if not (-90 <= float(lat) <= 90):
                self.add_error("latitude", "Kenglik noto‘g‘ri.")
        if lng is not None:
            if not (-180 <= float(lng) <= 180):
                self.add_error("longitude", "Uzunlik noto‘g‘ri.")
        choice = cleaned.get("delivery_time_choice")
        time_value = cleaned.get("delivery_time")
        if choice == "schedule" and not time_value:
            self.add_error("delivery_time", "Vaqtni tanlang.")
        return cleaned
