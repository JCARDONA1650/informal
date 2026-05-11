# attendance/models.py

from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.text import slugify
import secrets
import uuid

User = get_user_model()


# ──────────────────────────────────────────────────────────────────────────────
# Constantes generales
# ──────────────────────────────────────────────────────────────────────────────

CURRENCY_CHOICES = [
    ("USD", "USD - Dólar"),
    ("COP", "COP - Peso colombiano"),
]

SCAN_SOURCE_CHOICES = [
    ("qr", "QR"),
    ("biometric", "Biométrico"),
    ("manual", "Manual"),
]

SCAN_ACTION_CHOICES = [
    ("in", "Ingreso"),
    ("out", "Salida"),
]

WEEKDAY_CHOICES = [
    (0, "Lunes"),
    (1, "Martes"),
    (2, "Miércoles"),
    (3, "Jueves"),
    (4, "Viernes"),
    (5, "Sábado"),
    (6, "Domingo"),
]

name_validator = RegexValidator(
    regex=r"^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$",
    message="El nombre solo puede contener letras y espacios."
)

document_validator = RegexValidator(
    regex=r"^[A-Za-z0-9\-\.]+$",
    message="El documento solo puede contener letras, números, guiones o puntos."
)


# ──────────────────────────────────────────────────────────────────────────────
# Proyectos
# ──────────────────────────────────────────────────────────────────────────────

