from django.contrib import admin

from .models import Ambiente, Equipamento, Manutencao, Movimentacao


@admin.register(Ambiente)
class AmbienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo")
    search_fields = ("nome",)


@admin.register(Equipamento)
class EquipamentoAdmin(admin.ModelAdmin):
    list_display = ("patrimonio", "nome", "categoria", "modelo", "status", "ambiente")
    list_filter = ("categoria", "status", "ambiente")
    search_fields = ("patrimonio", "nome", "modelo", "numero_serie")


@admin.register(Manutencao)
class ManutencaoAdmin(admin.ModelAdmin):
    list_display = ("equipamento", "data", "problema")
    search_fields = ("equipamento__patrimonio", "problema")


@admin.register(Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = ("equipamento", "origem", "destino", "data")
