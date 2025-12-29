import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import LibraryBook

def normalize_phone(value: str) -> str:
    value = value.strip()
    return re.sub(r"[\s\-()]", "", value)


class PhoneUserCreationForm(UserCreationForm):
    full_name = forms.CharField(
        label="Ism F.I.O.",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ism va familiya"}),
    )
    phone = forms.CharField(
        label="Telefon",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "+998 90 123 45 67"}),
    )

    class Meta:
        model = User
        fields = ("full_name", "phone", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update({"class": "form-control", "placeholder": "Parol"})
        self.fields["password2"].widget.attrs.update({"class": "form-control", "placeholder": "Parolni tasdiqlang"})

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data.get("phone", ""))
        if len(phone) < 7:
            raise forms.ValidationError("Telefon raqam noto‘g‘ri.")
        if User.objects.filter(username=phone).exists():
            raise forms.ValidationError("Bu telefon raqam bilan akkaunt mavjud.")
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["phone"]
        user.first_name = self.cleaned_data.get("full_name", "").strip()
        if commit:
            user.save()
        return user


class PhoneAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Telefon",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "+998 90 123 45 67"}),
    )
    password = forms.CharField(
        label="Parol",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Parol"}),
    )

    def clean_username(self):
        username = self.cleaned_data.get("username", "")
        return normalize_phone(username)


class LibraryBookForm(forms.ModelForm):
    class Meta:
        model = LibraryBook
        fields = ("title", "author", "status")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Kitob nomi"}),
            "author": forms.TextInput(attrs={"class": "form-control", "placeholder": "Muallif"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def clean_title(self):
        title = (self.cleaned_data.get("title") or "").strip()
        if not title:
            raise forms.ValidationError("Kitob nomini kiriting.")
        return title

    def clean_author(self):
        author = (self.cleaned_data.get("author") or "").strip()
        if not author:
            raise forms.ValidationError("Muallifni kiriting.")
        return author
