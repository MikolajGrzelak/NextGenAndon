from django import forms
from .models import ScrapEntry, Item, Location, ScrapCode, CycleCountRequest

class ScrapEntryForm(forms.ModelForm):
    item_code = forms.CharField(label="Numer Itemu", max_length=50, required=True)
    quantity = forms.IntegerField(label="Ilość", min_value=1, required=True)

    class Meta:
        model = ScrapEntry
        fields = ["item", "quantity", "quality_reason", "create_warehouse_request"]
        widgets = {
            "item": forms.Select(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control"}),
            "quality_reason": forms.Select(attrs={"class": "form-control"}),
            "create_warehouse_request": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_item_code(self):
        item_code = self.cleaned_data.get("item_code")
        try:
            item = Item.objects.get(item_code=item_code)
        except Item.DoesNotExist:
            raise forms.ValidationError("Nie znaleziono itemu o podanym numerze.")
        return item_code

    def save(self, commit=True):
        item_code = self.cleaned_data.get("item_code")
        quantity = self.cleaned_data.get("quantity")
        item = Item.objects.get(item_code=item_code)
        scrap_entry = ScrapEntry(item=item, quantity=quantity)
        if commit:
            scrap_entry.save()
        return scrap_entry

class CycleCountRequestForm(forms.ModelForm):
    """
    Formularz do zgłaszania wniosków o przeliczenie stanów magazynowych.
    """
    class Meta:
        model = CycleCountRequest
        fields = ["item", "location", "system_qty", "physical_qty", "comment"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["location"].queryset = Location.objects.all()
        self.fields["item"].queryset = Item.objects.all()

class ExcelUploadForm(forms.Form):
    file = forms.FileField(label="Wybierz plik Excel")
