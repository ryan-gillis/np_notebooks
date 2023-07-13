cd c:\users\svc_neuropix\documents\github\np_notebooks
"C:\Users\svc_neuropix\AppData\Local\Programs\Python\Python311\python.exe" -m venv .venv
call .venv\scripts\activate.bat
python -m ensurepip
@REM python -m pip install -U np_workflows --extra-index-url https://pypi.org/simple --upgrade-strategy eager
python -m pip install --extra-index-url https://pypi.org/simple pdm
python -m pdm install --no-self