import os
import pandas as pd
from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.timezone import now
from django.apps import apps

class Item(models.Model):
    """
    Model do przechowywania danych o przedmiotach (Item).
    Przykładowe kolumny importowane z Excela: 
      - Item
      - Description
      - Supplier
      - Responsible
      - Price
      - ProductionTime
    """
    item_code = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    supplier = models.CharField(max_length=150, blank=True)
    responsible = models.CharField(max_length=150, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    production_time = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Czas produkcji w godzinach, np. 1.5 = 1h 30min"
    )
    gpg = models.CharField(max_length=255, blank=True, null=True)
    production_line = models.CharField(max_length=5, blank=True, null=True)

    def __str__(self):
        return f"{self.item_code} - {self.description}"

class Client(models.Model):
    """
    Model do przechowywania danych o klientach.
    Przykładowe kolumny importowane z Excela:
      - client_number
      - client_name
    """
    client_number = models.CharField(max_length=50, unique=True)
    client_name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.client_number} - {self.client_name}"

class ExcelUpload(models.Model):
    """
    Model pomocniczy do obsługi wgrywania plików Excel (.xlsx) z panelu admina.
      - file: plik Excel
      - upload_type: określa, czy plik dotyczy Itemów czy Klientów
      - uploaded_at: data i godzina wgrania pliku

    Po zapisaniu w adminie:
      - sprawdzamy rozszerzenie pliku (w 'clean()'),
      - w 'save()' wywołujemy odpowiednią metodę importującą,
      - w razie błędów walidacji usuwamy plik i rzucamy ValidationError.
    """
    file = models.FileField(upload_to='uploads/')
    upload_type = models.CharField(
        max_length=50,
        choices=(
            ('items', 'Importuj Itemy'),
            ('clients', 'Importuj Klientów'),
            ('locations', 'Importuj Lokacje'),
            ('scrap_codes', 'Importuj Kody złomu'),
        )
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Plik {self.file.name} - {self.upload_type}"

    def clean(self):
        """
        Podstawowa walidacja przed zapisaniem (np. format pliku).
        Metoda clean() wywoływana jest przez admina przed zapisaniem modelu.
        """
        super().clean()

        if not self.file:
            raise ValidationError("Nie wybrałeś pliku do importu.")

        if not self.file.name.endswith('.xlsx'):
            raise ValidationError("Wybierz plik w formacie .xlsx.")

    def save(self, *args, **kwargs):
        """
        Po super().save() plik będzie fizycznie dostępny w 'uploads/'.
        Następnie, w zależności od upload_type, wykonujemy import.
        Jeśli wystąpi błąd, usuwamy plik i ponownie rzucamy ValidationError.
        """
        super().save(*args, **kwargs)  # Zapisuje obiekt i przenosi plik do 'uploads/'

        try:
            if self.upload_type == 'items':
                self._import_items()
            elif self.upload_type == 'clients':
                self._import_clients()
            elif self.upload_type == 'locations':
                self._import_locations()
            elif self.upload_type == 'scrap_codes':
                self._import_scrap_codes()
        except ValidationError as e:
            # Usuwamy plik w razie błędu, by nie zalegał na serwerze
            if self.file and os.path.exists(self.file.path):
                os.remove(self.file.path)
            raise e

    def _import_items(self):
        """
        Importuje listę itemów z pliku Excel. 
        - Pomija puste wiersze.
        - Obsługuje liczby zapisane z przecinkiem (zamienia na kropki).
        - Aktualizuje istniejące rekordy lub tworzy nowe.
        - Loguje błędy, aby łatwiej było je znaleźć.
        """
        import pandas as pd
        from decimal import Decimal
        from django.core.exceptions import ValidationError
        from .models import Item  # Import modelu, jeśli jest w tym samym pliku
        
        try:
            df = pd.read_excel(self.file.path)
        except Exception as e:
            raise ValidationError(f"Błąd podczas odczytu pliku Excel: {str(e)}")

        # Sprawdzamy wymagane kolumny
        required_cols = ["Item", "Description", "Supplier", "Responsible", "Price", "ProductionTime"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValidationError(f"Brak wymaganych kolumn: {', '.join(missing_cols)}")

        errors = []  # Lista na błędy

        for i, row in df.iterrows():
            try:
                # Pobieramy Item Code (ID produktu)
                item_code = str(row["Item"]).strip() if not pd.isna(row["Item"]) else None
                if not item_code:
                    continue  # Pomijamy puste wiersze

                # Pobieramy pozostałe pola
                description = row.get("Description", "")
                supplier = row.get("Supplier", "")
                responsible = row.get("Responsible", "")
                price = row.get("Price", 0)
                production_time = row.get("ProductionTime", 0)
                gpg = row.get("GPG", "")
                production_line = row.get("ProductionLine", "")

                # Konwersja wartości liczbowych (obsługa przecinków)
                try:
                    price_str = str(price).replace(',', '.')
                    price_value = Decimal(price_str) if price_str else Decimal("0.00")
                except Exception:
                    errors.append(f"BŁĄD KONWERSJI CENY W WIERSZU {i+2}: {price}")
                    price_value = Decimal("0.00")  # Ustaw domyślną wartość

                try:
                    production_time_str = str(production_time).replace(',', '.')
                    production_time_value = Decimal(production_time_str) if production_time_str else Decimal("0.00")
                except Exception:
                    errors.append(f"BŁĄD KONWERSJI CZASU PRODUKCJI W WIERSZU {i+2}: {production_time}")
                    production_time_value = Decimal("0.00")

                # Próba zapisania rekordu w bazie (update_or_create)
                try:
                    Item.objects.update_or_create(
                        item_code=item_code,
                        defaults={
                            "description": description,
                            "supplier": supplier,
                            "responsible": responsible,
                            "price": price_value,
                            "production_time": production_time_value,
                            "gpg": gpg,
                            "production_line": production_line
                        }
                    )
                except Exception as e:
                    errors.append(f"BŁĄD ZAPISU WIERSZA {i+2} (Item: {item_code}): {e}")

            except Exception as err:
                errors.append(f"🔴 Nieznany błąd w wierszu {i+2}: {err}")

        # Jeśli są błędy, podnieś ValidationError, aby użytkownik widział problem
        if errors:
            raise ValidationError(errors)
    def _import_clients(self):
        from .models import Client
        try:
            df = pd.read_excel(self.file.path)
        except Exception as e:
            raise ValidationError(f"Błąd podczas odczytu pliku Excel: {str(e)}")

        required_cols = ["client_number", "client_name"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValidationError(f"Brak wymaganych kolumn: {', '.join(missing_cols)}")

        errors = []

        # 1) Zamiast listy, używamy słownika { client_number: { dane } }
        clients_dict = {}

        for i, row in df.iterrows():
            client_number = row["client_number"]
            client_name = row["client_name"]

            if pd.isna(client_number) or not str(client_number).strip():
                errors.append(f"[Wiersz {i+2}] Brak wartości w 'client_number'")
                continue
            if pd.isna(client_name) or not str(client_name).strip():
                errors.append(f"[Wiersz {i+2}] Brak wartości w 'client_name'")
                continue

            # 2) Konwertujemy do stringów i usuwamy spacje:
            c_num_clean = str(client_number).strip()
            c_name_clean = str(client_name).strip()

            # 3) Wstawiamy/aktualizujemy w słowniku
            #    Jeśli ten client_number pojawi się ponownie, to zostanie nadpisany
            clients_dict[c_num_clean] = {
                "client_number": c_num_clean,
                "client_name": c_name_clean
            }

        if errors:
            raise ValidationError(errors)

        # 4) Usuwamy stare rekordy (jeśli taką masz logikę)
        Client.objects.all().delete()

        # 5) Tworzymy nowych klientów
        for c_data in clients_dict.values():
            Client.objects.create(**c_data)

    def _import_locations(self):
        """
        Importuje listę lokalizacji z pliku Excel.
        - Każda lokalizacja ma maksymalnie 15 znaków.
        - Sprawdza unikalność lokalizacji.
        """
        import pandas as pd
        from .models import Location  # Model Lokalizacji

        try:
            df = pd.read_excel(self.file.path)
        except Exception as e:
            raise ValidationError(f"Błąd odczytu pliku Excel: {str(e)}")

        required_cols = ["Location"]
        if not all(col in df.columns for col in required_cols):
            raise ValidationError(f"Plik musi zawierać kolumnę: {', '.join(required_cols)}")

        errors = []
        for i, row in df.iterrows():
            location_name = str(row["Location"]).strip() if not pd.isna(row["Location"]) else None

            if not location_name or len(location_name) > 15:
                errors.append(f"BŁĄD: Lokalizacja w wierszu {i+2} przekracza 15 znaków lub jest pusta.")
                continue

            Location.objects.update_or_create(name=location_name)

        if errors:
            raise ValidationError(errors)

    def _import_scrap_codes(self):
        """
        Importuje kody ScrapCode z pliku Excel.
        - Kod musi mieć dokładnie 3 znaki.
        - Opis maksymalnie 50 znaków.
        """
        import pandas as pd
        from .models import ScrapCode  # Model ScrapCode

        try:
            df = pd.read_excel(self.file.path)
        except Exception as e:
            raise ValidationError(f"Błąd odczytu pliku Excel: {str(e)}")

        required_cols = ["Scrap Code", "Description"]
        if not all(col in df.columns for col in required_cols):
            raise ValidationError(f"Plik musi zawierać kolumny: {', '.join(required_cols)}")

        errors = []
        for i, row in df.iterrows():
            code = str(row["Scrap Code"]).strip() if not pd.isna(row["Scrap Code"]) else None
            description = str(row["Description"]).strip() if not pd.isna(row["Description"]) else None

            if not code or len(code) != 3:
                errors.append(f"BŁĄD: Kod Scrap w wierszu {i+2} musi mieć dokładnie 3 znaki.")
                continue

            if not description or len(description) > 50:
                errors.append(f"BŁĄD: Opis w wierszu {i+2} przekracza 50 znaków lub jest pusty.")
                continue

            ScrapCode.objects.update_or_create(code=code, defaults={"description": description})

        if errors:
            raise ValidationError(errors)        
    
class SupportTicket(models.Model):
    STATUS_CHOICES = [
        ("open", "🟢 Otwarte"),
        ("in_progress", "🟡 W trakcie"),
        ("closed", "🔴 Zamknięte"),
    ]

    CATEGORY_CHOICES = [
        ("technician", "Technik"),
        ("engineer", "Inżynier"),
        ("quality", "Jakość"),
    ]

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="Kategoria zgłoszenia")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Zgłoszone przez")
    workplace = models.CharField(max_length=50, verbose_name="Miejsce pracy")
    description = models.TextField(blank=True, null=True, verbose_name="Opis problemu")
    created_at = models.DateTimeField(default=now, verbose_name="Data utworzenia")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open", verbose_name="Status")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tickets", verbose_name="Przypisane do")
    taken_at = models.DateTimeField(null=True, blank=True, verbose_name="Czas podjęcia akcji")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Czas zamknięcia zgłoszenia")
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="resolved_tickets", verbose_name="Zamknięte przez")

    def __str__(self):
        return f"{self.get_category_display()} | {self.status} | {self.workplace} | {self.created_by}"

