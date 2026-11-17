from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from .forms import AmbienteForm, EquipamentoForm
from .models import Ambiente, Equipamento


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


class EquipamentoListView(ListView):
    """US03 — lista com busca por identificação, nome/modelo ou categoria."""

    model = Equipamento
    template_name = "inventario/equipamento_lista.html"
    context_object_name = "equipamentos"
    paginate_by = 20

    def get_queryset(self):
        qs = Equipamento.objects.select_related("ambiente")
        q = self.request.GET.get("q", "").strip()
        categoria = self.request.GET.get("categoria", "")
        if q:
            qs = qs.filter(
                Q(patrimonio__icontains=q)
                | Q(nome__icontains=q)
                | Q(modelo__icontains=q)
                | Q(categoria__icontains=q)
            )
        if categoria:
            qs = qs.filter(categoria=categoria)
        if not self.request.GET.get("inativos"):
            qs = qs.exclude(status=Equipamento.Status.INATIVO)
        return qs

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
