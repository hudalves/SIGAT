import csv
import json

from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from .forms import AmbienteForm, EquipamentoForm
from .models import Ambiente, Equipamento


def filtrar_equipamentos(params):
    """Filtro único usado pela lista e pela exportação CSV (busca, categoria e inativos)."""
    qs = Equipamento.objects.select_related("ambiente")
    q = params.get("q", "").strip()
    categoria = params.get("categoria", "")
    if q:
        qs = qs.filter(
            Q(patrimonio__icontains=q)
            | Q(nome__icontains=q)
            | Q(modelo__icontains=q)
            | Q(categoria__icontains=q)
        )
    if categoria:
        qs = qs.filter(categoria=categoria)
    if not params.get("inativos"):
        qs = qs.exclude(status=Equipamento.Status.INATIVO)
    return qs


class AmbienteListView(ListView):
    model = Ambiente
    template_name = "inventario/ambiente_lista.html"
    context_object_name = "ambientes"


class AmbienteCreateView(CreateView):
    model = Ambiente
    form_class = AmbienteForm
    template_name = "inventario/form.html"
    success_url = reverse_lazy("inventario:ambiente_lista")
    extra_context = {"titulo": "Novo ambiente"}

    def form_valid(self, form):
        messages.success(self.request, "Ambiente cadastrado com sucesso.")
        return super().form_valid(form)


class AmbienteUpdateView(UpdateView):
    model = Ambiente
    form_class = AmbienteForm
    template_name = "inventario/form.html"
    success_url = reverse_lazy("inventario:ambiente_lista")
    extra_context = {"titulo": "Editar ambiente"}

    def form_valid(self, form):
        messages.success(self.request, "Ambiente atualizado.")
        return super().form_valid(form)


