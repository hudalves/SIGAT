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


class ExportarCsvTests(TestCase):  # US10
    def setUp(self):
        self.amb = criar_ambiente("Recepção")
        Equipamento.objects.create(**{**dados_equipamento(self.amb), "ambiente": self.amb, "patrimonio": "CA01"})
        Equipamento.objects.create(**{
            **dados_equipamento(self.amb), "ambiente": self.amb, "patrimonio": "CA02",
            "categoria": Equipamento.Categoria.MONITOR, "modelo": "24MK430H", "nome": "=1+1",
        })
        Equipamento.objects.create(**{
            **dados_equipamento(self.amb), "ambiente": self.amb, "patrimonio": "CA03", "status": "inativo",
        })

    def baixar(self, **params):
        resp = self.client.get(reverse("inventario:equipamento_csv"), params)
        self.assertEqual(resp.status_code, 200)
        return resp, resp.content.decode("utf-8-sig").splitlines()

    def test_cabecalho_bom_e_tipo_de_arquivo(self):
        resp, linhas = self.baixar()
        self.assertTrue(resp.content.startswith(b"\xef\xbb\xbf"))  # BOM para o Excel
        self.assertIn("text/csv", resp["Content-Type"])
        self.assertIn("attachment", resp["Content-Disposition"])
        self.assertTrue(linhas[0].startswith("Patrimônio;Nome;Categoria"))

    def test_exporta_ativos_e_oculta_inativos_por_padrao(self):
        _, linhas = self.baixar()
        texto = "\n".join(linhas)
        self.assertIn("CA01", texto)
        self.assertIn("Recepção", texto)
        self.assertNotIn("CA03", texto)

    def test_inclui_inativos_quando_pedido(self):
        _, linhas = self.baixar(inativos="1")
        self.assertIn("CA03", "\n".join(linhas))

    def test_respeita_busca_e_categoria(self):
        _, linhas = self.baixar(q="24MK")
        self.assertEqual(len(linhas), 2)  # cabeçalho + 1 linha
        _, linhas = self.baixar(categoria="monitor")
        self.assertEqual(len(linhas), 2)

    def test_protege_contra_injecao_de_formula(self):
        _, linhas = self.baixar(q="CA02")
        self.assertIn("'=1+1", linhas[1])


class CriteriosPlantaTests(TestCase):  # critérios de aceite US05, US06 e US07
    def setUp(self):
        self.amb = Ambiente.objects.create(nome="Recepção", tipo="setor", planta_x=5, planta_y=10, planta_largura=40, planta_altura=40)
        self.vazio = Ambiente.objects.create(nome="Depósito", tipo="deposito", planta_x=50, planta_y=10, planta_largura=40, planta_altura=40)
        self.eq = Equipamento.objects.create(**{
            **dados_equipamento(self.amb), "ambiente": self.amb, "patrimonio": "CA20",
            "numero_serie": "SN-XYZ-99", "observacoes": "Teclado trocado em outubro",
        })

    def test_us05_planta_identifica_ambientes_e_ambiente_sem_ativos(self):
        dados = self.client.get(reverse("inventario:planta")).context["dados"]
        nomes = {a["nome"] for a in dados["ambientes"]}
        self.assertEqual(nomes, {"Recepção", "Depósito"})
        deposito = [a for a in dados["ambientes"] if a["nome"] == "Depósito"][0]
        self.assertEqual([e for e in dados["equipamentos"] if e["ambiente"] == deposito["id"]], [])

    def test_us06_ativos_do_ambiente_com_link_para_a_ficha(self):
        dados = self.client.get(reverse("inventario:planta")).context["dados"]
        itens = [e for e in dados["equipamentos"] if e["ambiente"] == self.amb.pk]
        self.assertEqual([e["patrimonio"] for e in itens], ["CA20"])
        self.assertEqual(itens[0]["url"], reverse("inventario:equipamento_detalhe", args=[self.eq.pk]))

    def test_us07_planta_entrega_todos_os_campos_da_ficha(self):
        dados = self.client.get(reverse("inventario:planta")).context["dados"]
        e = dados["equipamentos"][0]
        for campo in ("patrimonio", "categoria_label", "fabricante", "modelo", "numero_serie", "status_label", "ambiente", "observacoes"):
            self.assertIn(campo, e)
        self.assertEqual(e["numero_serie"], "SN-XYZ-99")
        self.assertEqual(e["observacoes"], "Teclado trocado em outubro")

    def test_us07_ficha_mostra_todos_os_campos(self):
        resp = self.client.get(reverse("inventario:equipamento_detalhe", args=[self.eq.pk]))
        for texto in ("CA20", "Dell", "OptiPlex 3080", "SN-XYZ-99", "Em uso", "Recepção", "Teclado trocado em outubro"):
            self.assertContains(resp, texto)


