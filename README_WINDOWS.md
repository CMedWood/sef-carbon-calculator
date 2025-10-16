
# SEF Carbon Calculator (Fresh Starter)

This starter includes a branded Streamlit app with a large SVG logo header and a factors CSV template.

## Folder layout
```
sef_app_starter/
├─ app.py
├─ requirements.txt
├─ nga_factors_2024.csv
└─ assets/
   └─ Sustainable Equine Program.svg
```

## Windows quick start (Python 3.12)
Open PowerShell in this folder and run:
```
python -m venv venv312
.\venv312\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

> If activation is blocked, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` once in the same terminal and retry the Activate.ps1 line.

## Replace factors with NGA values
The provided `nga_factors_2024.csv` includes **placeholder** factors so the app runs. Replace with the latest **NGA 2024/25** emission factors before using with clinics.
