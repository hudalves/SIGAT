@echo off
cd /d %~dp0
echo === SIGAT: preparar, testar e publicar no GitHub ===
if not exist .venv\Scripts\python.exe python -m venv .venv
call .venv\Scripts\activate
echo Instalando dependencias (se estiver bloqueado, segue com o que ja esta instalado)...
python -m pip install -q -r requirements.txt
if errorlevel 1 echo AVISO: nao consegui instalar agora; usando o que ja esta instalado.
python manage.py makemigrations inventario || goto erro
python manage.py migrate || goto erro
python manage.py seed_demo
python manage.py test
echo.
echo === Enviando para o GitHub ===
git init
git add .
git commit -m "Sprint 2: planta interativa, exportar CSV e integracao continua"
git branch -M main
git remote remove origin 2>nul
git remote add origin https://github.com/hudalves/SIGAT.git
git pull origin main --allow-unrelated-histories --no-edit -X ours
git push -u origin main
echo.
echo Pronto. Confira o resultado dos testes acima (precisa aparecer OK).
pause
exit /b 0
:erro
echo ERRO: copie a mensagem acima e envie para o Claude.
pause
exit /b 1
