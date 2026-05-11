# attendance/backoffice_views.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth import get_user_model
from .backoffice_forms import BOUserCreateForm
User = get_user_model()

from .models import (
    Project,
    Employee,
    Attendance,
    PayrollPeriod,
    ProjectIncome,
    ProjectExpense,
    ProjectLunchRule,
)

from .backoffice_forms import (
    BOProjectForm,
    BOEmployeeForm,
    BOAttendanceForm,
    BOPayrollPeriodForm,
    BOIncomeForm,
    BOExpenseForm,
)

from .forms import ProjectLunchRuleForm


# ──────────────────────────────────────────────
# Seguridad
# ──────────────────────────────────────────────

def is_admin_user(user):
    return user.is_authenticated and user.is_superuser

# ──────────────────────────────────────────────
# Helpers Backoffice
# ──────────────────────────────────────────────

def backoffice_list(
    request,
    model,
    template_name,
    context_name="items",
    search_fields=None,
    extra_context=None,
    per_page=25,
):
    qs = model.objects.all().order_by("-id")
    q = request.GET.get("q", "").strip()

    if q and search_fields:
        query = Q()
        for field in search_fields:
            query |= Q(**{f"{field}__icontains": q})
        qs = qs.filter(query)

    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        context_name: page_obj.object_list,
        "page_obj": page_obj,
        "q": q,
    }

    if extra_context:
        context.update(extra_context)

    return render(request, template_name, context)


def backoffice_form(request, form_class, template_name, title, instance=None, success_url=None):
    if request.method == "POST":
        form = form_class(request.POST, instance=instance)

        if form.is_valid():
            form.save()
            messages.success(request, f"{title} guardado correctamente.")
            return redirect(success_url)

        messages.error(request, "No se pudo guardar. Revisa los campos.")
    else:
        form = form_class(instance=instance)

    return render(request, template_name, {
        "form": form,
        "title": title,
        "obj": instance,
    })


# ──────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────

@login_required
@user_passes_test(is_admin_user)
def backoffice_dashboard(request):
    context = {
        "projects_count": Project.objects.count(),
        "employees_count": Employee.objects.count(),
        "attendance_count": Attendance.objects.count(),
        "payroll_count": PayrollPeriod.objects.count(),
        "income_count": ProjectIncome.objects.count(),
        "expense_count": ProjectExpense.objects.count(),
        "lunch_rules_count": ProjectLunchRule.objects.count(),
    }

    return render(request, "backoffice/dashboard.html", context)


# ──────────────────────────────────────────────
# Projects
# ──────────────────────────────────────────────

@login_required
@user_passes_test(is_admin_user)
def bo_project_list(request):
    return backoffice_list(
        request,
        model=Project,
        template_name="backoffice/project_list.html",
        search_fields=["name", "slug"],
        extra_context={"title": "Proyectos"},
    )


@login_required
@user_passes_test(is_admin_user)
def bo_project_create(request):
    return backoffice_form(
        request,
        form_class=BOProjectForm,
        template_name="backoffice/form.html",
        title="Nuevo Proyecto",
        success_url="bo_project_list",
    )


@login_required
@user_passes_test(is_admin_user)
def bo_project_edit(request, pk):
    obj = get_object_or_404(Project, pk=pk)

    return backoffice_form(
        request,
        form_class=BOProjectForm,
        template_name="backoffice/form.html",
        title="Editar Proyecto",
        instance=obj,
        success_url="bo_project_list",
    )


@login_required
@user_passes_test(is_admin_user)
def bo_project_delete(request, pk):
    obj = get_object_or_404(Project, pk=pk)

    if request.method == "POST":
        obj.delete()
        messages.success(request, "Proyecto eliminado correctamente.")
        return redirect("bo_project_list")

    return render(request, "backoffice/confirm_delete.html", {
        "obj": obj,
        "title": "Eliminar Proyecto",
        "cancel_url": "bo_project_list",
    })


# ──────────────────────────────────────────────
# Employees
# ──────────────────────────────────────────────

@login_required
@user_passes_test(is_admin_user)
def bo_employee_list(request):
    return backoffice_list(
        request,
        model=Employee,
        template_name="backoffice/employee_list.html",
        search_fields=["full_name", "position", "document_id"],
        extra_context={"title": "Empleados"},
    )


@login_required
@user_passes_test(is_admin_user)
def bo_employee_create(request):
    return backoffice_form(
        request,
        form_class=BOEmployeeForm,
        template_name="backoffice/form.html",
        title="Nuevo Empleado",
        success_url="bo_employee_list",
    )


@login_required
@user_passes_test(is_admin_user)
def bo_employee_edit(request, pk):
    obj = get_object_or_404(Employee, pk=pk)

    return backoffice_form(
        request,
        form_class=BOEmployeeForm,
        template_name="backoffice/form.html",
        title="Editar Empleado",
        instance=obj,
        success_url="bo_employee_list",
    )


