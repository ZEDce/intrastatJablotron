@echo off
echo ===============================================
echo    INTRASTAT JABLOTRON - CONDA ENV SETUP
echo ===============================================

echo.
echo 1. Vytvaram novu conda environment...
conda env create -f environment.yml

echo.
echo 2. Aktivujem environment...
call conda activate intrastat-jablotron

echo.
echo 3. Kontrolujem instalovane balicky...
echo Pip packages:
pip list | findstr -i "pymupdf google dotenv"

echo.
echo Conda packages:
conda list | findstr -i "pandas pillow tqdm"

echo.
echo ===============================================
echo    SETUP DOKONCENY!
echo ===============================================
echo.
echo Pre aktivaciu environment pouzi:
echo   conda activate intrastat-jablotron
echo.
echo Pre testovanie refaktorovanej verzie:
echo   python main_new.py
echo.
echo Pre deaktivaciu:
echo   conda deactivate
echo.
pause 