class PlantaView(TemplateView):
    """Função principal: planta 2D interativa (ambientes e equipamentos posicionáveis)."""

    template_name = "inventario/planta.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ambientes = []
        sem_posicao = 0
        for a in Ambiente.objects.all():
            if None in (a.planta_x, a.planta_y, a.planta_largura, a.planta_altura):
                i = sem_posicao
                sem_posicao += 1
                x, y, w, h = 2 + (i % 3) * 33, 2 + (i // 3) * 32, 30, 28
            else:
                x, y, w, h = a.planta_x, a.planta_y, a.planta_largura, a.planta_altura
            ambientes.append({"id": a.pk, "nome": a.nome, "tipo": a.get_tipo_display(), "x": x, "y": y, "w": w, "h": h})

        equipamentos = [
            {
                "id": e.pk,
                "patrimonio": e.patrimonio,
                "nome": e.nome,
                "fabricante": e.fabricante,
                "modelo": e.modelo,
                "numero_serie": e.numero_serie,
                "observacoes": e.observacoes,
                "categoria": e.categoria,
                "categoria_label": e.get_categoria_display(),
                "status_label": e.get_status_display(),
                "ambiente": e.ambiente_id,
                "x": e.planta_x,
                "y": e.planta_y,
                "url": e.get_absolute_url(),
            }
            for e in Equipamento.objects.exclude(status=Equipamento.Status.INATIVO).order_by("patrimonio")
        ]
        ctx["dados"] = {
            "ambientes": ambientes,
            "equipamentos": equipamentos,
            "categorias": [list(c) for c in Equipamento.Categoria.choices],
            "urls": {
                "ambiente": reverse("inventario:planta_ambiente_pos", args=[0]),
                "equipamento": reverse("inventario:planta_equipamento_pos", args=[0]),
            },
        }
        return ctx


def _json_body(request):
    try:
        return json.loads(request.body or b"{}")
    except (ValueError, TypeError):
        return None


@require_POST
def planta_ambiente_posicao(request, pk):
    """Salva posição e tamanho do ambiente na planta (em %)."""
    ambiente = get_object_or_404(Ambiente, pk=pk)
    corpo = _json_body(request)
    try:
        x, y, w, h = (int(round(float(corpo[k]))) for k in ("x", "y", "largura", "altura"))
    except (TypeError, KeyError, ValueError):
        return JsonResponse({"erro": "dados inválidos"}, status=400)
    if w < 5 or h < 5 or x < 0 or y < 0 or x + w > 100 or y + h > 100:
        return JsonResponse({"erro": "posição fora da planta"}, status=400)
    ambiente.planta_x, ambiente.planta_y, ambiente.planta_largura, ambiente.planta_altura = x, y, w, h
    ambiente.save(update_fields=["planta_x", "planta_y", "planta_largura", "planta_altura"])
    return JsonResponse({"ok": True})


@require_POST
def planta_equipamento_posicao(request, pk):
    """Salva a posição do equipamento dentro do ambiente; se vier 'ambiente', atualiza a localização."""
    equipamento = get_object_or_404(Equipamento, pk=pk)
    corpo = _json_body(request)
    try:
        x, y = float(corpo["x"]), float(corpo["y"])
    except (TypeError, KeyError, ValueError):
        return JsonResponse({"erro": "dados inválidos"}, status=400)
    if not (0 <= x <= 100 and 0 <= y <= 100):
        return JsonResponse({"erro": "posição fora do ambiente"}, status=400)
    campos = ["planta_x", "planta_y", "atualizado_em"]
    if corpo.get("ambiente") is not None:
        try:
            equipamento.ambiente = Ambiente.objects.get(pk=int(corpo["ambiente"]))
        except (TypeError, ValueError, Ambiente.DoesNotExist):
            return JsonResponse({"erro": "ambiente inválido"}, status=400)
        campos.append("ambiente")
    equipamento.planta_x, equipamento.planta_y = x, y
    equipamento.save(update_fields=campos)
    return JsonResponse({"ok": True})


class EquipamentoListView(ListView):
    """US03 — lista com busca por identificação, nome/modelo ou categoria."""

    model = Equipamento
    template_name = "inventario/equipamento_lista.html"
    context_object_name = "equipamentos"
    paginate_by = 20

    def get_queryset(self):
        return filtrar_equipamentos(self.request.GET)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["categoria_sel"] = self.request.GET.get("categoria", "")
        ctx["inativos"] = bool(self.request.GET.get("inativos"))
        ctx["categorias"] = Equipamento.Categoria.choices
        return ctx


class EquipamentoDetailView(DetailView):
    model = Equipamento
    template_name = "inventario/equipamento_detalhe.html"
    context_object_name = "equipamento"


class EquipamentoCreateView(CreateView):
    model = Equipamento
    form_class = EquipamentoForm
    template_name = "inventario/form.html"
    extra_context = {"titulo": "Novo equipamento"}

    def form_valid(self, form):
        messages.success(self.request, "Equipamento cadastrado com sucesso.")
        return super().form_valid(form)


class EquipamentoUpdateView(UpdateView):
    model = Equipamento
    form_class = EquipamentoForm
    template_name = "inventario/form.html"
    extra_context = {"titulo": "Editar equipamento"}

    def form_valid(self, form):
        messages.success(self.request, "Equipamento atualizado.")
        return super().form_valid(form)


class EquipamentoInativarView(View):
    """US04 — inativa com confirmação; não há exclusão física."""

    template_name = "inventario/equipamento_inativar.html"

    def get(self, request, pk):
        from django.shortcuts import render

        equipamento = get_object_or_404(Equipamento, pk=pk)
        return render(request, self.template_name, {"equipamento": equipamento})

    def post(self, request, pk):
        equipamento = get_object_or_404(Equipamento, pk=pk)
        equipamento.status = Equipamento.Status.INATIVO
        equipamento.save(update_fields=["status", "atualizado_em"])
        messages.success(request, f"{equipamento.patrimonio} foi inativado (o registro foi mantido).")
        return redirect("inventario:equipamento_lista")


CSV_COLUNAS = [
    "Patrimônio", "Nome", "Categoria", "Fabricante", "Modelo",
    "Número de série", "Status", "Ambiente", "Observações",
]


def _celula_segura(valor):
    """Evita injeção de fórmula ao abrir no Excel (células que começam com = + - @)."""
    texto = "" if valor is None else str(valor)
    return "'" + texto if texto[:1] in ("=", "+", "-", "@", "\t", "\r") else texto


def exportar_csv(request):
    """US10 — exporta o inventário em CSV (abre direto no Excel), respeitando os filtros da lista."""
    resposta = HttpResponse(content_type="text/csv; charset=utf-8")
    nome = f"inventario_sigat_{timezone.localdate():%Y-%m-%d}.csv"
    resposta["Content-Disposition"] = f'attachment; filename="{nome}"'
    resposta.write("\ufeff")  # BOM: o Excel reconhece acentos corretamente
    escritor = csv.writer(resposta, delimiter=";")  # ';' é o separador padrão do Excel em pt-BR
    escritor.writerow(CSV_COLUNAS)
    for e in filtrar_equipamentos(request.GET).order_by("patrimonio"):
        escritor.writerow([
            _celula_segura(v)
            for v in (
                e.patrimonio, e.nome, e.get_categoria_display(), e.fabricante, e.modelo,
                e.numero_serie, e.get_status_display(), e.ambiente.nome, e.observacoes,
            )
        ])
    return resposta