@login_required
@user_passes_test(is_admin_user)
def bo_employee_delete(request, pk):
    obj = get_object_or_404(Employee, pk=pk)

    if request.method == "POST":
        obj.delete()
        messages.success(request, "Empleado eliminado correctamente.")
        return redirect("bo_employee_list")

    return render(request, "backoffice/confirm_delete.html", {
        "obj": obj,
        "title": "Eliminar Empleado",
        "cancel_url": "bo_employee_list",
    })


# ──────────────────────────────────────────────
# Attendance
# ──────────────────────────────────────────────

@login_required
@user_passes_test(is_admin_user)
def bo_attendance_list(request):
    return backoffice_list(
        request,
        model=Attendance,
        template_name="backoffice/attendance_list.html",
        search_fields=[
            "employee__full_name",
            "employee__document_id",
            "project__name",
            "notes",
        ],
        extra_context={"title": "Asistencias"},
    )


@login_required
@user_passes_test(is_admin_user)
def bo_attendance_create(request):
    return backoffice_form(
        request,
        form_class=BOAttendanceForm,
        template_name="backoffice/form.html",
        title="Nueva Asistencia",
        success_url="bo_attendance_list",
    )


@login_required
@user_passes_test(is_admin_user)
def bo_attendance_edit(request, pk):
    obj = get_object_or_404(Attendance, pk=pk)

    return backoffice_form(
        request,
        form_class=BOAttendanceForm,
        template_name="backoffice/form.html",
        title="Editar Asistencia",
        instance=obj,
        success_url="bo_attendance_list",
    )


@login_required
@user_passes_test(is_admin_user)
def bo_attendance_delete(request, pk):
    obj = get_object_or_404(Attendance, pk=pk)

    if request.method == "POST":
        obj.delete()
        messages.success(request, "Asistencia eliminada correctamente.")
        return redirect("bo_attendance_list")

    return render(request, "backoffice/confirm_delete.html", {
        "obj": obj,
        "title": "Eliminar Asistencia",
        "cancel_url": "bo_attendance_list",
    })


# ──────────────────────────────────────────────
# Payroll
# ──────────────────────────────────────────────

@login_required
@user_passes_test(is_admin_user)
def bo_payroll_list(request):
    return backoffice_list(
        request,
        model=PayrollPeriod,
        template_name="backoffice/payroll_list.html",
        search_fields=["project__name", "status"],
        extra_context={"title": "Nómina"},
    )


@login_required
@user_passes_test(is_admin_user)
def bo_payroll_create(request):
    return backoffice_form(
        request,
        form_class=BOPayrollPeriodForm,
        template_name="backoffice/form.html",
        title="Nuevo Período de Nómina",
        success_url="bo_payroll_list",
    )


@login_required
@user_passes_test(is_admin_user)
def bo_payroll_edit(request, pk):
    obj = get_object_or_404(PayrollPeriod, pk=pk)

    return backoffice_form(
        request,
        form_class=BOPayrollPeriodForm,
        template_name="backoffice/form.html",
        title="Editar Período de Nómina",
        instance=obj,
        success_url="bo_payroll_list",
    )


@login_required
@user_passes_test(is_admin_user)
def bo_payroll_delete(request, pk):
    obj = get_object_or_404(PayrollPeriod, pk=pk)

    if request.method == "POST":
        obj.delete()
        messages.success(request, "Período de nómina eliminado correctamente.")
        return redirect("bo_payroll_list")

    return render(request, "backoffice/confirm_delete.html", {
        "obj": obj,
        "title": "Eliminar Período de Nómina",
        "cancel_url": "bo_payroll_list",
    })


# ──────────────────────────────────────────────
# Incomes
# ──────────────────────────────────────────────

@login_required
@user_passes_test(is_admin_user)
def bo_income_list(request):
    return backoffice_list(
        request,
        model=ProjectIncome,
        template_name="backoffice/income_list.html",
        search_fields=["project__name", "description", "currency"],
        extra_context={"title": "Ingresos"},
    )


@login_required
@user_passes_test(is_admin_user)
def bo_income_create(request):
    return backoffice_form(
        request,
        form_class=BOIncomeForm,
        template_name="backoffice/form.html",
        title="Nuevo Ingreso",
        success_url="bo_income_list",
    )


@login_required
@user_passes_test(is_admin_user)
def bo_income_edit(request, pk):
    obj = get_object_or_404(ProjectIncome, pk=pk)

    return backoffice_form(
        request,
        form_class=BOIncomeForm,
        template_name="backoffice/form.html",
        title="Editar Ingreso",
        instance=obj,
        success_url="bo_income_list",
    )


@login_required
@user_passes_test(is_admin_user)
def bo_income_delete(request, pk):
    obj = get_object_or_404(ProjectIncome, pk=pk)

    if request.method == "POST":
        obj.delete()
        messages.success(request, "Ingreso eliminado correctamente.")
        return redirect("bo_income_list")

    return render(request, "backoffice/confirm_delete.html", {
        "obj": obj,
        "title": "Eliminar Ingreso",
        "cancel_url": "bo_income_list",
    })