class QualityReason(models.Model):
    name = models.CharField(max_length=100, unique=True)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    workplace = models.CharField(max_length=50, verbose_name="Miejsce pracy", blank=True, null=True)

    def __str__(self):
        return f"Profil: {self.user.username}" 

    
class C2MaterialGroup(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Grupa materiałowa (np. Korpus, Płytka)")
    
    def __str__(self):
        return self.name

class C2MaterialItem(models.Model):
    group = models.ForeignKey(C2MaterialGroup, on_delete=models.CASCADE, related_name="items")
    item_code = models.CharField(max_length=50, unique=True, verbose_name="Numer itemu")
    description = models.CharField(max_length=200, blank=True, verbose_name="Opis")

    def __str__(self):
        return f"{self.item_code} - {self.description}"    

class WarehouseReason(models.Model):
    name = models.CharField(max_length=100, verbose_name="Powód zgłoszenia")

    def __str__(self):
        return self.name

class WarehouseRequest(models.Model):
    """Model zgłoszeń do magazynu"""
    LOCATION_CHOICES = [
        ("gaming", "🎮 Gaming"),
        ("c2", "⚙️ C2"),
        ("rm5", "🏭 RM5"),
        ("scancoin", "💰 ScanCoin"),
        ("comestero", "💳 Comestero"),
        ("b2b", "📦 B2B"),
    ]

    STATUS_CHOICES = [
        ("new", "🟢 Nowe"),
        ("in_progress", "🟡 W realizacji"),
        ("resolved", "🔴 Zamknięte"),
    ]

    CATEGORY_CHOICES = [
        ("raw_materials", "📦 Braki surowców"),
        ("logistics_issue", "🚚 Błąd w dostawie"),
        ("return", "🔄 Zwrot na magazyn"),
    ]

    location = models.CharField(max_length=20, choices=LOCATION_CHOICES, default="c2", verbose_name="Lokalizacja")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Zgłaszający")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="Kategoria zgłoszenia")
    warehouse_reason = models.ForeignKey(WarehouseReason, on_delete=models.SET_NULL, null=True, verbose_name="Powód zgłoszenia")
    description = models.TextField(verbose_name="Opis problemu")
    item = models.ForeignKey("Item", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Item")  # Połączenie z Item
    quantity = models.PositiveIntegerField(verbose_name="Ilość", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new", verbose_name="Status")
    created_at = models.DateTimeField(default=now, verbose_name="Data utworzenia")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Data zamknięcia")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="warehouse_tickets", verbose_name="Przypisane do")
    handled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="handled_warehouse_requests", verbose_name="Obsługujący")
    handled_at = models.DateTimeField(null=True, blank=True, verbose_name="Data obsługi")

    def __str__(self):
        return f"{self.get_category_display()} | {self.status} | {self.created_by}"
    
class WarehouseComment(models.Model):
    ticket = models.ForeignKey(WarehouseRequest, on_delete=models.CASCADE, related_name="comments", verbose_name="Zgłoszenie")
    text = models.TextField(verbose_name="Treść komentarza")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Utworzone przez")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data utworzenia")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Data edycji")  # Nowe pole
    
    quantity = models.PositiveIntegerField(verbose_name="Ilość", null=True, blank=True)  # Nowe pole
    

    def __str__(self):
        return f"Komentarz od {self.created_by} do zgłoszenia {self.ticket.id}"

class ScrapEntry(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, verbose_name="Item")
    quantity = models.PositiveIntegerField(verbose_name="Ilość")
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Zgłoszone przez")
    quality_reason = models.ForeignKey(QualityReason, on_delete=models.SET_NULL, null=True, verbose_name="Powód")
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Koszt", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data utworzenia")
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Całkowity koszt", null=True, blank=True)
    production_line = models.CharField(max_length=5, verbose_name="Linia produkcyjna", default="SC1", null=True, blank=True)
    create_warehouse_request = models.BooleanField(default=False, verbose_name="Utwórz zgłoszenie magazynowe")
    gpg = models.CharField(max_length=50, verbose_name="GPG", null=True, blank=True)
    workplace = models.CharField(max_length=50, default="ScanCoin", verbose_name="Miejsce pracy", null=True, blank=True)
    supplier = models.CharField(max_length=50, verbose_name="Dostawca", null=True, blank=True)
    description = models.TextField(verbose_name="Opis", null=True, blank=True)


    def save(self, *args, **kwargs):
        """Zapisuje zgłoszenie odpadu i opcjonalnie tworzy WarehouseRequest"""
        # Obliczamy wartość odpadu
        if self.item and self.quantity:
            self.total_cost = self.item.price * self.quantity

        # 🚀 Najpierw zapisujemy ScrapEntry do bazy
        super().save(*args, **kwargs)  

        # Jeśli checkbox jest zaznaczony, tworzymy WarehouseRequest
        if self.create_warehouse_request:
            WarehouseRequest = apps.get_model('core', 'WarehouseRequest')  # 🔹 Lazy import modelu
            WarehouseRequest.objects.create(
                location=self.production_line,  
                created_by=self.reported_by,
                category="return",  
                warehouse_reason=None,  
                description=f"Automatycznie utworzone ze zgłoszenia odpadu: {self.item}",
                item=self.item,
                quantity=self.quantity,
                status="new",
            )

    def __str__(self):
        return f"{self.item.item_code} - {self.quantity} szt."

