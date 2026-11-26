#!/bin/bash
cd "$(dirname "$0")"
set -e
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py makemigrations inventario
python manage.py migrate
python manage.py seed_demo
python manage.py test || echo "ATENÇÃO: há testes falhando, veja acima."
git init
git add .
git commit -m "Sprint 1: ambientes e equipamentos (US01-US04)" || true
git branch -M main
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/hudalves/SIGAT.git
git pull origin main --allow-unrelated-histories --no-edit -X ours || true
git push -u origin main