# ──────────────────────────────────────────────
# Expenses
# ──────────────────────────────────────────────

@login_required
@user_passes_test(is_admin_user)
def bo_expense_list(request):
    return backoffice_list(
        request,
        model=ProjectExpense,
        template_name="backoffice/expense_list.html",
        search_fields=["project__name", "description", "category", "currency"],
        extra_context={"title": "Gastos"},
    )


@login_required
@user_passes_test(is_admin_user)
def bo_expense_create(request):
    return backoffice_form(
        request,
        form_class=BOExpenseForm,
        template_name="backoffice/form.html",
        title="Nuevo Gasto",
        success_url="bo_expense_list",
    )


@login_required
@user_passes_test(is_admin_user)
def bo_expense_edit(request, pk):
    obj = get_object_or_404(ProjectExpense, pk=pk)

    return backoffice_form(
        request,
        form_class=BOExpenseForm,
        template_name="backoffice/form.html",
        title="Editar Gasto",
        instance=obj,
        success_url="bo_expense_list",
    )


@login_required
@user_passes_test(is_admin_user)
def bo_expense_delete(request, pk):
    obj = get_object_or_404(ProjectExpense, pk=pk)

    if request.method == "POST":
        obj.delete()
        messages.success(request, "Gasto eliminado correctamente.")
        return redirect("bo_expense_list")

    return render(request, "backoffice/confirm_delete.html", {
        "obj": obj,
        "title": "Eliminar Gasto",
        "cancel_url": "bo_expense_list",
    })


# ──────────────────────────────────────────────
# Lunch Rules
# ──────────────────────────────────────────────

@login_required
@user_passes_test(is_admin_user)
def bo_lunch_rule_list(request):
    q_project = (request.GET.get("project") or "").strip()

    rules = (
        ProjectLunchRule.objects
        .select_related("project")
        .order_by("project__name", "weekday", "start_time")
    )

    if q_project == "global":
        rules = rules.filter(project__isnull=True)
    elif q_project:
        rules = rules.filter(project__slug=q_project)

    paginator = Paginator(rules, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "backoffice/lunch_rule_list.html", {
        "rules": page_obj.object_list,
        "page_obj": page_obj,
        "projects": Project.objects.all().order_by("name"),
        "q_project": q_project,
        "title": "Horario de Almuerzo",
    })


@login_required
@user_passes_test(is_admin_user)
def bo_lunch_rule_create(request):
    if request.method == "POST":
        form = ProjectLunchRuleForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Horario de almuerzo guardado correctamente.")
            return redirect("bo_lunch_rule_list")

        messages.error(request, "No se pudo guardar. Revisa los campos.")
    else:
        form = ProjectLunchRuleForm()

    return render(request, "backoffice/lunch_rule_form.html", {
        "form": form,
        "rule": None,
        "title": "Nuevo Horario de Almuerzo",
    })


@login_required
@user_passes_test(is_admin_user)
def bo_lunch_rule_edit(request, pk):
    rule = get_object_or_404(ProjectLunchRule, pk=pk)

    if request.method == "POST":
        form = ProjectLunchRuleForm(request.POST, instance=rule)

        if form.is_valid():
            form.save()
            messages.success(request, "Horario de almuerzo actualizado correctamente.")
            return redirect("bo_lunch_rule_list")

        messages.error(request, "No se pudo actualizar. Revisa los campos.")
    else:
        form = ProjectLunchRuleForm(instance=rule)

    return render(request, "backoffice/lunch_rule_form.html", {
        "form": form,
        "rule": rule,
        "title": "Editar Horario de Almuerzo",
    })


@login_required
@user_passes_test(is_admin_user)
def bo_lunch_rule_delete(request, pk):
    rule = get_object_or_404(ProjectLunchRule, pk=pk)

    if request.method == "POST":
        rule.delete()
        messages.success(request, "Horario de almuerzo eliminado correctamente.")
        return redirect("bo_lunch_rule_list")

    return render(request, "backoffice/confirm_delete.html", {
        "obj": rule,
        "title": "Eliminar Horario de Almuerzo",
        "cancel_url": "bo_lunch_rule_list",
    })



@login_required
@user_passes_test(is_admin_user)
def bo_user_list(request):
    q = (request.GET.get("q") or "").strip()

    users = User.objects.all().order_by("-id")

    if q:
        users = users.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        )

    paginator = Paginator(users, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "backoffice/user_list.html", {
        "users": page_obj.object_list,
        "page_obj": page_obj,
        "q": q,
        "title": "Usuarios",
    })


@login_required
@user_passes_test(is_admin_user)
def bo_user_create(request):
    if request.method == "POST":
        form = BOUserCreateForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Usuario creado correctamente.")
            return redirect("bo_user_list")

        messages.error(request, "No se pudo crear el usuario. Revisa los campos.")
    else:
        form = BOUserCreateForm()

    return render(request, "backoffice/user_form.html", {
        "form": form,
        "title": "Nuevo Usuario",
    })