class ProductionOrder(models.Model):
    mo_number = models.CharField(max_length=50, unique=True, verbose_name="Numer MO")
    item = models.ForeignKey("Item", on_delete=models.CASCADE, verbose_name="Item", null=True)
    mo_quantity = models.PositiveIntegerField(verbose_name="Całkowita ilość MO")  # Całkowita ilość MO
    produced_quantity = models.PositiveIntegerField(default=0, verbose_name="Ilość wykonana")  # Faktycznie wyprodukowane
    status = models.CharField(
        max_length=20,
        choices=[
            ("new", "Nowe"),
            ("in_progress", "W realizacji"),
            ("wip", "WIP"),
            ("printed", "Wydrukowane"),
            ("completed", "Zakończone"),
            ("stopped", "Zatrzymane"),
        ],
        verbose_name="Status zlecenia",
        default="new",
    )
    production_line = models.CharField(max_length=5, verbose_name="Linia produkcyjna", null=True, blank=True)
    created_at = models.DateTimeField(default=now, verbose_name="Data dodania")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Data zakończenia")

    def __str__(self):
        return f"MO {self.mo_number} | {self.status}"

class ProductionPlan(models.Model):
    production_order = models.ForeignKey(
        ProductionOrder, on_delete=models.CASCADE, related_name="plans", verbose_name="Zlecenie MO"
    )
    production_line = models.CharField(max_length=5, verbose_name="Linia produkcyjna", default="SC1")
    date = models.DateField(null=True, blank=True, verbose_name="Data zaplanowana")  # Dla linii C2 i RM5
    planned_week = models.PositiveIntegerField(null=True, blank=True, verbose_name="Zaplanowany tydzień")  # Dla innych linii
    planned_quantity = models.PositiveIntegerField(verbose_name="Ilość zaplanowana", default=0)  # Ilość na dzień/tydzień
    planned_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=100.0, verbose_name="Procent realizacji"
    )
    created_at = models.DateTimeField(default=now, verbose_name="Data przypisania")

    def __str__(self):
        if self.date:
            return f"Plan: {self.production_order.mo_number} na {self.date}"
        return f"Plan: {self.production_order.mo_number} na tydzień {self.planned_week}"

