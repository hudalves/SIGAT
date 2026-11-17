from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "inventario"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="inventario:planta"), name="home"),
    path("planta/", views.PlantaView.as_view(), name="planta"),
    path("ambientes/", views.AmbienteListView.as_view(), name="ambiente_lista"),
    path("ambientes/<int:pk>/editar/", views.AmbienteUpdateView.as_view(), name="ambiente_editar"),
    path("ambientes/novo/", views.AmbienteCreateView.as_view(), name="ambiente_novo"),
    path("equipamentos/", views.EquipamentoListView.as_view(), name="equipamento_lista"),
    path("equipamentos/novo/", views.EquipamentoCreateView.as_view(), name="equipamento_novo"),
    path("equipamentos/<int:pk>/", views.EquipamentoDetailView.as_view(), name="equipamento_detalhe"),
    path("equipamentos/<int:pk>/editar/", views.EquipamentoUpdateView.as_view(), name="equipamento_editar"),
    path("equipamentos/<int:pk>/inativar/", views.EquipamentoInativarView.as_view(), name="equipamento_inativar"),
]
