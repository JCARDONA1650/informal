# attendance/forms.py

import re
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from .models import (
    Employee,
    PayrollPeriod,
    PayrollLine,
    Project,
    ProjectIncome,
    ProjectExpense,
    ProjectLunchRule,
    CURRENCY_CHOICES,
    SCAN_SOURCE_CHOICES,
)


# ──────────────────────────────────────────────
# Opciones
# ──────────────────────────────────────────────

ACTIONS = (
    ("IN", "Check-In (Ingreso)"),
    ("OUT", "Check-Out (Salida)"),
)

SCAN_METHODS = (
    ("qr", "QR"),
    ("biometric", "Biométrico"),
)


# ──────────────────────────────────────────────
# Helpers de validación
# ──────────────────────────────────────────────

def clean_text_spaces(value):
    return " ".join((value or "").strip().split())


def validate_only_letters(value, field_name="Este campo"):
    value = clean_text_spaces(value)

    if not value:
        raise forms.ValidationError(f"{field_name} es obligatorio.")

    if re.search(r"\d", value):
        raise forms.ValidationError(f"{field_name} no puede contener números.")

    if not re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+", value):
        raise forms.ValidationError(f"{field_name} solo puede contener letras y espacios.")

    return value


def validate_money_positive(value, field_name="Valor"):
    if value is None:
        raise forms.ValidationError(f"{field_name} es obligatorio.")

    if value < Decimal("0.00"):
        raise forms.ValidationError(f"{field_name} no puede ser negativo.")

    if value > Decimal("999999999999.99"):
        raise forms.ValidationError(f"{field_name} es demasiado alto.")

    return value


# ──────────────────────────────────────────────
# Scan QR / Biométrico
# ──────────────────────────────────────────────

class ScanForm(forms.Form):
    employee = forms.ModelChoiceField(
        label="Empleado",
        queryset=Employee.objects.none(),
        empty_label="Seleccione empleado",
        widget=forms.Select(attrs={
            "class": "form-select bg-dark text-light border-danger"
        })
    )

    action = forms.ChoiceField(
        label="Acción",
        choices=ACTIONS,
        widget=forms.Select(attrs={
            "class": "form-select bg-dark text-light border-danger"
        })
    )

    source = forms.ChoiceField(
        label="Método de registro",
        choices=SCAN_METHODS,
        required=False,
        initial="qr",
        widget=forms.Select(attrs={
            "class": "form-select bg-dark text-light border-danger"
        })
    )

    evidence_photo = forms.ImageField(
        label="Tomar foto",
        required=True,
        widget=forms.ClearableFileInput(attrs={
            "class": "form-control bg-dark text-light border-danger",
            "accept": "image/*",
            "capture": "environment",
        })
    )

    client_uuid = forms.CharField(
        required=False,
        max_length=64,
        widget=forms.HiddenInput()
    )

    device_ts = forms.CharField(
        required=False,
        max_length=40,
        widget=forms.HiddenInput()
    )

    verification_reference = forms.CharField(
        required=False,
        max_length=120,
        widget=forms.HiddenInput()
    )

    device_name = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.HiddenInput()
    )

    def __init__(self, *args, **kwargs):
        project = kwargs.pop("project", None)
        super().__init__(*args, **kwargs)

        if project and project.employees.exists():
            self.fields["employee"].queryset = (
                project.employees.filter(active=True).order_by("full_name")
            )
        else:
            self.fields["employee"].queryset = (
                Employee.objects.filter(active=True).order_by("full_name")
            )

    def clean_evidence_photo(self):
        photo = self.cleaned_data.get("evidence_photo")

        if not photo:
            raise forms.ValidationError("Debes tomar o adjuntar una foto.")

        allowed = {"image/jpeg", "image/png", "image/webp"}

        if hasattr(photo, "content_type") and photo.content_type not in allowed:
            raise forms.ValidationError("Formato no permitido. Usa JPG, PNG o WEBP.")

        if photo.size > 6 * 1024 * 1024:
            raise forms.ValidationError("La foto no puede superar 6 MB.")

        return photo

    def clean_source(self):
        source = self.cleaned_data.get("source") or "qr"

        if source not in ["qr", "biometric"]:
            raise forms.ValidationError("Método de registro inválido.")

        return source


