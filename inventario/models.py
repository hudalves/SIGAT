from django.db import models
from django.urls import reverse


class Ambiente(models.Model):
    """US01 — ambientes e setores onde os equipamentos ficam instalados."""

    class Tipo(models.TextChoices):
        SETOR = "setor", "Setor"
        SALA = "sala", "Sala"
        ATENDIMENTO = "atendimento", "Ponto de atendimento"
        DEPOSITO = "deposito", "Depósito / estoque"
        OUTRO = "outro", "Outro"

    nome = models.CharField("nome", max_length=100, unique=True)
    tipo = models.CharField("tipo", max_length=20, choices=Tipo.choices, default=Tipo.SETOR)
    descricao = models.TextField("descrição", blank=True)
    # Posição na planta 2D, em % da largura/altura da planta (0–100). Vazio = posicionamento automático.
    planta_x = models.PositiveSmallIntegerField("posição X na planta (%)", null=True, blank=True)
    planta_y = models.PositiveSmallIntegerField("posição Y na planta (%)", null=True, blank=True)
    planta_largura = models.PositiveSmallIntegerField("largura na planta (%)", null=True, blank=True)
    planta_altura = models.PositiveSmallIntegerField("altura na planta (%)", null=True, blank=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "ambiente"
        verbose_name_plural = "ambientes"

    def __str__(self):
        return self.nome


class Equipamento(models.Model):
    """US02–US04 — ativo de TI do inventário."""

    class Categoria(models.TextChoices):
        COMPUTADOR = "computador", "Computador"
        NOTEBOOK = "notebook", "Notebook"
        MONITOR = "monitor", "Monitor"
        IMPRESSORA = "impressora", "Impressora / scanner"
        REDE = "rede", "Equipamento de rede"
        PERIFERICO = "periferico", "Periférico"
        OUTRO = "outro", "Outro"

    class Status(models.TextChoices):
        EM_USO = "em_uso", "Em uso"
        ESTOQUE = "estoque", "Em estoque"
        MANUTENCAO = "manutencao", "Em manutenção"
        INATIVO = "inativo", "Inativo"

    patrimonio = models.CharField("identificação / patrimônio", max_length=30, unique=True)
    nome = models.CharField("nome", max_length=100, blank=True)
    categoria = models.CharField("categoria", max_length=20, choices=Categoria.choices)
    fabricante = models.CharField("fabricante", max_length=60)
    modelo = models.CharField("modelo", max_length=80)
    numero_serie = models.CharField("número de série", max_length=80)
    status = models.CharField("status", max_length=20, choices=Status.choices, default=Status.EM_USO)
    ambiente = models.ForeignKey(
        Ambiente,
        verbose_name="ambiente",
        on_delete=models.PROTECT,
        related_name="equipamentos",
    )
    observacoes = models.TextField("observações", blank=True)
    # Posição do item dentro do ambiente na planta, em % da caixa do ambiente (0–100). Vazio = automático.
    planta_x = models.FloatField("posição X no ambiente (%)", null=True, blank=True)
    planta_y = models.FloatField("posição Y no ambiente (%)", null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["patrimonio"]
        verbose_name = "equipamento"
        verbose_name_plural = "equipamentos"

    def __str__(self):
        return f"{self.patrimonio} — {self.nome or self.modelo}"

    @property
    def esta_inativo(self):
        return self.status == self.Status.INATIVO

    def get_absolute_url(self):
        return reverse("inventario:equipamento_detalhe", args=[self.pk])

    def mover_para(self, destino, observacao=""):
        """US09 — troca o ambiente atual e registra origem/destino no histórico de movimentação."""
        if destino.pk == self.ambiente_id:
            return None
        movimentacao = Movimentacao.objects.create(
            equipamento=self, origem=self.ambiente, destino=destino, observacao=observacao
        )
        self.ambiente = destino
        self.planta_x = self.planta_y = None  # a posição antiga não vale no novo ambiente
        self.save(update_fields=["ambiente", "planta_x", "planta_y", "atualizado_em"])
        return movimentacao


class Manutencao(models.Model):
    """US08 — histórico de manutenção vinculado ao ativo."""

    equipamento = models.ForeignKey(
        Equipamento, verbose_name="equipamento", on_delete=models.CASCADE, related_name="manutencoes"
    )
    data = models.DateField("data")
    problema = models.TextField("problema")
    acao = models.TextField("ação executada")
    observacao = models.TextField("observação", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data", "-id"]
        verbose_name = "manutenção"
        verbose_name_plural = "manutenções"

    def __str__(self):
        return f"{self.equipamento.patrimonio} — {self.data:%d/%m/%Y}"


class Movimentacao(models.Model):
    """US09 — histórico de movimentação entre ambientes."""

    equipamento = models.ForeignKey(
        Equipamento, verbose_name="equipamento", on_delete=models.CASCADE, related_name="movimentacoes"
    )
    origem = models.ForeignKey(
        Ambiente, verbose_name="origem", on_delete=models.PROTECT, related_name="saidas", null=True, blank=True
    )
    destino = models.ForeignKey(
        Ambiente, verbose_name="destino", on_delete=models.PROTECT, related_name="entradas"
    )
    observacao = models.TextField("observação", blank=True)
    data = models.DateTimeField("data", auto_now_add=True)

    class Meta:
        ordering = ["-data", "-id"]
        verbose_name = "movimentação"
        verbose_name_plural = "movimentações"

    def __str__(self):
        return f"{self.equipamento.patrimonio}: {self.origem or '—'} → {self.destino}"
