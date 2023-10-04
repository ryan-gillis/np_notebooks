echo off
title Reset notebooks - Update Python env - Launch JupyterLab

taskkill /f /im JupyterLab.exe
taskkill /f /im python.exe

cd c:\users\svc_neuropix\documents\github\np_notebooks

@REM call \\allen\programs\mindscope\workgroups\np-exp\envs\win\np_notebooks\3.11\.venv\Scripts\activate
call .venv\scripts\activate.bat

echo git reset
git reset --hard -q

echo git clean
@REM first display the files without deleting, in case the user isn't aware of what this script does
@REM git clean -n -f -d

@REM y for yes: default behavior is to delete untracked files in np_notebooks
set clean=y
set /p clean=The above files/folders will be deleted. Clean? (y/n) [%clean%]
IF not %clean%==n (
git clean -f -d
)

git pull origin main

@REM python -m pip install -r requirements.txt
python -m pdm sync

start C:\JupyterLab\JupyterLab.exe

exit /b 