class ProductionComment(models.Model):
    production_plan = models.ForeignKey("ProductionPlan", related_name="comments", on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on ProductionPlan {self.production_order.id}"

class ProductionLog(models.Model):
    # Data, której dotyczy wykonanie
    date = models.DateField()

    # Numer MO - można też łączyć z ProductionPlan, 
    # ale często MO jest tylko kluczem tekstowym
    mo_number = models.CharField(max_length=50)

    # Item - jeżeli chcesz relację do Item, 
    # można dać ForeignKey do Item, albo przechowywać samego stringa
    item_code = models.CharField(max_length=50)

    # Ilość wykonana danego dnia
    quantity = models.PositiveIntegerField()

    # Dodatkowo linia, GPG, user, itp. – jeśli chcesz
    # lub można je automatycznie wnioskować z ProductionPlan
    # ...
    
    class Meta:
        # ewentualnie ordering
        ordering = ["-date"]

    def __str__(self):
        return f"ProductionLog {self.mo_number} on {self.date} = {self.quantity}"

class Location(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class CycleCountRequest(models.Model):
    STATUS_CHOICES = [
        ("new", "Nowe"),
        ("review", "W trakcie"),
        ("closed", "Zakończone"),
        ("removed", "Usunięte"),
    ]

    item = models.ForeignKey(Item, on_delete=models.CASCADE, verbose_name="Item")
    location = models.ForeignKey(Location, on_delete=models.CASCADE, verbose_name="Lokalizacja")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Zgłaszający")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    physical_qty = models.PositiveIntegerField(verbose_name="Ilość fizyczna")
    system_qty = models.PositiveIntegerField(verbose_name="Ilość systemowa")
    comment = models.TextField(blank=True, verbose_name="Komentarz")
      # Nowe pola:
    closed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="closed_cycle_requests",
        verbose_name="Zamknięte przez"
    )
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="Data zamknięcia")


    def __str__(self):
        return f"Zgłoszenie inwentaryzacji {self.location} ({self.get_status_display()})"

