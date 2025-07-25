from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.views.decorators.csrf import csrf_exempt
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db.models.functions import TruncDate
from django.utils import timezone
from .models import (
    SupportTicket,
    Item,
    QualityReason,
    C2MaterialItem,
    C2MaterialGroup,
    ScrapEntry,
    WarehouseRequest,
    WarehouseComment,
    WarehouseReason,
    ProductionLog,
    ProductionPlan,
    ProductionComment,
    ProductionOrder,
    Location,
    ScrapCode,
    CycleCountRequest,
    InvRequest,
    InvRequestLine,
    Notification
)
from django.core.paginator import Paginator
from django.utils.dateparse import parse_date
from django.utils.timezone import now, datetime, make_aware
from .forms import ScrapEntry, CycleCountRequestForm, ExcelUploadForm
from django.http import JsonResponse
from datetime import timedelta, datetime
from django.db.models import Sum, F, DecimalField, ExpressionWrapper, Max, Q, Count, Case, When, Value, IntegerField
from django.contrib import messages
import io
import base64
import json
import matplotlib.pyplot as plt
from decimal import Decimal
from django.db import transaction
from . import models


@login_required
def index(request):
    logout(request)  # Wylogowanie użytkownika przy każdym wejściu na stronę główną
    return redirect("login")  # Przekierowanie na stronę logowania

@login_required
def index_view(request):
    """Dynamicznie zmienia wygląd strony index w zależności od roli użytkownika"""
    user = request.user
    # Pobierz nazwy grup, do których należy użytkownik
    group_names = list(user.groups.values_list("name", flat=True))

    # Oblicz zmienne boolean na podstawie przynależności do grup
    is_produkcja = "Produkcja" in group_names
    is_lider = "Lider" in group_names
    is_planista = "Planista" in group_names # Dodaj dla kompletności
    is_manager = "Manager" in group_names   # Dodaj dla kompletności
    is_magazyn = "Magazyn" in group_names   # Dodaj dla kompletności

    # Ustal rolę i szablon do renderowania
    if is_produkcja:
        role = "Produkcja"
        template = "index_production.html"
    elif is_lider:
        role = "Lider"
        template = "index_leader.html"
    elif is_planista: # Użyj zmiennej boolean
        role = "Planista"
        template = "index_planner.html"
    elif is_manager: # Użyj zmiennej boolean
        role = "Manager"
        template = "index_default.html"
    elif is_magazyn: # Użyj zmiennej boolean
        role = "Magazyn"
        template = "index_warehouse.html"
    else:
        role = "Nieznana rola"
        template = "index_default.html"

    # Przekaż wszystkie niezbędne zmienne do kontekstu szablonu
    return render(request, template, {
        "role": role,
        "group_names": group_names,
        "is_produkcja": is_produkcja,
        "is_lider": is_lider,
        "is_planista": is_planista, # Dodano
        "is_manager": is_manager,   # Dodano
        "is_magazyn": is_magazyn,   # Dodano
    })

@login_required
def production_c2(request):
    return render(request, "production_c2.html")

@login_required
def production_rm5(request):
    return render(request, "daily_panel.html")

@login_required
def production_b2b(request):
    return render(request, "daily_panel.html")

@login_required
def production_gaming(request):
    return render(request, "daily_panel.html")

@login_required
def production_scancoin(request):
    return render(request, "daily_panel.html")

@login_required
def production_comestero(request):
    return render(request, "daily_panel.html")

@login_required
def daily_panel(request):
    user = request.user
    group_names = list(user.groups.values_list("name", flat=True))
    is_produkcja = "Produkcja" in group_names
    is_lider = "Lider" in group_names
    is_magazyn = "Magazyn" in group_names

    return render(request, "daily_panel.html", {
        "is_produkcja": is_produkcja,
        "is_lider": is_lider,
        "is_magazyn": is_magazyn,
    })
@login_required
def index_production(request):
    return render(request, "index_production.html")

@login_required
def index_leader(request):
    return render(request, "index_leader.html")

@login_required
def index_planner(request):
    return render(request, "index_planner.html")

@login_required
def index_manager(request):
    return render(request, "index_manager.html")

@login_required
def warehouse_index(request):
    """
    Widok główny dla Panelu Magazynu (index_warehouse.html).
    """
    return render(request, "index_warehouse.html")




TWO_DAYS_AGO = now() - timedelta(days=2)

def register_scrap(request):
    if request.method == "POST":
        item_code = request.POST.get("item_code", "").strip()
        quantity = request.POST.get("quantity", "").strip()
        quality_reason_id = request.POST.get("quality_reason", "").strip()
        create_warehouse_request = request.POST.get("create_warehouse_request") == "on"  # Sprawdzamy, czy checkbox był zaznaczony
        create_quality_request = request.POST.get("create_quality_request") == "on"  # Sprawdzamy, czy checkbox był zaznaczony

        # Sprawdzenie czy item istnieje w bazie
        try:
            item = Item.objects.get(item_code=item_code)
        except Item.DoesNotExist:
            messages.error(request, "❌ Nie znaleziono itemu o podanym numerze. Sprawdź i spróbuj ponownie.")
            return redirect("register_scrap")

        # Sprawdzenie, czy podana ilość jest poprawna
        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            messages.error(request, "⚠️ Podaj poprawną ilość większą od 0.")
            return redirect("register_scrap")

        # Pobranie powodu odpadu
        quality_reason = None
        if quality_reason_id:
            try:
                quality_reason = QualityReason.objects.get(id=quality_reason_id)
            except QualityReason.DoesNotExist:
                messages.error(request, "⚠️ Wybrany powód odpadu nie istnieje.")
                return redirect("register_scrap")

        # Tworzenie wpisu scrapu
        scrap_entry = ScrapEntry.objects.create(
            item=item,
            quantity=quantity,
            cost=item.price * quantity * -1,
            gpg=item.gpg,
            supplier=item.supplier,
            description=item.description,
            production_line=item.production_line,
            reported_by=request.user,
            quality_reason=quality_reason
        )

        # Jeśli checkbox był zaznaczony, tworzymy zgłoszenie WarehouseRequest
        if create_warehouse_request:
            WarehouseRequest.objects.create(
                location=item.production_line,
                created_by=request.user,
                category="return",
                warehouse_reason=None,
                description=f"Automatycznie utworzone ze zgłoszenia odpadu: {item.item_code}",
                item=item,
                quantity=quantity,
                status="new",
            )

        # Jeśli checkbox był zaznaczony, tworzymy zgłoszenie jakości
        if create_quality_request:
            SupportTicket.objects.create(
                category="quality",
                created_by=request.user,
                workplace="Nie dotyczy",
                description=f"Prośba o zweryfikowanie poprawności stocku dla itemu: {item.item_code}",
                status="open",
            )

        messages.success(request, "✅ Zarejestrowano odpad!")
        return redirect("register_scrap_success")

    material_groups = C2MaterialGroup.objects.all()
    quality_reasons = QualityReason.objects.all()
    return render(request, "register_scrap.html", {
        "material_groups": material_groups,
        "quality_reasons": quality_reasons
    })

