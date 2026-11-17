from django.core.management.base import BaseCommand

from inventario.models import Ambiente, Equipamento


class Command(BaseCommand):
    help = "Cria dados fictícios de demonstração (ambientes e equipamentos)."

    def handle(self, *args, **options):
        recepcao, _ = Ambiente.objects.get_or_create(
            nome="Recepção", defaults={"tipo": Ambiente.Tipo.ATENDIMENTO, "descricao": "Atendimento ao público (demo)"}
        )
        sala_ti, _ = Ambiente.objects.get_or_create(
            nome="Sala de TI", defaults={"tipo": Ambiente.Tipo.SALA, "descricao": "Suporte e infraestrutura (demo)"}
        )
        for amb, pos in ((recepcao, (5, 10, 40, 45)), (sala_ti, (52, 10, 40, 45))):
            if amb.planta_x is None:
                amb.planta_x, amb.planta_y, amb.planta_largura, amb.planta_altura = pos
                amb.save()
        demo = [
            ("DEMO-001", "PC Balcão 1", "computador", "Dell", "OptiPlex 3080", "SN-DEMO-001", "em_uso", recepcao, (25, 55)),
            ("DEMO-002", "Monitor Balcão 1", "monitor", "LG", "24MK430H", "SN-DEMO-002", "em_uso", recepcao, (55, 55)),
            ("DEMO-003", "Notebook Suporte", "notebook", "Lenovo", "ThinkPad E14", "SN-DEMO-003", "estoque", sala_ti, (50, 55)),
        ]
        criados = 0
        for pat, nome, cat, fab, mod, serie, status, amb, pos in demo:
            _, novo = Equipamento.objects.get_or_create(
                patrimonio=pat,
                defaults=dict(nome=nome, categoria=cat, fabricante=fab, modelo=mod,
                              numero_serie=serie, status=status, ambiente=amb,
                              planta_x=pos[0], planta_y=pos[1]),
            )
            criados += int(novo)
        self.stdout.write(self.style.SUCCESS(f"Dados de demonstração prontos ({criados} novos equipamentos)."))