class ManutencaoTests(TestCase):  # US08
    def setUp(self):
        self.amb = criar_ambiente("Sala TI")
        self.eq = Equipamento.objects.create(**{**dados_equipamento(self.amb), "ambiente": self.amb, "patrimonio": "CA30"})
        self.outro = Equipamento.objects.create(**{**dados_equipamento(self.amb), "ambiente": self.amb, "patrimonio": "CA31"})
        self.url = reverse("inventario:manutencao_nova", args=[self.eq.pk])

    def dados(self, **extra):
        from django.utils import timezone
        base = {"data": timezone.localdate().isoformat(), "problema": "Não liga", "acao": "Troca da fonte", "observacao": ""}
        base.update(extra)
        return base

    def test_registra_manutencao_e_mostra_na_ficha(self):
        resp = self.client.post(self.url, self.dados())
        self.assertRedirects(resp, self.eq.get_absolute_url())
        self.assertEqual(self.eq.manutencoes.count(), 1)
        ficha = self.client.get(self.eq.get_absolute_url())
        self.assertContains(ficha, "Não liga")
        self.assertContains(ficha, "Troca da fonte")

    def test_historico_fica_vinculado_ao_ativo(self):
        self.client.post(self.url, self.dados())
        self.assertNotContains(self.client.get(self.outro.get_absolute_url()), "Troca da fonte")

    def test_rejeita_data_futura(self):
        from datetime import timedelta
        from django.utils import timezone
        futuro = (timezone.localdate() + timedelta(days=3)).isoformat()
        self.assertEqual(self.client.post(self.url, self.dados(data=futuro)).status_code, 200)
        self.assertEqual(self.eq.manutencoes.count(), 0)

    def test_exige_problema_e_acao(self):
        self.client.post(self.url, self.dados(problema="   "))
        self.client.post(self.url, self.dados(acao=""))
        self.assertEqual(self.eq.manutencoes.count(), 0)

    def test_historico_mais_recente_primeiro(self):
        self.client.post(self.url, self.dados(data="2026-01-10", problema="Antigo"))
        self.client.post(self.url, self.dados(data="2026-03-10", problema="Recente"))
        problemas = [m.problema for m in self.eq.manutencoes.all()]
        self.assertEqual(problemas, ["Recente", "Antigo"])

    def test_sem_manutencao_mostra_mensagem_de_vazio(self):
        self.assertContains(self.client.get(self.eq.get_absolute_url()), "Nenhuma manutenção registrada")


class MovimentacaoTests(TestCase):  # US09
    def setUp(self):
        self.origem = criar_ambiente("Recepção")
        self.destino = criar_ambiente("Sala TI")
        self.eq = Equipamento.objects.create(**{
            **dados_equipamento(self.origem), "ambiente": self.origem, "patrimonio": "CA40",
            "planta_x": 30, "planta_y": 40,
        })
        self.url = reverse("inventario:equipamento_mover", args=[self.eq.pk])

    def test_move_atualiza_localizacao_e_registra_historico(self):
        resp = self.client.post(self.url, {"destino": self.destino.pk, "observacao": "Troca de setor"})
        self.assertRedirects(resp, self.eq.get_absolute_url())
        self.eq.refresh_from_db()
        self.assertEqual(self.eq.ambiente, self.destino)
        mov = self.eq.movimentacoes.get()
        self.assertEqual((mov.origem, mov.destino, mov.observacao), (self.origem, self.destino, "Troca de setor"))
        self.assertIsNotNone(mov.data)

    def test_move_zera_posicao_antiga_na_planta(self):
        self.client.post(self.url, {"destino": self.destino.pk})
        self.eq.refresh_from_db()
        self.assertIsNone(self.eq.planta_x)

    def test_ambiente_atual_nao_e_aceito_como_destino(self):
        resp = self.client.post(self.url, {"destino": self.origem.pk})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.eq.movimentacoes.count(), 0)

    def test_historico_aparece_na_ficha(self):
        self.client.post(self.url, {"destino": self.destino.pk})
        ficha = self.client.get(self.eq.get_absolute_url())
        self.assertContains(ficha, "Recepção")
        self.assertContains(ficha, "Sala TI")

    def test_mover_na_planta_tambem_registra_movimentacao(self):
        url = reverse("inventario:planta_equipamento_pos", args=[self.eq.pk])
        resp = self.client.post(url, data=json.dumps({"x": 20, "y": 20, "ambiente": self.destino.pk}), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.eq.refresh_from_db()
        self.assertEqual(self.eq.ambiente, self.destino)
        self.assertEqual((self.eq.planta_x, self.eq.planta_y), (20, 20))
        self.assertEqual(self.eq.movimentacoes.count(), 1)

    def test_posicionar_no_mesmo_ambiente_nao_registra_movimentacao(self):
        url = reverse("inventario:planta_equipamento_pos", args=[self.eq.pk])
        self.client.post(url, data=json.dumps({"x": 50, "y": 50, "ambiente": self.origem.pk}), content_type="application/json")
        self.assertEqual(self.eq.movimentacoes.count(), 0)

    def test_trocar_ambiente_na_edicao_registra_movimentacao(self):
        dados = dados_equipamento(self.origem, patrimonio="CA40", ambiente=self.destino.pk)
        self.client.post(reverse("inventario:equipamento_editar", args=[self.eq.pk]), dados)
        self.eq.refresh_from_db()
        self.assertEqual(self.eq.ambiente, self.destino)
        mov = self.eq.movimentacoes.get()
        self.assertEqual((mov.origem, mov.destino), (self.origem, self.destino))