def get_item_details(request):
    item_code = request.GET.get("item_code")
    try:
        item = Item.objects.get(item_code=item_code)
        data = {
            "description": item.description,
            "gpg": item.gpg,
            "supplier": item.supplier,
            "price": item.price,
            "responsible": item.responsible,
        }
    except Item.DoesNotExist:
        data = {"error": "Nie znaleziono itemu"}

    return JsonResponse(data)

@login_required
def upload_plan(request):
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]
        df = pd.read_excel(file)

        partially_planned_mos = []  # Lista MO, które są częściowo zaplanowane
        ignored_mos = []  # Lista MO, które zostały zignorowane

        for _, row in df.iterrows():
            mo_number = str(row["MO Number"]).strip()
            date = row.get("Planned Date", None)
            planned_week = row.get("Planned Week", None)
            planned_quantity = row.get("Planned Quantity", None)
            planned_percentage = row.get("Planned Percentage", None)

            # Pobierz zlecenie produkcyjne
            production_order = ProductionOrder.objects.filter(mo_number=mo_number).select_related("item").first()
            if not production_order:
                messages.error(request, f"MO {mo_number} nie znaleziono w bazie. Wgraj statusy najpierw!")
                continue

            # Pobierz linię produkcyjną z powiązanego Item
            if production_order.item:
                production_order.production_line = production_order.item.production_line
                production_order.save()

            # Domyślne wartości
            if planned_quantity is None or pd.isna(planned_quantity):  # Sprawdzenie NaN lub None
                planned_quantity = production_order.mo_quantity
            if planned_percentage is None or pd.isna(planned_percentage):  # Sprawdzenie NaN lub None
                planned_percentage = 100.0

            # Walidacja procentu realizacji
            if not (0 <= planned_percentage <= 100):
                messages.error(request, f"Nieprawidłowy procent realizacji dla MO {mo_number}.")
                continue

            # Sprawdź, czy MO jest już w pełni zaplanowane
            total_planned = ProductionPlan.objects.filter(production_order=production_order).aggregate(
                total=Sum("planned_quantity")
            )["total"] or 0

            if total_planned >= production_order.mo_quantity:
                ignored_mos.append(mo_number)
                continue  # Ignoruj MO, które są już w pełni zaplanowane

            # Sprawdź, czy MO jest częściowo zaplanowane
            total_planned += planned_quantity
            if total_planned < production_order.mo_quantity:
                partially_planned_mos.append({
                    "mo_number": mo_number,
                    "remaining_quantity": production_order.mo_quantity - total_planned,
                })

            # Tworzenie przypisania do daty lub tygodnia
            ProductionPlan.objects.create(
                production_order=production_order,
                date=date if pd.notna(date) else None,
                planned_week=planned_week if pd.notna(planned_week) else None,
                planned_quantity=planned_quantity,
                planned_percentage=planned_percentage,
            )

        # Wyświetl komunikaty
        if ignored_mos:
            messages.info(request, f"Ignorowano zaplanowane MO: {', '.join(ignored_mos)}")
        if partially_planned_mos:
            messages.warning(
                request,
                "Niektóre MO są częściowo zaplanowane. Przejdź do edycji, aby zaplanować pozostałe sub-MO."
            )
            return redirect("production_plan")  # Przekierowanie do widoku planu produkcji

        messages.success(request, "Plan produkcji został zapisany.")
        return redirect("upload_plan")

    return render(request, "upload_plan.html")

def upload_status(request):
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]
        df = pd.read_excel(file)

        for _, row in df.iterrows():
            mo_number = str(row["MO Number"]).strip()
            item_code = str(row["Item"]).strip()  # Pobieramy numer Itemu
            mo_quantity = row["MO Quantity"]  # Całkowita ilość MO
            produced_quantity = row["Produced Quantity"]  # Faktycznie wyprodukowane
            status_mo = str(row["MO Status"]).strip()

            # Pobieramy dane z Item, jeśli istnieje
            item = Item.objects.filter(item_code=item_code).first()

            # Tworzymy lub aktualizujemy MO
            production_order, created = ProductionOrder.objects.update_or_create(
                mo_number=mo_number,
                defaults={
                    "mo_quantity": mo_quantity,
                    "produced_quantity": produced_quantity,
                    "status": "completed" if mo_quantity == produced_quantity else "new",
                    "item": item,  # Przypisanie itemu z bazy
                }
            )

            # Ustawiamy datę zakończenia, jeśli zlecenie jest zakończone
            if mo_quantity == produced_quantity:
                production_order.completed_at = now()
                production_order.save()

        messages.success(request, "Statusy zleceń zostały zaktualizowane.")
        return redirect("upload_status")

    return render(request, "upload_status.html")

def get_production_plan_data(request):
    line = request.GET.get("line", "")
    gpg = request.GET.get("gpg", "")
    status = request.GET.get("status", "")

    qs = ProductionPlan.objects.select_related("production_order__item").all()

    if line:
        qs = qs.filter(production_order__production_line=line)
    if gpg:
        qs = qs.filter(production_order__item__gpg=gpg)
    if status:
        qs = qs.filter(production_order__status=status)

    data = [
        {
            "id": plan.id,
            "line": plan.production_order.production_line,
            "gpg": plan.production_order.item.gpg if plan.production_order.item else "",
            "mo_number": plan.production_order.mo_number,
            "item_code": plan.production_order.item.item_code if plan.production_order.item else "",
            "description": plan.production_order.item.description if plan.production_order.item else "",
            "planned_quantity": float(plan.planned_quantity),
            "completed_quantity": float(plan.production_order.produced_quantity),
            "date": plan.date.strftime("%Y-%m-%d") if plan.date else "",
            "status": plan.production_order.status,
        }
        for plan in qs
    ]

    return JsonResponse({"results": data})

@login_required
def production_plan_view(request):
    """
    Widok renderujący stronę z planem produkcji.
    """
    lines = ProductionPlan.objects.values_list("production_order__production_line", flat=True).distinct()
    gpgs = ProductionPlan.objects.values_list("production_order__item__gpg", flat=True).distinct()

    return render(request, "production_plan.html", {
        "lines": lines,
        "gpgs": gpgs,
    })
