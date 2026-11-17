from django.contrib import admin

from .models import Ambiente, Equipamento


@admin.register(Ambiente)
class AmbienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo")
    search_fields = ("nome",)


@admin.register(Equipamento)
class EquipamentoAdmin(admin.ModelAdmin):
    list_display = ("patrimonio", "nome", "categoria", "modelo", "status", "ambiente")
    list_filter = ("categoria", "status", "ambiente")
    search_fields = ("patrimonio", "nome", "modelo", "numero_serie")
