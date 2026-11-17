import json

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


class PlantaTests(TestCase):  # função principal: planta 2D interativa
    def setUp(self):
        self.amb = Ambiente.objects.create(
            nome="Recepcao", tipo="setor", planta_x=5, planta_y=10, planta_largura=40, planta_altura=40
        )
        self.outro = Ambiente.objects.create(nome="Sala TI", tipo="sala", planta_x=50, planta_y=10, planta_largura=40, planta_altura=40)
        self.eq = Equipamento.objects.create(**{**dados_equipamento(self.amb), "ambiente": self.amb, "patrimonio": "CA10"})

    def post_json(self, url, corpo):
        return self.client.post(url, data=json.dumps(corpo), content_type="application/json")

    def test_planta_entrega_dados_de_ambientes_e_equipamentos(self):
        resp = self.client.get(reverse("inventario:planta"))
        self.assertEqual(resp.status_code, 200)
        dados = resp.context["dados"]
        self.assertEqual({a["nome"] for a in dados["ambientes"]}, {"Recepcao", "Sala TI"})
        self.assertEqual([e["patrimonio"] for e in dados["equipamentos"]], ["CA10"])
        self.assertContains(resp, 'id="planta"')

    def test_planta_nao_inclui_inativos(self):
        self.eq.status = Equipamento.Status.INATIVO
        self.eq.save()
        resp = self.client.get(reverse("inventario:planta"))
        self.assertEqual(resp.context["dados"]["equipamentos"], [])

    def test_ambiente_sem_posicao_recebe_posicao_automatica(self):
        Ambiente.objects.create(nome="Deposito", tipo="deposito")
        resp = self.client.get(reverse("inventario:planta"))
        dep = [a for a in resp.context["dados"]["ambientes"] if a["nome"] == "Deposito"][0]
        self.assertIsNotNone(dep["x"])
        self.assertGreaterEqual(dep["w"], 5)

    def test_salva_posicao_do_ambiente(self):
        url = reverse("inventario:planta_ambiente_pos", args=[self.amb.pk])
        resp = self.post_json(url, {"x": 10, "y": 20, "largura": 30, "altura": 25})
        self.assertEqual(resp.status_code, 200)
        self.amb.refresh_from_db()
        self.assertEqual((self.amb.planta_x, self.amb.planta_y, self.amb.planta_largura, self.amb.planta_altura), (10, 20, 30, 25))

    def test_rejeita_posicao_do_ambiente_fora_da_planta(self):
        url = reverse("inventario:planta_ambiente_pos", args=[self.amb.pk])
        self.assertEqual(self.post_json(url, {"x": 80, "y": 20, "largura": 40, "altura": 25}).status_code, 400)
        self.assertEqual(self.post_json(url, {"x": "a"}).status_code, 400)

    def test_salva_posicao_do_equipamento(self):
        url = reverse("inventario:planta_equipamento_pos", args=[self.eq.pk])
        resp = self.post_json(url, {"x": 40.5, "y": 60})
        self.assertEqual(resp.status_code, 200)
        self.eq.refresh_from_db()
        self.assertEqual((self.eq.planta_x, self.eq.planta_y), (40.5, 60))
        self.assertEqual(self.eq.ambiente, self.amb)

    def test_mover_equipamento_para_outro_ambiente_atualiza_localizacao(self):
        url = reverse("inventario:planta_equipamento_pos", args=[self.eq.pk])
        resp = self.post_json(url, {"x": 30, "y": 30, "ambiente": self.outro.pk})
        self.assertEqual(resp.status_code, 200)
        self.eq.refresh_from_db()
        self.assertEqual(self.eq.ambiente, self.outro)

    def test_rejeita_posicao_invalida_do_equipamento(self):
        url = reverse("inventario:planta_equipamento_pos", args=[self.eq.pk])
        self.assertEqual(self.post_json(url, {"x": 150, "y": 10}).status_code, 400)
        self.assertEqual(self.post_json(url, {"x": 10, "y": 10, "ambiente": 9999}).status_code, 400)

    def test_endpoints_de_posicao_aceitam_apenas_post(self):
        self.assertEqual(self.client.get(reverse("inventario:planta_equipamento_pos", args=[self.eq.pk])).status_code, 405)

    def test_valida_posicao_fora_da_planta_no_formulario(self):
        resp = self.client.post(reverse("inventario:ambiente_novo"), {
            "nome": "Fora", "tipo": "sala", "descricao": "",
            "planta_x": 80, "planta_y": 10, "planta_largura": 40, "planta_altura": 20,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Ambiente.objects.filter(nome="Fora").exists())

    def test_posicao_incompleta_e_rejeitada_no_formulario(self):
        resp = self.client.post(reverse("inventario:ambiente_novo"), {
            "nome": "Parcial", "tipo": "sala", "descricao": "", "planta_x": 10,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Ambiente.objects.filter(nome="Parcial").exists())
