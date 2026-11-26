from django import forms

from django.utils import timezone

from .models import Ambiente, Equipamento, Manutencao


class AmbienteForm(forms.ModelForm):
    class Meta:
        model = Ambiente
        fields = ["nome", "tipo", "descricao", "planta_x", "planta_y", "planta_largura", "planta_altura"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "planta_x": forms.NumberInput(attrs={"min": 0, "max": 100}),
            "planta_y": forms.NumberInput(attrs={"min": 0, "max": 100}),
            "planta_largura": forms.NumberInput(attrs={"min": 5, "max": 100}),
            "planta_altura": forms.NumberInput(attrs={"min": 5, "max": 100}),
        }
        help_texts = {
            "planta_x": "Opcional. Deixe os 4 campos da planta em branco para posicionar automaticamente.",
        }

    def clean(self):
        data = super().clean()
        campos = [data.get(k) for k in ("planta_x", "planta_y", "planta_largura", "planta_altura")]
        if any(v is not None for v in campos):
            if any(v is None for v in campos):
                raise forms.ValidationError(
                    "Para posicionar na planta, preencha posição X, Y, largura e altura (ou deixe os quatro em branco)."
                )
            x, y, w, h = campos
            if w < 5 or h < 5:
                raise forms.ValidationError("Largura e altura mínimas na planta: 5%.")
            if x + w > 100 or y + h > 100:
                raise forms.ValidationError("O ambiente passa da borda da planta: X + largura e Y + altura devem ser até 100.")
        return data

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


class ManutencaoForm(forms.ModelForm):
    """US08 — data, problema, ação executada e observação."""

    class Meta:
        model = Manutencao
        fields = ["data", "problema", "acao", "observacao"]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "problema": forms.Textarea(attrs={"rows": 3}),
            "acao": forms.Textarea(attrs={"rows": 3}),
            "observacao": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.fields["data"].initial = timezone.localdate

    def clean_data(self):
        data = self.cleaned_data["data"]
        if data > timezone.localdate():
            raise forms.ValidationError("A data da manutenção não pode estar no futuro.")
        return data

    def clean_problema(self):
        texto = self.cleaned_data["problema"].strip()
        if not texto:
            raise forms.ValidationError("Descreva o problema.")
        return texto

    def clean_acao(self):
        texto = self.cleaned_data["acao"].strip()
        if not texto:
            raise forms.ValidationError("Informe a ação executada.")
        return texto


class MovimentacaoForm(forms.Form):
    """US09 — escolher o novo ambiente (o atual não é oferecido)."""

    destino = forms.ModelChoiceField(queryset=Ambiente.objects.all(), label="Novo ambiente", empty_label="Selecione…")
    observacao = forms.CharField(label="Observação", required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, equipamento, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["destino"].queryset = Ambiente.objects.exclude(pk=equipamento.ambiente_id)
