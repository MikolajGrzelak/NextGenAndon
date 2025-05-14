from django.contrib import admin
from .models import (
    Item, Client, ExcelUpload, ScrapEntry, SupportTicket, QualityReason,
    C2MaterialGroup, C2MaterialItem, WarehouseReason, WarehouseRequest, WarehouseComment, ProductionPlan, Location,
    ProductionOrder, ScrapCode, CycleCountRequest, InvRequest, InvRequestLine
)
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db import models


# 🔹 SEKCA: PRODUKCJA
@admin.register(ScrapEntry)
class ScrapEntryAdmin(admin.ModelAdmin):
    list_display = ("item", "quantity", "total_cost", "created_at", "reported_by", "gpg", "production_line")
    list_filter = ("created_at",)
    search_fields = ("item__item_code",)

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("item_code", "description", "supplier", "responsible", "price", "production_time", "gpg", "production_line")
    search_fields = ("item_code", "description", "supplier", "gpg", "production_line")

admin.site.register(QualityReason)

# 🔹 SEKCJA: PLANOWANIE
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('client_number', 'client_name')

@admin.register(ProductionOrder)
class ProductionOrderAdmin(admin.ModelAdmin):
    list_display = ("mo_number", "item", "mo_quantity", "produced_quantity", "status", "production_line", "created_at")
    list_filter = ("status", "production_line")
    search_fields = ("mo_number", "item__item_code")

@admin.register(ProductionPlan)
class ProductionPlanAdmin(admin.ModelAdmin):
    list_display = ("production_order", "date", "created_at")  # Poprawione nazwy pól
    list_filter = ("date",)
    search_fields = ("production_order__mo_number",)

    def get_readonly_fields(self, request, obj=None):
        """ Ustawia 'created_at' jako tylko do odczytu, jeśli edytujemy istniejący wpis """
        if obj:
            return ("created_at",)
        return ()

# 🔹 SEKCJA: OBSŁUGA ZGŁOSZEŃ
@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "workplace", "created_by", "created_at", "status", "assigned_to", "resolved_by", "taken_at", "resolved_at")
    list_filter = ("status", "category", "workplace")
    search_fields = ("workplace", "created_by__username", "assigned_to__username", "description")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "taken_at", "resolved_at")

    fieldsets = (
        ("Informacje o zgłoszeniu", {
            "fields": ("category", "workplace", "description", "status"),
        }),
        ("Osoby", {
            "fields": ("created_by", "assigned_to", "resolved_by"),
        }),
        ("Czas", {
            "fields": ("created_at", "taken_at", "resolved_at"),
        }),
    )

admin.site.register(C2MaterialGroup)
admin.site.register(C2MaterialItem)

# 🔹 SEKCJA: MAGAZYN
class WarehouseCommentInline(admin.TabularInline):
    """ Widok komentarzy w zgłoszeniach magazynowych """
    model = WarehouseComment
    extra = 0  
    readonly_fields = ("created_by", "text", "created_at")
    can_delete = False  

@admin.register(WarehouseRequest)
class WarehouseRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "created_by", "location", "category", "status", "created_at", "resolved_at")
    list_filter = ("status", "category", "location")
    search_fields = ("id", "created_by__username", "description")
    readonly_fields = ("created_at", "resolved_at", "created_by")  
    inlines = [WarehouseCommentInline]  

admin.site.register(WarehouseReason)

@admin.register(ScrapCode)
class ScrapCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "description")
    search_fields = ("code", "description")

@admin.register(ExcelUpload)
class ExcelUploadAdmin(admin.ModelAdmin):
    list_display = ("file", "upload_type", "uploaded_at")
    search_fields = ("upload_type",)
    list_filter = ("upload_type",)

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

@admin.register(CycleCountRequest)
class CycleCountRequestAdmin(admin.ModelAdmin):
    """
    Panel w Django Admin do przeglądania wniosków o przeliczenie (Cycle Count).
    """
    # Pola wyświetlane w kolumnach na liście wniosków
    list_display = (
        "id", 
        "item", 
        "location", 
        "system_qty", 
        "physical_qty", 
        "status", 
        "created_by", 
        "created_at",
        "closed_at",
        "closed_by"
    )

    # Dodajemy filtry boczne
    list_filter = (
        "status",
        "created_by",
        "created_at",
        "closed_at",
    )

    # Możliwość wyszukiwania po różnych polach
    search_fields = (
        "item__item_code",
        "location__name",
        "comment",
    )

    # Pasek nawigacji po dacie w górnej części
    date_hierarchy = "created_at"

    # Jeśli chcesz, by szczegóły wiersza były tylko do odczytu
    # readonly_fields = ("created_at", "created_by", ...)

    # Możesz również użyć 'fields' lub 'fieldsets' do układu w edycji
    
class InvRequestLineInline(admin.TabularInline):
    model = InvRequestLine
    extra = 1
    max_num = 25  # Ograniczenie liczby wyświetlanych wierszy

class InvRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_by', 'status', 'created_at', 'total_value')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'created_by__username')
    readonly_fields = ('view_lines',)
    inlines = [InvRequestLineInline]

    fieldsets = (
        (None, {
            'fields': ('created_by', 'status', 'created_at', 'total_value')
        }),
        ('Pozycje wniosku', {
            'fields': ('view_lines',)
        }),
    )

    def total_value(self, obj):
        return sum(line.line_value() for line in obj.lines.all())
    total_value.short_description = 'Total Value'

    def view_lines(self, obj):
        lines = obj.lines.all()
        return mark_safe(self._generate_html_list(lines))
    view_lines.short_description = 'Pozycje wniosku'

    def _generate_html_list(self, lines):
        html = "<ul>"
        for line in lines:
            html += self._generate_html_list_item(line)
        html += "</ul>"
        return html

    def _generate_html_list_item(self, line):
        return f"<li>{line.item} - {line.quantity} szt. - {line.location} - {line.scrap_code}</li>"

admin.site.register(InvRequest, InvRequestAdmin)