class Project(models.Model):
    name = models.CharField("Proyecto", max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)

    supervisors = models.ManyToManyField(
        User,
        related_name="supervised_projects",
        blank=True
    )

    employees = models.ManyToManyField(
        "Employee",
        related_name="projects",
        blank=True
    )

    contract_value = models.DecimalField(
        "Valor del contrato",
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    contract_currency = models.CharField(
        "Moneda del contrato",
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="USD"
    )

    qr_secret = models.CharField(
        max_length=64,
        default=secrets.token_urlsafe,
        editable=False
    )

    active = models.BooleanField("Activo", default=True)

    class Meta:
        ordering = ["name"]

    def clean(self):
        if self.contract_value is not None and self.contract_value < Decimal("0.00"):
            raise ValidationError({
                "contract_value": "El valor del contrato no puede ser negativo."
            })

    def save(self, *args, **kwargs):
        if self.name:
            self.name = " ".join(self.name.strip().split())

        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1

            while Project.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"

            self.slug = slug

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def total_income(self):
        return sum((i.amount for i in self.incomes.all()), start=Decimal("0.00"))

    def total_expense(self):
        return sum((e.amount for e in self.expenses.all()), start=Decimal("0.00"))


# ──────────────────────────────────────────────────────────────────────────────
# Empleados
# ──────────────────────────────────────────────────────────────────────────────

class Employee(models.Model):
    document_id = models.CharField(
        "Documento / ID",
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        validators=[document_validator],
        help_text="Opcional. Puede contener letras, números, guiones o puntos."
    )

    full_name = models.CharField(
        "Nombre completo",
        max_length=150,
        validators=[name_validator]
    )

    position = models.CharField(
        "Cargo",
        max_length=100,
        blank=True
    )

    hourly_rate = models.DecimalField(
        "Tarifa por hora",
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))]
    )

    currency = models.CharField(
        "Moneda",
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="USD"
    )

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name"]

    def clean(self):
        if self.full_name:
            self.full_name = " ".join(self.full_name.strip().split())

        if self.document_id:
            self.document_id = self.document_id.strip().upper()

        if self.hourly_rate is not None and self.hourly_rate < Decimal("0.00"):
            raise ValidationError({
                "hourly_rate": "La tarifa por hora no puede ser negativa."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.document_id:
            return f"{self.full_name} ({self.document_id})"
        return self.full_name


# ──────────────────────────────────────────────────────────────────────────────
# Reglas de almuerzo por proyecto
# ──────────────────────────────────────────────────────────────────────────────
class ProjectLunchRule(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="lunch_rules",
        null=True,
        blank=True,
        verbose_name="Proyecto"
    )

    weekday = models.PositiveSmallIntegerField(
        "Día",
        choices=WEEKDAY_CHOICES
    )

    start_time = models.TimeField("Inicio almuerzo")
    end_time = models.TimeField("Fin almuerzo")

    active = models.BooleanField("Activo", default=True)

    class Meta:
        ordering = ["project__name", "weekday", "start_time"]

    def clean(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({
                "end_time": "La hora final del almuerzo debe ser mayor que la hora inicial."
            })

    @property
    def lunch_minutes(self):
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        return max(0, end_minutes - start_minutes)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        scope = self.project.name if self.project else "GLOBAL"
        return f"{scope} • {self.get_weekday_display()} • {self.start_time} - {self.end_time}"
# ──────────────────────────────────────────────────────────────────────────────
# Asistencia
# ──────────────────────────────────────────────────────────────────────────────

def evidence_upload_path(instance, filename):
    emp_slug = slugify(instance.employee.full_name) or "empleado"
    return f"attendance/{instance.project.slug}/{emp_slug}/{instance.date:%Y/%m/%d}/{filename}"


class Attendance(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        verbose_name="Proyecto"
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        verbose_name="Empleado"
    )

    date = models.DateField(
        "Fecha",
        default=timezone.localdate
    )

    check_in = models.DateTimeField(
        "Hora ingreso",
        blank=True,
        null=True
    )

    check_out = models.DateTimeField(
        "Hora salida",
        blank=True,
        null=True
    )

    check_in_source = models.CharField(
        "Método ingreso",
        max_length=20,
        choices=SCAN_SOURCE_CHOICES,
        default="qr"
    )

    check_out_source = models.CharField(
        "Método salida",
        max_length=20,
        choices=SCAN_SOURCE_CHOICES,
        default="qr"
    )

    evidence_photo = models.ImageField(
        "Foto constancia",
        upload_to=evidence_upload_path,
        blank=True,
        null=True
    )

    notes = models.CharField(
        "Observaciones",
        max_length=200,
        blank=True
    )

    manual_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Override de minutos netos ya revisados."
    )

    manual_note = models.CharField(
        "Motivo ajuste",
        max_length=200,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("project", "employee", "date")
        ordering = ["-date", "project__name", "employee__full_name"]

    def clean(self):
        if self.check_in and self.check_out and self.check_out < self.check_in:
            raise ValidationError({
                "check_out": "La hora de salida no puede ser menor que la hora de ingreso."
            })

    def _round_to_nearest_30(self, minutes: int) -> int:
        minutes = max(0, int(minutes))
        remainder = minutes % 30

        if remainder < 15:
            return minutes - remainder

        return minutes + (30 - remainder)

    def _configured_lunch_minutes(self) -> int:
        if not self.date:
            return 0

        project_rule = ProjectLunchRule.objects.filter(
            project=self.project,
            weekday=self.date.weekday(),
            active=True
        ).first()

        if project_rule:
            return int(project_rule.lunch_minutes)

        global_rule = ProjectLunchRule.objects.filter(
            project__isnull=True,
            weekday=self.date.weekday(),
            active=True
        ).first()

        if global_rule:
            return int(global_rule.lunch_minutes)

        return 0
    def worked_minutes(self) -> int:
        """
        Minutos netos trabajados:
        - Si hay ajuste manual, usa ese valor.
        - Si hay regla de almuerzo configurada para ese proyecto/día, descuenta ese rango.
        - Si no hay regla configurada, mantiene lógica anterior:
          lunes-viernes descuenta 1h si bruto > 5h; sábado no descuenta.
        - Redondea al múltiplo de 30 más cercano.
        """
        if self.manual_minutes is not None:
            return int(self.manual_minutes)

        if not self.check_in or not self.check_out:
            return 0

        gross = int((self.check_out - self.check_in).total_seconds() // 60)
        gross = max(0, gross)

        configured_lunch = self._configured_lunch_minutes()

        if configured_lunch > 0:
            gross -= configured_lunch
        else:
            is_saturday = self.date.weekday() == 5

            if not is_saturday and gross > 300:
                gross -= 60

        net = max(0, gross)

        return self._round_to_nearest_30(net)

    def worked_hhmm(self) -> str:
        minutes = self.worked_minutes()
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.project} • {self.employee} • {self.date} ({self.worked_hhmm()})"


# ──────────────────────────────────────────────────────────────────────────────
# Registro de escaneos QR / Biométrico / Manual
# ──────────────────────────────────────────────────────────────────────────────

class AttendanceScan(models.Model):
    """
    Registro liviano del evento de marcación.
    Sirve para:
    - QR
    - Biométrico
    - Manual
    - Reintentos offline sin duplicar por client_uuid

    Importante:
    No guarda huellas, rostro ni datos biométricos crudos.
    Solo guarda que el método usado fue biométrico.
    """

    client_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    action = models.CharField(
        max_length=10,
        choices=SCAN_ACTION_CHOICES
    )

    device_ts = models.DateTimeField()

    server_ts = models.DateTimeField(auto_now_add=True)

    source = models.CharField(
        max_length=20,
        choices=SCAN_SOURCE_CHOICES,
        default="qr"
    )

    device_name = models.CharField(
        "Dispositivo",
        max_length=100,
        blank=True
    )

    verification_reference = models.CharField(
        "Referencia verificación",
        max_length=120,
        blank=True,
        help_text="Referencia del proveedor biométrico o del dispositivo. No guardar datos biométricos crudos."
    )

    class Meta:
        indexes = [
            models.Index(fields=["employee", "server_ts"]),
            models.Index(fields=["project", "server_ts"]),
            models.Index(fields=["source", "server_ts"]),
        ]
        ordering = ["-server_ts"]

    def clean(self):
        if self.source not in ["qr", "biometric", "manual"]:
            raise ValidationError({
                "source": "Método de marcación inválido."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee} • {self.get_action_display()} • {self.get_source_display()} • {self.device_ts:%Y-%m-%d %H:%M}"


# ──────────────────────────────────────────────────────────────────────────────
# Nómina
# ──────────────────────────────────────────────────────────────────────────────

class PayrollPeriod(models.Model):
    PERIOD_STATUS = (
        ("OPEN", "Abierta"),
        ("CLOSED", "Cerrada"),
    )

    start_date = models.DateField("Inicio")
    end_date = models.DateField("Fin")

    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Proyecto opcional"
    )

    status = models.CharField(
        max_length=10,
        choices=PERIOD_STATUS,
        default="OPEN"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    closed_at = models.DateTimeField(null=True, blank=True)

    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="closed_payroll_periods"
    )

    class Meta:
        ordering = ["-start_date"]
        unique_together = ("start_date", "end_date", "project")

    def clean(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({
                "end_date": "La fecha final no puede ser menor que la fecha inicial."
            })

    @property
    def is_open(self):
        return self.status == "OPEN"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        scope = self.project.name if self.project else "Todos los proyectos"
        return f"{self.start_date} → {self.end_date} • {scope} • {self.status}"


class PayrollLine(models.Model):
    period = models.ForeignKey(
        PayrollPeriod,
        on_delete=models.CASCADE,
        related_name="lines"
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT
    )

    minutes = models.PositiveIntegerField(default=0)

    hourly_rate = models.DecimalField(
        "Tarifa por hora",
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )

    currency = models.CharField(
        "Moneda",
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="USD"
    )

    base_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))]
    )

    adjustment = models.DecimalField(
        "Ajuste (+/-)",
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00")
    )

    notes = models.CharField(
        "Notas ajuste",
        max_length=200,
        blank=True
    )

    class Meta:
        unique_together = ("period", "employee")
        ordering = ["employee__full_name"]

    @property
    def hours_hhmm(self):
        return f"{self.minutes // 60:02d}:{self.minutes % 60:02d}"

    @property
    def total(self):
        return (self.base_amount + self.adjustment).quantize(Decimal("0.01"))

    def clean(self):
        if self.hourly_rate is not None and self.hourly_rate < Decimal("0.00"):
            raise ValidationError({
                "hourly_rate": "La tarifa por hora no puede ser negativa."
            })

        if self.base_amount is not None and self.base_amount < Decimal("0.00"):
            raise ValidationError({
                "base_amount": "El valor base no puede ser negativo."
            })

    def save(self, *args, **kwargs):
        if self.employee_id and not self.currency:
            self.currency = self.employee.currency

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.period} • {self.employee} • {self.hours_hhmm} → {self.currency} {self.total}"


