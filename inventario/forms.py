from django import forms

from .models import Ambiente, Equipamento


class AmbienteForm(forms.ModelForm):
    class Meta:
        model = Ambiente
        fields = ["nome", "tipo", "descricao"]
        widgets = {"descricao": forms.Textarea(attrs={"rows": 3})}

    def clean_nome(self):
        nome = self.cleaned_data["nome"].strip()
        if not nome:
            raise forms.ValidationError("Informe o nome do ambiente.")
        return nome


class EquipamentoForm(forms.ModelForm):
    class Meta:
        model = Equipamento
        fields = [
            "patrimonio", "nome", "categoria", "fabricante", "modelo",
            "numero_serie", "status", "ambiente", "observacoes",
        ]
        widgets = {"observacoes": forms.Textarea(attrs={"rows": 3})}

    def clean_patrimonio(self):
        patrimonio = self.cleaned_data["patrimonio"].strip().upper()
        if not patrimonio:
            raise forms.ValidationError("Informe a identificação/patrimônio.")
        return patrimonio