@login_required
def edit_production_plan(request, plan_id):
    plan = get_object_or_404(ProductionPlan, id=plan_id)

    if request.method == "POST":
        # Pobierz dane z formularza
        new_date = request.POST.get("date")
        new_week = request.POST.get("week")
        new_quantity = request.POST.get("quantity")
        new_percentage = request.POST.get("percentage")

        # Walidacja danych
        if new_date and new_week:
            messages.error(request, "Nie możesz jednocześnie ustawić daty i tygodnia.")
            return redirect("edit_production_plan", plan_id=plan.id)

        if not new_quantity or int(new_quantity) <= 0:
            messages.error(request, "Ilość musi być większa od zera.")
            return redirect("edit_production_plan", plan_id=plan.id)

        # Aktualizacja planu
        plan.date = new_date if new_date else None
        plan.planned_week = new_week if new_week else None
        plan.planned_quantity = int(new_quantity)
        plan.planned_percentage = float(new_percentage)
        plan.save()

        messages.success(request, "Plan został zaktualizowany.")
        return redirect("production_plan")

    return render(request, "edit_plan.html", {"plan": plan})

@login_required
def get_comments(request, order_id):
    """
    Pobiera komentarze dla danego zamówienia produkcyjnego.
    """
    comments = ProductionComment.objects.filter(production_order_id=order_id).values("user__username", "text", "created_at")
    return JsonResponse({"comments": list(comments)})

