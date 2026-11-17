# SIGAT — Sistema de Gestão de Ativos de TI

MVP em Django (Projeto M2 — Métodos Ágeis). Este pacote cobre a **Sprint 1**: US01 a US04
(ambientes, cadastro, consulta/busca, edição e inativação de equipamentos).

## Atalho (automático)

- Windows: dê dois cliques em `1_local_e_github.bat` (cria o ambiente, migra, testa e envia ao GitHub).
- Mac/Linux: `./1_local_e_github.sh`
- PythonAnywhere (console Bash, depois de criar o web app na aba Web): `bash 2_deploy_pythonanywhere.sh`
- Dados fictícios de demonstração: `python manage.py seed_demo`

## Como rodar (manual)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations inventario
python manage.py migrate
python manage.py createsuperuser  # opcional, para usar /admin/
python manage.py runserver
```

Acesse http://127.0.0.1:8000/

## Testes

```bash
python manage.py test
```

## Mapa das histórias

| História | Onde está |
|---|---|
| US01 Ambientes | `/ambientes/`, `/ambientes/novo/` |
| US02 Cadastro de equipamento | `/equipamentos/novo/` |
| US03 Consulta e busca | `/equipamentos/` (busca por patrimônio, nome/modelo, categoria) |
| US04 Editar / inativar | `/equipamentos/<id>/editar/`, `/equipamentos/<id>/inativar/` |

Próximas Sprints: planta interativa (US05–US07), manutenção, movimentação e CSV (US08–US10).
