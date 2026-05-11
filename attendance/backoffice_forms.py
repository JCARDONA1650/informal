from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import (
    Project,
    Employee,
    Attendance,
    PayrollPeriod,
    ProjectIncome,
    ProjectExpense,
)

DARK_INPUT = "form-control bg-dark text-light border-danger"
DARK_SELECT = "form-select bg-dark text-light border-danger"
DARK_CHECK = "form-check-input"


class BOProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = "__all__"
        widgets = {
            "name": forms.TextInput(attrs={"class": DARK_INPUT}),
            "slug": forms.TextInput(attrs={"class": DARK_INPUT}),
            "contract_value": forms.NumberInput(attrs={
                "class": DARK_INPUT,
                "step": "0.01",
                "min": "0",
                "inputmode": "decimal",
            }),
            "contract_currency": forms.Select(attrs={"class": DARK_SELECT}),
            "supervisors": forms.SelectMultiple(attrs={"class": DARK_SELECT}),
            "employees": forms.SelectMultiple(attrs={"class": DARK_SELECT}),
            "active": forms.CheckboxInput(attrs={"class": DARK_CHECK}),
        }


class BOEmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = "__all__"
        widgets = {
            "document_id": forms.TextInput(attrs={
                "class": DARK_INPUT,
                "maxlength": "50",
            }),
            "full_name": forms.TextInput(attrs={
                "class": DARK_INPUT,
                "maxlength": "150",
            }),
            "position": forms.TextInput(attrs={
                "class": DARK_INPUT,
                "maxlength": "100",
            }),
            "hourly_rate": forms.NumberInput(attrs={
                "class": DARK_INPUT,
                "step": "0.01",
                "min": "0",
                "inputmode": "decimal",
            }),
            "currency": forms.Select(attrs={"class": DARK_SELECT}),
            "active": forms.CheckboxInput(attrs={"class": DARK_CHECK}),
        }


class BOAttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = "__all__"
        widgets = {
            "project": forms.Select(attrs={"class": DARK_SELECT}),
            "employee": forms.Select(attrs={"class": DARK_SELECT}),
            "date": forms.DateInput(attrs={
                "type": "date",
                "class": DARK_INPUT,
            }),
            "check_in": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "class": DARK_INPUT,
            }),
            "check_out": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "class": DARK_INPUT,
            }),
            "check_in_source": forms.Select(attrs={"class": DARK_SELECT}),
            "check_out_source": forms.Select(attrs={"class": DARK_SELECT}),
            "evidence_photo": forms.ClearableFileInput(attrs={
                "class": DARK_INPUT,
                "accept": "image/*",
            }),
            "notes": forms.TextInput(attrs={
                "class": DARK_INPUT,
                "maxlength": "200",
            }),
            "manual_minutes": forms.NumberInput(attrs={
                "class": DARK_INPUT,
                "min": "0",
                "step": "1",
            }),
            "manual_note": forms.TextInput(attrs={
                "class": DARK_INPUT,
                "maxlength": "200",
            }),
        }


class BOPayrollPeriodForm(forms.ModelForm):
    class Meta:
        model = PayrollPeriod
        fields = "__all__"
        widgets = {
            "start_date": forms.DateInput(attrs={
                "type": "date",
                "class": DARK_INPUT,
            }),
            "end_date": forms.DateInput(attrs={
                "type": "date",
                "class": DARK_INPUT,
            }),
            "project": forms.Select(attrs={"class": DARK_SELECT}),
            "status": forms.Select(attrs={"class": DARK_SELECT}),
            "created_by": forms.Select(attrs={"class": DARK_SELECT}),
            "closed_by": forms.Select(attrs={"class": DARK_SELECT}),
            "closed_at": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "class": DARK_INPUT,
            }),
        }


class BOIncomeForm(forms.ModelForm):
    class Meta:
        model = ProjectIncome
        fields = "__all__"
        widgets = {
            "project": forms.Select(attrs={"class": DARK_SELECT}),
            "date": forms.DateInput(attrs={
                "type": "date",
                "class": DARK_INPUT,
            }),
            "amount": forms.NumberInput(attrs={
                "class": DARK_INPUT,
                "step": "0.01",
                "min": "0",
                "inputmode": "decimal",
            }),
            "currency": forms.Select(attrs={"class": DARK_SELECT}),
            "description": forms.TextInput(attrs={
                "class": DARK_INPUT,
                "maxlength": "200",
            }),
            "created_by": forms.Select(attrs={"class": DARK_SELECT}),
        }


class BOExpenseForm(forms.ModelForm):
    class Meta:
        model = ProjectExpense
        fields = "__all__"
        widgets = {
            "project": forms.Select(attrs={"class": DARK_SELECT}),
            "date": forms.DateInput(attrs={
                "type": "date",
                "class": DARK_INPUT,
            }),
            "category": forms.Select(attrs={"class": DARK_SELECT}),
            "amount": forms.NumberInput(attrs={
                "class": DARK_INPUT,
                "step": "0.01",
                "min": "0",
                "inputmode": "decimal",
            }),
            "currency": forms.Select(attrs={"class": DARK_SELECT}),
            "description": forms.TextInput(attrs={
                "class": DARK_INPUT,
                "maxlength": "200",
            }),
            "created_by": forms.Select(attrs={"class": DARK_SELECT}),
        }

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class BOUserCreateForm(UserCreationForm):
    ROLE_CHOICES = (
        ("admin", "Admin"),
        ("supervisor", "Supervisor"),
    )

    role = forms.ChoiceField(
        label="Rol",
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={"class": DARK_SELECT})
    )

    first_name = forms.CharField(
        label="Nombre",
        required=False,
        widget=forms.TextInput(attrs={"class": DARK_INPUT})
    )

    last_name = forms.CharField(
        label="Apellido",
        required=False,
        widget=forms.TextInput(attrs={"class": DARK_INPUT})
    )

    email = forms.EmailField(
        label="Email",
        required=False,
        widget=forms.EmailInput(attrs={"class": DARK_INPUT})
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "password1",
            "password2",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["username"].widget.attrs.update({"class": DARK_INPUT})
        self.fields["password1"].widget.attrs.update({"class": DARK_INPUT})
        self.fields["password2"].widget.attrs.update({"class": DARK_INPUT})

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data.get("role")

        if role == "admin":
            user.is_superuser = True
            user.is_staff = True
        else:
            user.is_superuser = False
            user.is_staff = False

        if commit:
            user.save()

        return user