from django.test import TestCase
from django.urls import reverse

from .models import Ambiente, Equipamento


def criar_ambiente(nome="Atendimento 1"):
    return Ambiente.objects.create(nome=nome, tipo=Ambiente.Tipo.ATENDIMENTO)


def dados_equipamento(ambiente, **extra):
    dados = {
        "patrimonio": "ca01",
        "nome": "PC Balcão",
        "categoria": Equipamento.Categoria.COMPUTADOR,
        "fabricante": "Dell",
        "modelo": "OptiPlex 3080",
        "numero_serie": "ABC123",
        "status": Equipamento.Status.EM_USO,
        "ambiente": ambiente.pk,
        "observacoes": "",
    }
    dados.update(extra)
    return dados


class AmbienteTests(TestCase):  # US01
    def test_cadastra_ambiente(self):
        resp = self.client.post(reverse("inventario:ambiente_novo"), {"nome": "Recepção", "tipo": "setor", "descricao": ""})
        self.assertRedirects(resp, reverse("inventario:ambiente_lista"))
        self.assertTrue(Ambiente.objects.filter(nome="Recepção").exists())

    def test_impede_nome_vazio(self):
        resp = self.client.post(reverse("inventario:ambiente_novo"), {"nome": "   ", "tipo": "setor", "descricao": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Ambiente.objects.count(), 0)

    def test_lista_ambientes(self):
        criar_ambiente("Sala TI")
        resp = self.client.get(reverse("inventario:ambiente_lista"))
        self.assertContains(resp, "Sala TI")


class EquipamentoTests(TestCase):  # US02, US03, US04
    def setUp(self):
        self.amb = criar_ambiente()

    def test_cadastra_equipamento_e_normaliza_patrimonio(self):
        resp = self.client.post(reverse("inventario:equipamento_novo"), dados_equipamento(self.amb))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Equipamento.objects.get().patrimonio, "CA01")

    def test_campos_obrigatorios(self):
        resp = self.client.post(reverse("inventario:equipamento_novo"), dados_equipamento(self.amb, modelo=""))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Equipamento.objects.count(), 0)

    def test_patrimonio_unico(self):
        self.client.post(reverse("inventario:equipamento_novo"), dados_equipamento(self.amb))
        self.client.post(reverse("inventario:equipamento_novo"), dados_equipamento(self.amb))
        self.assertEqual(Equipamento.objects.count(), 1)

    def test_busca_por_patrimonio_modelo_e_categoria(self):
        self.client.post(reverse("inventario:equipamento_novo"), dados_equipamento(self.amb))
        url = reverse("inventario:equipamento_lista")
        for termo in ("CA01", "optiplex", "computador"):
            self.assertContains(self.client.get(url, {"q": termo}), "CA01")
        self.assertNotContains(self.client.get(url, {"q": "impressora"}), "CA01")

    def test_edita_equipamento(self):
        eq = Equipamento.objects.create(**{**dados_equipamento(self.amb), "ambiente": self.amb, "patrimonio": "CA02"})
        dados = dados_equipamento(self.amb, patrimonio="CA02", modelo="Novo Modelo")
        self.client.post(reverse("inventario:equipamento_editar", args=[eq.pk]), dados)
        eq.refresh_from_db()
        self.assertEqual(eq.modelo, "Novo Modelo")

    def test_inativar_exige_confirmacao_e_nao_exclui(self):
        eq = Equipamento.objects.create(**{**dados_equipamento(self.amb), "ambiente": self.amb, "patrimonio": "CA03"})
        url = reverse("inventario:equipamento_inativar", args=[eq.pk])
        self.assertContains(self.client.get(url), "Confirmar")  # GET só mostra a confirmação
        eq.refresh_from_db()
        self.assertFalse(eq.esta_inativo)
        self.client.post(url)
        eq.refresh_from_db()
        self.assertTrue(eq.esta_inativo)
        self.assertEqual(Equipamento.objects.count(), 1)  # registro mantido

    def test_inativos_ficam_ocultos_por_padrao(self):
        Equipamento.objects.create(**{**dados_equipamento(self.amb), "ambiente": self.amb, "patrimonio": "CA04", "status": "inativo"})
        url = reverse("inventario:equipamento_lista")
        self.assertNotContains(self.client.get(url), "CA04")
        self.assertContains(self.client.get(url, {"inativos": "1"}), "CA04")