# ──────────────────────────────────────────────────────────────────────────────
# Finanzas del proyecto
# ──────────────────────────────────────────────────────────────────────────────

class ProjectIncome(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="incomes"
    )

    date = models.DateField()

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )

    currency = models.CharField(
        "Moneda",
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="USD"
    )

    description = models.CharField(
        max_length=200,
        blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    class Meta:
        ordering = ["-date", "-id"]

    def clean(self):
        if self.amount is not None and self.amount < Decimal("0.00"):
            raise ValidationError({
                "amount": "El ingreso no puede ser negativo."
            })

    def save(self, *args, **kwargs):
        if self.project_id and not self.currency:
            self.currency = self.project.contract_currency

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.project}] {self.date} • +{self.currency} {self.amount} • {self.description or 'Ingreso'}"


class ProjectExpense(models.Model):
    CATEGORY = [
        ("materials", "Materiales"),
        ("transport", "Transporte"),
        ("meals", "Comida"),
        ("tools", "Herramientas"),
        ("payroll", "Nómina"),
        ("other", "Otros"),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="expenses"
    )

    date = models.DateField()

    category = models.CharField(
        max_length=20,
        choices=CATEGORY,
        default="other"
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )

    currency = models.CharField(
        "Moneda",
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="USD"
    )

    description = models.CharField(
        max_length=200,
        blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    class Meta:
        ordering = ["-date", "-id"]

    def clean(self):
        if self.amount is not None and self.amount < Decimal("0.00"):
            raise ValidationError({
                "amount": "El gasto no puede ser negativo."
            })

    def save(self, *args, **kwargs):
        if self.project_id and not self.currency:
            self.currency = self.project.contract_currency

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.project}] {self.date} • {self.get_category_display()} • -{self.currency} {self.amount}"