@login_required
def add_comment(request, plan_id):
    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        if not text:
            return JsonResponse({"success": False, "error": "Komentarz nie może być pusty."})

        # Pobierz plan produkcji
        try:
            plan = ProductionPlan.objects.get(id=plan_id)
        except ProductionPlan.DoesNotExist:
            return JsonResponse({"success": False, "error": "Nie znaleziono planu produkcji."})

        # Dodaj komentarz
        comment = ProductionComment.objects.create(
            production_plan=plan,
            user=request.user,
            text=text
        )

        return JsonResponse({
            "success": True,
            "user": request.user.username,
            "text": comment.text,
            "created_at": comment.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return JsonResponse({"success": False, "error": "Nieprawidłowe żądanie."})

def update_order_status(request, order_id):
    """
    Umożliwia ręczną zmianę statusu ProductionOrder np. in_progress, wip, printed.
    Odbiera 'new_status' z request.POST, np. "printed".
    Zwraca JSON z info o sukcesie.
    """
    if request.method == "POST":
        new_status = request.POST.get("new_status")
        order = get_object_or_404(ProductionOrder, id=order_id)

        # Ograniczamy do dozwolonych statusów:
        allowed_manual_statuses = ["in_progress", "wip", "printed", "stopped"]
        if new_status in allowed_manual_statuses:
            order.status = new_status
            order.save()
            return JsonResponse({"success": True, "status": new_status})
        else:
            return JsonResponse({"success": False, "error": "Niedozwolony status."})
    return JsonResponse({"success": False, "error": "Złe żądanie."}, status=400)

@login_required
def plan_na_dzis(request):
    today = now().date()
    plan_today = ProductionPlan.objects.filter(date=today).order_by("production_line")

    return render(request, "plan_na_dzis.html", {"plan_today": plan_today})

@login_required
def manufacturing_orders_menu(request):
    # Ten widok wyświetla przyciski do:
    # - Wgraj Plan
    # - Wgraj Status
    # - Plan na dziś
    return render(request, 'manufacturing_orders_menu.html')

def logout_success(request):
    return render(request, "logout.html")

@login_required
def call_quality(request):
    if request.method == "POST":
        description = request.POST.get("description", "Brak opisu")
        ticket = SupportTicket.objects.create(
            category="quality",
            created_by=request.user,
            workplace="Nie dotyczy",
            description=description,
            status="open",
        )

         # Tworzenie powiadomień dla grupy Jakości
        quality_group = Group.objects.get(name="Jakość")
        for user in quality_group.user_set.all():
            create_notification(user, f"Nowe zgłoszenie do jakości", url=f"/display_board/quality/")

        messages.success(request, "Zgłoszenie do technika zostało wysłane!")
        return redirect("filtered_display_board", category="quality")

    return render(request, "call_quality.html")

@login_required
def call_technician(request):
    if request.method == "POST":
        description = request.POST.get("description", "Brak opisu")
        ticket = SupportTicket.objects.create(
            category="technician",
            created_by=request.user,
            workplace="Nie dotyczy",
            description=description,
            status="open",
        )

        # Tworzenie powiadomień dla grupy Techników
        technik_group = Group.objects.get(name="Technik")
        for user in technik_group.user_set.all():
            create_notification(user, f"Nowe zgłoszenie do technika od {ticket.created_by}", url=f"/display_board/technician/")

        messages.success(request, "Zgłoszenie do technika zostało wysłane!")
        return redirect("filtered_display_board", category="technician")

    return render(request, "call_technician.html")

@login_required
def call_engineer(request):
    if request.method == "POST":
        description = request.POST.get("description", "Brak opisu")  # Domyślny opis
        ticket = SupportTicket.objects.create(
            category="engineer",
            created_by=request.user,
            workplace="Nie dotyczy",
            description=description,
            status="open",
        )

         # Tworzenie powiadomień dla grupy Inżynierów
        engineer_group = Group.objects.get(name="Inżynier")
        for user in engineer_group.user_set.all():
            create_notification(user, f"Nowe zgłoszenie do inżyniera od {ticket.created_by}", url=f"/display_board/engineer/")

        messages.success(request, "Zgłoszenie do inżyniera zostało wysłane!")
        return redirect("filtered_display_board", category="engineer")

    return render(request, "call_engineer.html")

@login_required
def main_display_board(request):
    """
    Widok dla GŁÓWNEJ tablicy, grupujący aktywne tickety 
    z różnych działów (SupportTicket i WarehouseRequest).
    """
    active_support_statuses = ['open', 'in_progress']
    active_warehouse_statuses = ['new', 'in_progress']

    support_tickets = SupportTicket.objects.filter(status__in=active_support_statuses).order_by('created_at')
    warehouse_tickets = WarehouseRequest.objects.filter(status__in=active_warehouse_statuses).order_by('created_at')

    grouped_tickets = {
        'Technicy': [],
        'Inżynierowie': [],
        'Jakość': [],
        'Magazyn': []
    }

    for ticket in support_tickets:
        if ticket.category == 'technician':
            grouped_tickets['Technicy'].append(ticket)
        elif ticket.category == 'engineer':
            grouped_tickets['Inżynierowie'].append(ticket)
        elif ticket.category == 'quality':
            grouped_tickets['Jakość'].append(ticket)

    for ticket in warehouse_tickets:
        grouped_tickets['Magazyn'].append(ticket)

    final_grouped_tickets = {category: tickets for category, tickets in grouped_tickets.items() if tickets}
    has_any_tickets = bool(final_grouped_tickets)

    context = {
        'grouped_tickets': final_grouped_tickets,
        'has_any_tickets': has_any_tickets,
    }
    return render(request, "main_display_board.html", context)


@login_required
def filtered_display_board(request, category):
    """
    Widok dla FILTROWANEJ tablicy, pokazujący zgłoszenia 
    tylko dla wybranej kategorii (np. 'technician').
    """
    status_order = Case(
        When(status='open', then=Value(1)),
        When(status='in_progress', then=Value(2)),
        default=Value(3),
        output_field=IntegerField()
    )
    
    tickets = SupportTicket.objects.filter(
        category=category
    ).filter(
        Q(status__in=["open", "in_progress"]) | 
        Q(status="resolved", resolved_at__gt=now() - timedelta(days=2))
    ).annotate(
        status_order=status_order
    ).order_by('status_order', 'created_at')
    
    context = {
        "tickets": tickets,
        "category": category,
    }
    return render(request, "filtered_display_board.html", context)

@login_required
def take_ticket(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    ticket.status = "in_progress"
    ticket.assigned_to = request.user
    ticket.taken_at = now()
    ticket.save()
    messages.success(request, "✅ Zgłoszenie zostało podjęte!")
    return redirect("filtered_display_board", category=ticket.category)

@login_required
def close_ticket(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    ticket.status = "closed"
    ticket.resolved_by = request.user
    ticket.resolved_at = now()
    ticket.save()
    messages.success(request, "✅ Zgłoszenie zostało zamknięte!")
    return redirect("filtered_display_board", category=ticket.category)

def register_scrap_success(request):
    return render(request, "register_scrap_success.html")

def autocomplete_item(request):
    query = request.GET.get("query", "").strip()
    if query:
        items = Item.objects.filter(item_code__startswith=query)[:5]
        results = [{"code": item.item_code, "description": item.description} for item in items]
        return JsonResponse({"items": results})
    return JsonResponse({"items": []})

def get_items_by_group(request):
    group_name = request.GET.get("group")
    if not group_name:
        return JsonResponse({"error": "Brak grupy"}, status=400)

    items = C2MaterialItem.objects.filter(group__name=group_name).values("item_code", "description")
    return JsonResponse({"items": list(items)})

@login_required
def warehouse_ticket_board(request):
    """
    Wyświetla tablicę zgłoszeń między Produkcją a Magazynem.
    """
    open_tickets = WarehouseRequest.objects.filter(status='open')
    in_progress_tickets = WarehouseRequest.objects.filter(status='in_progress')
    closed_tickets = WarehouseRequest.objects.filter(status='closed')
    return render(request, 'warehouse_ticket_board.html', {
        'open_tickets': open_tickets,
        'in_progress_tickets': in_progress_tickets,
        'closed_tickets': closed_tickets
    })

@login_required
def call_warehouse(request):
    """
    Formularz zgłoszenia dla magazynu.
    """
    warehouse_reasons = WarehouseReason.objects.all()

    if request.method == "POST":
        location = request.POST.get("location")
        description = request.POST.get("description")
        item_code = request.POST.get("item_code")
        quantity = request.POST.get("quantity")
        warehouse_reason_id = request.POST.get("warehouse_reason")

        valid_locations = dict(WarehouseRequest.LOCATION_CHOICES).keys()
        if location not in valid_locations:
            messages.error(request, "Nieprawidłowa lokalizacja!")
            return redirect("call_warehouse")

        if description and item_code and quantity and warehouse_reason_id:
            item_obj = get_object_or_404(Item, item_code=item_code)
            warehouse_reason_obj = get_object_or_404(WarehouseReason, id=warehouse_reason_id)

            WarehouseRequest.objects.create(
                location=location,
                created_by=request.user,
                description=description,
                item=item_obj,
                quantity=quantity,
                warehouse_reason=warehouse_reason_obj,
                status="new"
            )
            magazyn_group = Group.objects.get(name="Magazyn")
            for user in magazyn_group.user_set.all():
                create_notification(user, f"Nowe wezwanie do magazynu", url=f"/warehouse-tickets/{WarehouseRequest.id}/")

            messages.success(request, "Zgłoszenie zostało wysłane do magazynu.")
            return redirect("warehouse_tickets")
        else:
            messages.error(request, "Wypełnij wszystkie pola!")

    return render(request, "call_warehouse.html", {"warehouse_reasons": warehouse_reasons})

@login_required
def update_warehouse_status(request, ticket_id, status):
    """
    Aktualizuje status zgłoszenia.
    """
    ticket = get_object_or_404(WarehouseRequest, id=ticket_id)
    ticket.status = status
    ticket.save()
    return redirect("warehouse_ticket_board")

@login_required
def add_warehouse_comment(request, ticket_id):
    """
    Dodaje komentarz do zgłoszenia magazynowego.
    """
    ticket = get_object_or_404(WarehouseRequest, id=ticket_id)
    if request.method == "POST":
        comment_text = request.POST.get("text")
        if comment_text:
            comment = WarehouseComment.objects.create(
                ticket=ticket,
                created_by=request.user,
                text=comment_text,
                created_at=timezone.now()
            )
            return JsonResponse({
                "user": comment.created_by.username,
                "text": comment.text,
                "created_at": comment.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            })
    return JsonResponse({"error": "Nieprawidłowe dane"}, status=400)

def get_warehouse_ticket_comments(request, ticket_id):
    """
    Pobiera komentarze do zgłoszenia w formacie JSON.
    """
    ticket = get_object_or_404(WarehouseRequest, id=ticket_id)
    comments = WarehouseComment.objects.filter(ticket=ticket).order_by("created_at")
    data = [{
        "user": comment.created_by.username,
        "text": comment.text,
        "created_at": comment.created_at.strftime("%Y-%m-%d %H:%M:%S")
    } for comment in comments]
    return JsonResponse({"comments": data})

@login_required
def warehouse_tickets(request):
    tickets = WarehouseRequest.objects.filter(status__in=["new", "in_progress"]) | WarehouseRequest.objects.filter(status="resolved", resolved_at__gt=TWO_DAYS_AGO)
    return render(request, "warehouse_tickets.html", {"tickets": tickets})

@login_required
def warehouse_ticket_detail(request, ticket_id):
    ticket = get_object_or_404(WarehouseRequest, id=ticket_id)
    if request.method == "POST":
        comment_text = request.POST.get("text")
        WarehouseComment.objects.create(ticket=ticket, text=comment_text, created_by=request.user)
        return JsonResponse({"user": request.user.username, "text": comment_text, "created_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S")})
    return render(request, "warehouse_ticket_detail.html", {"ticket": ticket})

@login_required
def take_warehouse_ticket(request, ticket_id):
    ticket = get_object_or_404(WarehouseRequest, id=ticket_id)
    if ticket.status == "new":
        ticket.status = "in_progress"
        ticket.handled_by = request.user  # Przypisanie użytkownika
        ticket.handled_at = timezone.now()  # Timestamp podjęcia zgłoszenia
        ticket.save()
    return redirect("warehouse_tickets")

@login_required
def close_warehouse_ticket(request, ticket_id):
    ticket = get_object_or_404(WarehouseRequest, id=ticket_id)
    if ticket.status == "in_progress":
        ticket.status = "resolved"
        ticket.resolved_at = timezone.now()  # Timestamp zakończenia zgłoszenia
        ticket.save()
    return redirect("warehouse_tickets")

def upload_production_log(request):
    """
    Wgrywa plik Excel z dziennym wykonaniem (ProductionLog).
    Zakładamy kolumny: 'Date', 'MO Number', 'Item Code', 'Quantity'
    """
    if request.method == "POST":
        excel_file = request.FILES.get("file")
        if not excel_file:
            return JsonResponse({"success": False, "error": "Nie wybrano pliku."})

        try:
            df = pd.read_excel(excel_file)

            for _, row in df.iterrows():
                ProductionLog.objects.create(
                    date = row["Date"],
                    mo_number = str(row["MO Number"]),
                    item_code = str(row["Item Code"]),
                    quantity = int(row["Quantity"])
                )
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return render(request, "upload_production_log.html")


# Funkcja generująca wykres porównujący produkcję
def generate_production_chart(planned_quantities, executed_quantities, labels):
    plt.figure(figsize=(10, 5))

    x = range(len(labels))  # Oś X to indeksy MO Numbers

    plt.bar(x, planned_quantities, width=0.4, label='Produkcja planowana', color='blue', align='center')
    plt.bar(x, executed_quantities, width=0.4, label='Produkcja wykonana', color='red', align='edge')

    plt.xlabel('Zlecenia produkcyjne (MO Number)')
    plt.ylabel('Ilość')
    plt.title('Porównanie planowanej i wykonanej produkcji')
    plt.xticks(x, labels, rotation=45, ha="right")
    plt.legend()

    # Zapisz wykres do base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()

    return image_base64

# Widok raportu
def production_report_view(request):
    line = request.GET.get("line", "")
    gpg = request.GET.get("gpg", "")

    # Pobierz wszystkie plany produkcji
    plans = ProductionPlan.objects.select_related("production_order__item")

    # Filtrowanie po linii produkcyjnej i GPG
    if line:
        plans = plans.filter(production_order__item__production_line=line)
    if gpg:
        plans = plans.filter(production_order__item__gpg=gpg)

    results = []
    planned_quantities = []
    executed_quantities = []
    labels = []

    for plan in plans:
        order = plan.production_order
        mo_num = order.mo_number
        plan_qty = order.planned_quantity

        done = ProductionLog.objects.filter(mo_number=mo_num).aggregate(s=Sum("quantity"))["s"] or 0
        percent = round((done / plan_qty) * 100, 2) if plan_qty else 0
        item_code = order.item.item_code if order.item else "Brak danych"

        results.append({
            "mo_number": mo_num,
            "planned": plan_qty,
            "done": done,
            "percent": percent,
            "date": str(plan.date),
            "status": order.status,
            "item": item_code
        })

        planned_quantities.append(plan_qty)
        executed_quantities.append(done)
        labels.append(mo_num)

    # Oblicz sumy zbiorcze
    total_planned = sum(planned_quantities)
    total_done = sum(executed_quantities)
    global_percent = round((total_done / total_planned) * 100, 2) if total_planned > 0 else 0
    open_orders = sum(1 for r in results if r["done"] < r["planned"])

    # Generowanie wykresu
    chart_base64 = generate_production_chart(planned_quantities, executed_quantities, labels)

    # Kontekst dla szablonu
    context = {
        "results": results,
        "total_planned": total_planned,
        "total_done": total_done,
        "global_percent": global_percent,
        "open_orders": open_orders,
        "chart_base64": chart_base64,
    }

    return render(request, "production_report.html", context)

def get_production_report_data(request):
    """
    Zwraca JSON z danymi do raportu (planowana vs wykonana produkcja)
    """
    line = request.GET.get("line", "")
    gpg = request.GET.get("gpg", "")
    date_filter = request.GET.get("date", "")

    # Pobranie zleceń z planu produkcji
    qs = ProductionPlan.objects.select_related("production_order__item")

    # Filtrowanie po linii produkcyjnej
    if line:
        qs = qs.filter(production_order__item__production_line=line)

    # Filtrowanie po GPG
    if gpg:
        qs = qs.filter(production_order__item__gpg=gpg)

    # Filtrowanie po dacie
    if date_filter == "overdue":
        qs = qs.filter(date__lt=now().date())
    elif date_filter == "this_week":
        qs = qs.filter(date__range=[now().date(), now().date() + timedelta(days=6)])
    elif date_filter == "today":
        qs = qs.filter(date=now().date())

    results = []
    planned_quantities = []
    executed_quantities = []

    for plan in qs:
        order = plan.production_order
        mo_num = order.mo_number
        planned_qty = order.planned_quantity

        done_qty = ProductionLog.objects.filter(mo_number=mo_num).aggregate(Sum("quantity"))["quantity__sum"] or 0
        percent_done = round((done_qty / planned_qty) * 100, 2) if planned_qty else 0

        results.append({
            "mo_number": mo_num,
            "planned": planned_qty,
            "done": done_qty,
            "percent": percent_done,
            "date": str(plan.date),
            "status": order.status,
            "item": order.item.item_code if order.item else "Brak danych"
        })

        planned_quantities.append(planned_qty)
        executed_quantities.append(done_qty)

    # Oblicz sumy zbiorcze
    total_planned = sum(planned_quantities)
    total_done = sum(executed_quantities)
    global_percent = round((total_done / total_planned) * 100, 2) if total_planned > 0 else 0
    open_orders = sum(1 for r in results if r["done"] < r["planned"])

    response_data = {
        "labels": [r["mo_number"] for r in results],
        "planned": [r["planned"] for r in results],
        "done": [r["done"] for r in results],
        "results": results,
        "stats": {
            "open_orders": open_orders,
            "total_planned": total_planned,
            "total_done": total_done,
            "global_percent": global_percent,
        }
    }

    return JsonResponse(response_data, safe=False)

def import_scrap_codes(request):
    if request.method == "POST":
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES["file"]
            try:
                df = pd.read_excel(file)
                for _, row in df.iterrows():
                    ScrapCode.objects.update_or_create(
                        code=row["Kod"],
                        defaults={"description": row["Opis"]}
                    )
                messages.success(request, "Kody złomu zostały zaimportowane!")
            except Exception as e:
                messages.error(request, f"Błąd importu: {e}")
            return redirect("admin:index")

    return render(request, "import_scrap_codes.html", {"form": ExcelUploadForm()})


@login_required
def cycle_count_requests(request):
    if request.method == "POST":
        # Odczytujemy pola z formularza
        item_code = request.POST.get("item_code", "").strip()
        location_name = request.POST.get("location_name", "").strip()
        system_qty = request.POST.get("system_qty", "0")
        physical_qty = request.POST.get("physical_qty", "0")
        comment = request.POST.get("comment", "").strip()

        # Walidacja minimalna
        if not item_code:
            messages.error(request, "Nie podano kodu Itemu!")
            return redirect("cycle_count_requests")
        if not location_name:
            messages.error(request, "Nie podano lokalizacji!")
            return redirect("cycle_count_requests")

        # Znajdujemy obiekt Item wg item_code
        try:
            item_obj = Item.objects.get(item_code=item_code)
        except Item.DoesNotExist:
            messages.error(request, f"Item {item_code} nie istnieje w bazie!")
            return redirect("cycle_count_requests")

        # Znajdujemy obiekt Location wg nazwy
        try:
            location_obj = Location.objects.get(name=location_name)
        except Location.DoesNotExist:
            messages.error(request, f"Lokalizacja {location_name} nie istnieje!")
            return redirect("cycle_count_requests")

        # Konwersja ilości (obsługa błędów)
        try:
            system_qty = int(system_qty)
            physical_qty = int(physical_qty)
        except ValueError:
            messages.error(request, "Niepoprawne wartości ilości!")
            return redirect("cycle_count_requests")

        # Tworzymy wniosek
        CycleCountRequest.objects.create(
            item=item_obj,
            location=location_obj,
            system_qty=system_qty,
            physical_qty=physical_qty,
            comment=comment,
            created_by=request.user,
        )

        messages.success(request, "Zgłoszono wniosek o przeliczenie!")
        return redirect("cycle_count_requests")

    # Jeśli GET – wyświetlamy formularz
    # i listę istniejących wniosków
    requests_qs = CycleCountRequest.objects.order_by("-created_at")

    # Tworzymy listę słowników do szablonu z obliczoną różnicą
    items_for_template = []
    for req in requests_qs:
        diff = req.physical_qty - req.system_qty
        items_for_template.append({
            "item": req.item,
            "location": req.location,
            "system_qty": req.system_qty,
            "physical_qty": req.physical_qty,
            "difference": diff,
            "comment": req.comment,
            "status": req.get_status_display(),
        })

    return render(request, "cycle_count_requests.html", {
        "items": items_for_template
    })

@login_required
def update_cycle_count_status(request, request_id, status):
    """
    Aktualizuje status zgłoszenia Cycle Count.
    """
    valid_statuses = ["review", "closed", "removed"]
    if status not in valid_statuses:
        messages.error(request, "Nieprawidłowy status!")
        return redirect("cycle_count_view")

    cycle_request = get_object_or_404(CycleCountRequest, id=request_id)
    cycle_request.status = status
    cycle_request.save()

    if status in ["closed", "removed"]:
        cycle_request.closed_by = request.user
        cycle_request.closed_at = timezone.now()
    else:
        # Jeśli wracasz do "review", możesz wyzerować closed_by i closed_at, jeśli chcesz
        cycle_request.closed_by = None
        cycle_request.closed_at = None

    cycle_request.save()

    messages.success(request, f"Status zgłoszenia #{cycle_request.id} zmieniono na {cycle_request.get_status_display()}")
    return redirect("cycle_count_view")

@login_required
def cycle_count_view(request):
    requests = CycleCountRequest.objects.all().order_by("-created_at")
    items = []
    for req in requests:
        diff = req.physical_qty - req.system_qty
        items.append({
            "id": req.id,
            "item": req.item,
            "location": req.location,
            "system_qty": req.system_qty,
            "physical_qty": req.physical_qty,
            "difference": diff,
            "comment": req.comment,
            "status": req.status,
            "get_status_display": req.get_status_display(),
        })
    cutoff_date = now() - timedelta(days=30)

    # Pobranie zgłoszeń
    requests = CycleCountRequest.objects.filter(
        # Filtrujemy otwarte lub zamknięte w ciągu ostatnich 30 dni
        Q(status__in=["new", "review"]) |
        Q(status__in=["closed", "removed"], closed_at__gte=cutoff_date)
    ).order_by("-created_at")

    return render(request, "cycle_count_view.html", {"requests": items})

def check_scrap_code(request):
    """Sprawdza, czy wpisany kod scrapu istnieje w bazie"""
    scrap_code = request.GET.get("code", "").strip().upper()
    exists = ScrapCode.objects.filter(code=scrap_code).exists()
    return JsonResponse({"exists": exists})

def check_location(request):
    """Sprawdza, czy wpisana lokalizacja istnieje w bazie Location"""
    location_name = request.GET.get("location", "").strip().upper()
    exists = Location.objects.filter(name=location_name).exists()
    return JsonResponse({"exists": exists})

def autocomplete_item(request):
    query = request.GET.get("query", "").strip()
    items = Item.objects.filter(item_code__icontains=query)[:5]  # np. 5 podpowiedzi
    data = [{"code": i.item_code, "description": i.description} for i in items]
    return JsonResponse({"items": data})

def autocomplete_location(request):
    query = request.GET.get("query", "").strip()
    locations = Location.objects.filter(name__icontains=query)[:5]  # 5 pasujących
    data = [{"name": loc.name} for loc in locations]
    return JsonResponse({"locations": data})

@login_required
def cycle_count_report(request):
    # 1) Odczyt parametrów
    start_date_str = request.GET.get("start_date", "")
    end_date_str = request.GET.get("end_date", "")
    status_filter = request.GET.get("status", "")

    qs = CycleCountRequest.objects.all()

    # 2) Filtrowanie po datach
    try:
        if start_date_str:
            start_dt = make_aware(datetime.strptime(start_date_str, "%Y-%m-%d"))
            qs = qs.filter(created_at__gte=start_dt)
        if end_date_str:
            end_dt = make_aware(datetime.strptime(end_date_str, "%Y-%m-%d"))
            qs = qs.filter(created_at__lte=end_dt)
    except ValueError:
        pass  # Jeśli parsowanie się nie uda, pomiń filtrowanie i/lub wyświetl błąd

    # 3) Filtrowanie po statusie (opcjonalne)
    if status_filter:
        qs = qs.filter(status=status_filter)

    # 4) Obliczenie sumarycznych statystyk (status, wartość)
    status_counts = qs.values("status").annotate(count=Count("id")).order_by("status")

    # Dodaj 'cost' = item.price * (physical_qty - system_qty)
    qs_value = qs.annotate(
        difference=F("physical_qty") - F("system_qty"),
        cost=F("item__price") * (F("physical_qty") - F("system_qty"))
    )
    total_value = qs_value.aggregate(total_cost=Sum("cost"))["total_cost"] or 0

    # Policz liczbę ticketów w poszczególnych statusach
    new_count     = qs.filter(status="new").count()
    review_count  = qs.filter(status="review").count()
    closed_count  = qs.filter(status="closed").count()
    removed_count = qs.filter(status="removed").count()

    requests_count = qs.count()

    # 5) Generowanie danych do WYKRESU – oś X = data
    # Grupujemy dziennie i liczymy liczbę ticketów (daily_count) i sumę kosztów (daily_value)
    daily_stats = qs_value.annotate(
        day=TruncDate("created_at")
    ).values("day").annotate(
        daily_count=Count("id"),
        daily_value=Sum("cost")
    ).order_by("day")

    # Zmieniamy na listy w Pythonie
    dates_list = []
    counts_list = []
    values_list = []
    for row in daily_stats:
        date_str = row["day"].strftime("%Y-%m-%d")
        dates_list.append(date_str)
        counts_list.append(int(row["daily_count"] or 0))  # Liczba ticketów
        # Konwersja Decimal -> float:
        value_float = float(row["daily_value"] or 0)
        values_list.append(value_float)

    # Zamieniamy na JSON, by wstawić w <script> i bezpiecznie sparsować w JS
    chart_dates_json  = json.dumps(dates_list)
    chart_counts_json = json.dumps(counts_list)
    chart_values_json = json.dumps(values_list)

    context = {
        "start_date_str": start_date_str,
        "end_date_str": end_date_str,
        "status_filter": status_filter,
        "requests_count": requests_count,
        "total_value": total_value,
        "new_count": new_count,
        "review_count": review_count,
        "closed_count": closed_count,
        "removed_count": removed_count,
        # Dla wykresu
        "chart_dates": chart_dates_json,   # oś X = data
        "chart_counts": chart_counts_json, # Y1 = ilość ticketów
        "chart_values": chart_values_json, # Y2 = łączna wartość
    }
    return render(request, "cycle_count_report.html", context)

@login_required
def inv_request_list(request):
    requests = InvRequest.objects.all()

    # Pobieranie dat z parametrów GET
    created_from = request.GET.get('created_from')
    created_to = request.GET.get('created_to')

    # Filtrowanie wniosków na podstawie dat
    if created_from:
        requests = requests.filter(created_at__gte=parse_date(created_from))
    if created_to:
        requests = requests.filter(created_at__lte=parse_date(created_to))

    # Paginacja
    paginator = Paginator(requests, 20)  # 20 wniosków na stronę
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Obliczanie sumy wartości zatwierdzonych wniosków w bieżącym miesiącu
    now_date = now()
    current_month_start = now_date.replace(day=1)
    current_month_end = (now_date.replace(month=now_date.month % 12 + 1, day=1) - timedelta(days=1))
    approved_requests = InvRequest.objects.filter(
        status='approved',
        created_at__gte=current_month_start,
        created_at__lte=current_month_end
    )

    # Obliczanie wartości dynamicznie
    total_approved_value = InvRequestLine.objects.filter(
        request__in=approved_requests
    ).aggregate(
        total_value=Sum(
            ExpressionWrapper(
                F('quantity') * F('item__price') * -1,
                output_field=DecimalField()
            )
        )
    )['total_value'] or 0

    user_groups = request.user.groups.values_list('name', flat=True)

    return render(request, 'inv_request_list.html', {
        'page_obj': page_obj,
        'total_approved_value': total_approved_value,
        'user_groups': user_groups
    })

@login_required
def inv_request_create(request):
    if request.method == "POST":
        item_codes = request.POST.get("item_codes", "").strip().split("\n")
        quantities = request.POST.get("quantities", "").strip().split("\n")
        locations = request.POST.get("locations", "").strip().split("\n")
        scrap_codes = request.POST.get("scrap_codes", "").strip().split("\n")

        # Przekierowanie do widoku podglądu
        request.session['item_codes'] = item_codes
        request.session['quantities'] = quantities
        request.session['locations'] = locations
        request.session['scrap_codes'] = scrap_codes

        return redirect("inv_request_preview")

    return render(request, "inv_request_create.html")

@login_required
def inv_request_detail(request, req_id):
    """
    Szczegóły wniosku.
    """
    inv_req = get_object_or_404(InvRequest, id=req_id)
    return render(request, "inv_request_detail.html", {
        "inv_req": inv_req
    })


@login_required
def inv_request_approve(request, req_id):
    """
    Zatwierdzenie wniosku w zależności od bieżącego etapu:
      - Sprawdza status wniosku,
      - Weryfikuje, czy user ma prawo do tego kroku (grupa 'Magazyn', 'Dyrektor', 'CycleCount'),
      - Przechodzi do kolejnego etapu lub finalnie -> 'approved'.
    """
    inv_req = get_object_or_404(InvRequest, id=req_id)

    # Obliczamy wartość wniosku
    total_val = inv_req.total_value()

    # 1. Sprawdź, na jakim etapie jest wniosek
    if inv_req.status == "awaiting_magazyn":
        # Czy user jest w grupie 'Magazyn'?
        if not request.user.groups.filter(name="Magazyn").exists():
            messages.error(request, "Brak uprawnień (Magazyn)!")
            return redirect("inv_request_list")

        # Tutaj wniosek idzie dalej.
        inv_req.status = "awaiting_dyrektor"
        messages.success(request, "Etap Magazyn zaliczony!")

    elif inv_req.status == "awaiting_dyrektor":
        # Czy user jest w grupie 'Dyrektor'?
        if not request.user.groups.filter(name="Dyrektor").exists():
            messages.error(request, "Brak uprawnień (Dyrektor)!")
            return redirect("inv_request_list")

        # Przechodzimy do etapu 3
        inv_req.status = "awaiting_cycle"
        messages.success(request, "Etap Dyrektor zaliczony!")

    elif inv_req.status == "awaiting_cycle":
        # Czy user jest w grupie 'CycleCount'?
        if not request.user.groups.filter(name="CycleCount").exists():
            messages.error(request, "Brak uprawnień (CycleCount)!")
            return redirect("inv_request_list")

        # To już ostatni etap → wniosek finalnie zatwierdzony
        inv_req.status = "approved"
        inv_req.approved_by = request.user
        inv_req.approved_at = now()
        messages.success(request, "Wniosek został całkowicie zatwierdzony!")

    elif inv_req.status in ["approved", "rejected"]:
        messages.warning(request, "Wniosek jest już w statusie końcowym!")
        return redirect("inv_request_list")

    else:
        # Jeżeli wniosek ma jakiś inny status, nieobsługiwany
        messages.error(request, f"Nieobsługiwany status: {inv_req.status}")
        return redirect("inv_request_list")

    # Zapisujemy zmianę statusu
    inv_req.save()
    return redirect("inv_request_list")


@login_required
def inv_request_reject(request, req_id):
    """
    Odrzucenie wniosku na dowolnym etapie.
    """
    inv_req = get_object_or_404(InvRequest, id=req_id)

    # Przykładowo: każda z grup, która mogłaby zaakceptować, może też odrzucić
    # lub dozwolisz to tylko 'Magazyn' i 'Dyrektor'?
    # W prostym wariancie sprawdzamy, czy user jest w jakiejś z tych grup.
    if not (
    request.user.groups.filter(name="Magazyn").exists() or
    request.user.groups.filter(name="Dyrektor").exists() or
    request.user.groups.filter(name="CycleCount").exists()
            ):
        messages.error(request, "Brak uprawnień do odrzucenia!")
        return redirect("inv_request_list")

    # Ustawiamy finalny status 'rejected'
    inv_req.status = "rejected"
    inv_req.rejected_by = request.user
    inv_req.rejected_at = now()
    inv_req.save()

    messages.warning(request, f"Wniosek #{inv_req.id} został ODRZUCONY!")
    return redirect("inv_request_list")

@login_required
def inv_request_preview(request):
    item_codes = request.session.get('item_codes', [])
    quantities = request.session.get('quantities', [])
    locations = request.session.get('locations', [])
    scrap_codes = request.session.get('scrap_codes', [])

    # Walidacja danych
    errors = []
    items = []
    total_value = 0
    for code in item_codes:
        code = code.strip()
        try:
            item = Item.objects.get(item_code=code)
            items.append(item)
        except Item.DoesNotExist:
            errors.append(f"Item o kodzie {code} nie istnieje.")

    if errors:
        for error in errors:
            messages.error(request, error)
        return redirect("inv_request_create")

    # Przekazujemy dane do szablonu
    preview_data = []
    for i in range(len(item_codes)):
        quantity = int(quantities[i].strip())
        item = items[i]
        price = item.price  # Assuming `price` field exists in `Item` model
        value = quantity * price * -1
        total_value += value
        preview_data.append({
            "item_code": item_codes[i].strip(),
            "quantity": quantity,
            "location": locations[i].strip(),
            "scrap_code": scrap_codes[i].strip(),
            "price": price,
            "value": value,
            "item": item
        })

    return render(request, "inv_request_preview.html", {
        "preview_data": preview_data,
        "total_value": total_value
    })

@login_required
def inv_request_submit(request):
    if request.method == "POST":
        item_codes = request.session.get('item_codes', [])
        quantities = request.session.get('quantities', [])
        locations = request.session.get('locations', [])
        scrap_codes = request.session.get('scrap_codes', [])

        # Walidacja danych
        errors = []
        items = []
        for code in item_codes:
            code = code.strip()
            try:
                item = Item.objects.get(item_code=code)
                items.append(item)
            except Item.DoesNotExist:
                errors.append(f"Item o kodzie {code} nie istnieje.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect("inv_request_create")

        # Tworzymy nowy wniosek
        inv_request = InvRequest.objects.create(
            created_by=request.user,
            status="awaiting_magazyn",
            created_at=now()
        )

        # Dodajemy pozycje do wniosku
        for i in range(len(item_codes)):
            item = items[i]
            location = Location.objects.get(name=locations[i].strip())
            scrap_code = ScrapCode.objects.get(code=scrap_codes[i].strip())
            quantity = int(quantities[i].strip())

            InvRequestLine.objects.create(
                request=inv_request,
                item=item,
                quantity=quantity,
                location=location,
                scrap_code=scrap_code
            )

        messages.success(request, "✅ Wniosek został zapisany!")
        return redirect("inv_request_list")  # Przekierowanie do listy wniosków

    return redirect("inv_request_create")

@login_required
def inv_request_cancel(request, req_id):
    """
    Anulowanie wniosku przez autora.
    """
    inv_req = get_object_or_404(InvRequest, id=req_id)

    # Sprawdzenie, czy użytkownik jest autorem wniosku
    if inv_req.created_by != request.user:
        messages.error(request, "Brak uprawnień do anulowania tego wniosku!")
        return redirect("inv_request_list")

    # Ustawiamy status 'cancelled'
    inv_req.status = "cancelled"
    inv_req.save()

    messages.success(request, f"Wniosek #{inv_req.id} został anulowany!")
    return redirect("inv_request_list")

@login_required
def notifications_list(request):
    notifications = request.user.notifications.all()
    return render(request, 'notifications_list.html', {'notifications': notifications})

@login_required
def mark_as_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.read = True
    notification.save()
    return JsonResponse({"success": True})
@login_required
def get_unread_notifications(request):
    notifications = request.user.notifications.filter(read=False)
    data = [
        {
            "id": n.id,
            "message": n.message,
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "url": n.url
        }
        for n in notifications
    ]
    return JsonResponse({"notifications": data, "count": notifications.count()})

def create_notification(user, message, url=None):
    Notification.objects.create(user=user, message=message, url=url)
