#!/bin/bash
# Rode no console Bash do PythonAnywhere, DEPOIS de criar o web app (Manual configuration) na aba Web.
set -e
cd ~
if [ -d SIGAT ]; then cd SIGAT && git pull; else git clone https://github.com/hudalves/SIGAT.git && cd SIGAT; fi
PY=$(for v in python3.13 python3.12 python3.11 python3.10; do command -v $v && break; done || true)
if [ -z "$PY" ]; then echo "Python 3.10+ não encontrado."; exit 1; fi
$PY -m venv ~/.virtualenvs/sigat
VPY=$HOME/.virtualenvs/sigat/bin/python
$VPY -m pip install -q -r requirements.txt
$VPY manage.py migrate
$VPY manage.py collectstatic --noinput
$VPY manage.py seed_demo
SECRET=$($VPY -c "import secrets; print(secrets.token_urlsafe(50))")
WSGI=/var/www/$(whoami)_pythonanywhere_com_wsgi.py
CONTEUDO="import os, sys
path = '$HOME/SIGAT'
if path not in sys.path:
    sys.path.append(path)
os.environ['DJANGO_SETTINGS_MODULE'] = 'sigat.settings'
os.environ['DJANGO_DEBUG'] = '0'
os.environ['DJANGO_SECRET_KEY'] = '$SECRET'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()"
if [ -w "$(dirname $WSGI)" ] && [ -f "$WSGI" ]; then
  echo "$CONTEUDO" > "$WSGI"; echo "Arquivo WSGI configurado."
else
  echo "Não consegui gravar o WSGI. Cole isto no WSGI configuration file da aba Web:"; echo "$CONTEUDO"
fi
echo
echo "Falta só na aba Web: Virtualenv = $HOME/.virtualenvs/sigat"
echo "e Static files: /static/  ->  $HOME/SIGAT/staticfiles   (depois clique em Reload)"
