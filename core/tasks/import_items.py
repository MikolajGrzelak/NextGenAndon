import os
import pandas as pd
from decimal import Decimal
from django.core.exceptions import ValidationError
from models import Item

FILE_PATH = "/var/data/items.xlsx"  # Lokalizacja pliku

def import_items():
    if not os.path.exists(FILE_PATH):
        print(f"Plik {FILE_PATH} nie istnieje.")
        return
    
    try:
        df = pd.read_excel(FILE_PATH)
    except Exception as e:
        raise ValidationError(f"Błąd podczas odczytu pliku Excel: {str(e)}")

    required_cols = ["Item", "Description", "Supplier", "Responsible", "Price", "ProductionTime"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValidationError(f"Brak wymaganych kolumn: {', '.join(missing_cols)}")

    for i, row in df.iterrows():
        try:
            item_code = str(row["Item"]).strip() if not pd.isna(row["Item"]) else None
            if not item_code:
                continue  

            description = row.get("Description", "")
            supplier = row.get("Supplier", "")
            responsible = row.get("Responsible", "")
            price = row.get("Price", 0)
            production_time = row.get("ProductionTime", 0)
            gpg = row.get("GPG", "")
            production_line = row.get("ProductionLine", "")

            price_value = Decimal(str(price).replace(',', '.')) if price else Decimal("0.00")
            production_time_value = Decimal(str(production_time).replace(',', '.')) if production_time else Decimal("0.00")

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
            print(f"Błąd w wierszu {i+2}: {e}")

    print("Import zakończony sukcesem.")