# ──────────────────────────────────────────────
# Empleados
# ──────────────────────────────────────────────

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            "document_id",
            "full_name",
            "position",
            "hourly_rate",
            "currency",
            "active",
        ]

        widgets = {
            "document_id": forms.TextInput(attrs={
                "class": "form-control bg-dark text-light border-danger",
                "placeholder": "Documento / ID del empleado",
                "maxlength": "50",
                "autocomplete": "off",
                "pattern": r"[A-Za-z0-9\-\.]+",
                "title": "Solo letras, números, guiones o puntos.",
            }),
            "full_name": forms.TextInput(attrs={
                "class": "form-control bg-dark text-light border-danger",
                "placeholder": "Nombre completo",
                "maxlength": "150",
                "autocomplete": "off",
                "pattern": r"[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+",
                "title": "El nombre solo debe contener letras y espacios.",
            }),
            "position": forms.TextInput(attrs={
                "class": "form-control bg-dark text-light border-danger",
                "placeholder": "Cargo",
                "maxlength": "100",
            }),
            "hourly_rate": forms.NumberInput(attrs={
                "class": "form-control bg-dark text-light border-danger",
                "placeholder": "0.00",
                "min": "0",
                "step": "0.01",
                "inputmode": "decimal",
            }),
            "currency": forms.Select(attrs={
                "class": "form-select bg-dark text-light border-danger",
            }),
            "active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }

    def clean_document_id(self):
        document_id = clean_text_spaces(self.cleaned_data.get("document_id"))

        if not document_id:
            return None

        document_id = document_id.upper()

        if not re.fullmatch(r"[A-Za-z0-9\-\.]+", document_id):
            raise forms.ValidationError("El documento solo puede tener letras, números, guiones o puntos.")

        qs = Employee.objects.filter(document_id=document_id)

        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Ya existe un empleado registrado con este documento.")

        return document_id

    def clean_full_name(self):
        full_name = self.cleaned_data.get("full_name")
        full_name = validate_only_letters(full_name, "El nombre")

        if len(full_name) < 3:
            raise forms.ValidationError("El nombre debe tener mínimo 3 caracteres.")

        return full_name

    def clean_position(self):
        position = clean_text_spaces(self.cleaned_data.get("position"))

        if not position:
            return ""

        if re.search(r"\d", position):
            raise forms.ValidationError("El cargo no debe contener números.")

        if not re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñ\s\/\-\.]+", position):
            raise forms.ValidationError("El cargo contiene caracteres no permitidos.")

        return position

    def clean_hourly_rate(self):
        hourly_rate = self.cleaned_data.get("hourly_rate")
        return validate_money_positive(hourly_rate, "La tarifa por hora")


# ──────────────────────────────────────────────
# Reglas de almuerzo por proyecto
# ──────────────────────────────────────────────

class ProjectLunchRuleForm(forms.ModelForm):
    class Meta:
        model = ProjectLunchRule
        fields = ["project", "weekday", "start_time", "end_time", "active"]

        widgets = {
            "project": forms.Select(attrs={
                "class": "form-select bg-dark text-light border-danger",
            }),
            "weekday": forms.Select(attrs={
                "class": "form-select bg-dark text-light border-danger",
            }),
            "start_time": forms.TimeInput(attrs={
                "type": "time",
                "class": "form-control bg-dark text-light border-danger",
            }),
            "end_time": forms.TimeInput(attrs={
                "type": "time",
                "class": "form-control bg-dark text-light border-danger",
            }),
            "active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].required = False
        self.fields["project"].empty_label = "Global - todos los proyectos"

    def clean(self):
        cleaned = super().clean()
        start_time = cleaned.get("start_time")
        end_time = cleaned.get("end_time")

        if start_time and end_time and end_time <= start_time:
            raise forms.ValidationError("La hora final debe ser mayor que la hora inicial.")

        return cleaned

# ──────────────────────────────────────────────
# Nómina
# ──────────────────────────────────────────────

class PayrollPeriodForm(forms.ModelForm):
    class Meta:
        model = PayrollPeriod
        fields = ["start_date", "end_date", "project"]

        widgets = {
            "start_date": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control bg-dark text-light border-danger",
            }),
            "end_date": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control bg-dark text-light border-danger",
            }),
            "project": forms.Select(attrs={
                "class": "form-select bg-dark text-light border-danger",
            }),
        }

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get("start_date")
        end_date = cleaned.get("end_date")

        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("La fecha final no puede ser menor que la fecha inicial.")

        return cleaned


class PayrollLineAdjustmentForm(forms.ModelForm):
    class Meta:
        model = PayrollLine
        fields = ["adjustment", "notes"]

        widgets = {
            "adjustment": forms.NumberInput(attrs={
                "class": "form-control bg-dark text-light border-danger",
                "step": "0.01",
                "inputmode": "decimal",
            }),
            "notes": forms.TextInput(attrs={
                "class": "form-control bg-dark text-light border-danger",
                "maxlength": "200",
                "placeholder": "Motivo del ajuste",
            }),
        }

    def clean_adjustment(self):
        adjustment = self.cleaned_data.get("adjustment")

        if adjustment is None:
            return Decimal("0.00")

        if adjustment > Decimal("999999999999.99") or adjustment < Decimal("-999999999999.99"):
            raise forms.ValidationError("El ajuste ingresado es demasiado alto.")

        return adjustment