class ScrapCode(models.Model):
    code = models.CharField(max_length=3, unique=True, verbose_name="Kod złomu")
    description = models.CharField(max_length=255, verbose_name="Opis")
    def __str__(self):
        return f"{self.code} - {self.description}"

class InvRequest(models.Model):
    STATUS_CHOICES = [
        ("awaiting_magazyn",  "W trakcie: Magazyn"),
        ("awaiting_dyrektor", "W trakcie: Dyrektor"),
        ("awaiting_cycle",    "W trakcie: Cycle Count"),
        ("approved",          "Zatwierdzony"),
        ("rejected",          "Odrzucony"),
        ("cancelled",         "Anulowany"),
    ]

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, 
        null=True, related_name="inv_requests"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default="awaiting_magazyn"
    )

    # Jeśli chcesz przechowywać, kto i kiedy zatwierdził *ostatni* krok:
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name="inv_requests_approved"
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    rejected_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name="inv_requests_rejected"
    )
    rejected_at = models.DateTimeField(null=True, blank=True)

    def total_value(self) -> float:
        """
        Zwraca sumę wartości wszystkich pozycji (ilość * cena).
        Uwaga, jeśli quantity może być ujemne.
        """
        return sum(line.line_value() for line in self.lines.all())

    def __str__(self):
        return f"Inwentaryzacja #{self.id} [{self.get_status_display()}]"

class InvRequestLine(models.Model):
    request = models.ForeignKey(
        InvRequest, on_delete=models.CASCADE, 
        related_name="lines"
    )
    item = models.ForeignKey("Item", on_delete=models.CASCADE)
    quantity = models.IntegerField(
        help_text="Może być ujemna dla zdjęcia stanu"
    )
    location = models.ForeignKey("Location", on_delete=models.PROTECT)
    scrap_code = models.ForeignKey("ScrapCode", on_delete=models.PROTECT)

    def line_value(self):
        """Zwraca (quantity * item.price). Może być ujemne."""
        if self.item and self.item.price:
            return float(self.quantity) * float(self.item.price) * -1
        return 0.0

    def __str__(self):
        return f"{self.item.item_code} ({self.quantity} szt.)"
    
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    created_at = models.DateTimeField(default=now)
    read = models.BooleanField(default=False)
    url = models.URLField(null=True, blank=True)  # Dodaj to pole, jeśli go brakuje

    def __str__(self):
        return f"Notification for {self.user.username} - {self.message[:20]}..."