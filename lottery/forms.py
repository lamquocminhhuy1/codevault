from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Ticket
from .services import SOUTHERN_STATIONS


class SignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)


class TicketForm(forms.ModelForm):
    number = forms.CharField(
        min_length=2,
        max_length=6,
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "pattern": "[0-9]*",
                "placeholder": "123456",
                "autocomplete": "off",
                "id": "id_number",
            }
        ),
    )
    station = forms.ChoiceField(choices=[(s, s) for s in SOUTHERN_STATIONS])

    class Meta:
        model = Ticket
        fields = ["number", "station", "draw_date", "cost"]
        widgets = {
            "draw_date": forms.DateInput(attrs={"type": "date"}),
            "cost": forms.NumberInput(attrs={"step": 1000, "min": 0}),
        }

    def clean_number(self):
        number = self.cleaned_data["number"].strip()
        if not number.isdigit():
            raise forms.ValidationError("Số vé chỉ được gồm chữ số.")
        return number

    def clean_draw_date(self):
        draw_date = self.cleaned_data["draw_date"]
        if draw_date > timezone.localdate():
            raise forms.ValidationError("Không thể chọn ngày trong tương lai.")
        return draw_date