# ──────────────────────────────────────────────
# Exportar nómina
# ──────────────────────────────────────────────

class PayrollExportForm(forms.Form):
    SCOPE_CHOICES = (
        ("quincena", "Quincena"),
        ("mes", "Mes"),
        ("anio", "Año"),
    )

    scope = forms.ChoiceField(
        label="Ámbito",
        choices=SCOPE_CHOICES,
        widget=forms.Select(attrs={
            "class": "form-select bg-dark text-light border-danger",
        })
    )

    project = forms.ModelChoiceField(
        label="Proyecto",
        queryset=Project.objects.all(),
        required=False,
        empty_label="Todos los proyectos",
        widget=forms.Select(attrs={
            "class": "form-select bg-dark text-light border-danger",
        })
    )

    month = forms.DateField(
        label="Mes",
        required=False,
        widget=forms.DateInput(attrs={
            "type": "month",
            "class": "form-control bg-dark text-light border-danger",
        })
    )

    year = forms.IntegerField(
        label="Año",
        required=False,
        min_value=2020,
        max_value=2100,
        widget=forms.NumberInput(attrs={
            "class": "form-control bg-dark text-light border-danger",
            "min": "2020",
            "max": "2100",
            "step": "1",
        })
    )

    half = forms.ChoiceField(
        label="Quincena",
        required=False,
        choices=(("", "Seleccione"), ("1", "Primera"), ("2", "Segunda")),
        widget=forms.Select(attrs={
            "class": "form-select bg-dark text-light border-danger",
        })
    )


# ──────────────────────────────────────────────
# Finanzas de Proyecto
# ──────────────────────────────────────────────

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "name",
            "contract_value",
            "contract_currency",
            "supervisors",
            "employees",
            "active",
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control bg-dark text-light border-danger",
                "placeholder": "Nombre del proyecto",
                "maxlength": "120",
            }),
            "contract_value": forms.NumberInput(attrs={
                "class": "form-control bg-dark text-light border-danger",
                "step": "0.01",
                "min": "0",
                "inputmode": "decimal",
            }),
            "contract_currency": forms.Select(attrs={
                "class": "form-select bg-dark text-light border-danger",
            }),
            "supervisors": forms.SelectMultiple(attrs={
                "class": "form-select bg-dark text-light border-danger",
            }),
            "employees": forms.SelectMultiple(attrs={
                "class": "form-select bg-dark text-light border-danger",
            }),
            "active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }

    def clean_name(self):
        name = clean_text_spaces(self.cleaned_data.get("name"))

        if not name:
            raise forms.ValidationError("El nombre del proyecto es obligatorio.")

        if len(name) < 3:
            raise forms.ValidationError("El nombre del proyecto debe tener mínimo 3 caracteres.")

        return name

    def clean_contract_value(self):
        contract_value = self.cleaned_data.get("contract_value")
        return validate_money_positive(contract_value, "El valor del contrato")


class IncomeForm(forms.ModelForm):
    class Meta:
        model = ProjectIncome
        fields = [
            "project",
            "date",
            "amount",
            "currency",
            "description",
        ]

        widgets = {
            "project": forms.Select(attrs={
                "class": "form-select bg-dark text-light border-danger",
            }),
            "date": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control bg-dark text-light border-danger",
            }),
            "amount": forms.NumberInput(attrs={
                "class": "form-control bg-dark text-light border-danger",
                "step": "0.01",
                "min": "0",
                "inputmode": "decimal",
            }),
            "currency": forms.Select(attrs={
                "class": "form-select bg-dark text-light border-danger",
            }),
            "description": forms.TextInput(attrs={
                "class": "form-control bg-dark text-light border-danger",
                "maxlength": "200",
                "placeholder": "Descripción del ingreso",
            }),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        return validate_money_positive(amount, "El ingreso")


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = ProjectExpense
        fields = [
            "project",
            "date",
            "category",
            "amount",
            "currency",
            "description",
        ]

        widgets = {
            "project": forms.Select(attrs={
                "class": "form-select bg-dark text-light border-danger",
            }),
            "date": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control bg-dark text-light border-danger",
            }),
            "category": forms.Select(attrs={
                "class": "form-select bg-dark text-light border-danger",
            }),
            "amount": forms.NumberInput(attrs={
                "class": "form-control bg-dark text-light border-danger",
                "step": "0.01",
                "min": "0",
                "inputmode": "decimal",
            }),
            "currency": forms.Select(attrs={
                "class": "form-select bg-dark text-light border-danger",
            }),
            "description": forms.TextInput(attrs={
                "class": "form-control bg-dark text-light border-danger",
                "maxlength": "200",
                "placeholder": "Descripción del gasto",
            }),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        return validate_money_positive(amount, "El gasto")
    
    