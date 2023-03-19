echo off
title Reset notebooks - Update Python env - Launch JupyterLab

taskkill /f /im JupyterLab.exe

cd c:\users\svc_neuropix\documents\github\np_notebooks

call .venv\scripts\activate.bat

echo git reset
git reset --hard -q

@REM first display the files without deleting, in case the user isn't aware of what this script does
echo git clean
git clean -n -f -d

@REM y for yes: default behavior is to delete untracked files in np_notebooks
set clean=y
@REM set /p clean=The above files/folders will be deleted. Clean? (y/n) [%clean%]
IF not %clean%==n (
git clean -f -d
)

git pull origin main

python -m pdm update np_workflows --no-self

start C:\JupyterLab\JupyterLab.exe

exit /b