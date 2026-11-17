@echo off
cd /d %~dp0
echo === SIGAT: preparar, testar e publicar no GitHub ===
python -m venv .venv || goto erro
call .venv\Scripts\activate
pip install -r requirements.txt || goto erro
python manage.py makemigrations inventario || goto erro
python manage.py migrate || goto erro
python manage.py seed_demo
python manage.py test
echo.
echo === Enviando para o GitHub ===
git init
git add .
git commit -m "Sprint 1: ambientes e equipamentos (US01-US04)"
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
