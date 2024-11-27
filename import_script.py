import os
import sys
import django
from subprocess import run

# Basisverzeichnis und virtuelle Umgebung definieren
base_dir = os.path.abspath(os.path.dirname(__file__))
venv_path = os.path.join(base_dir, "venv", "Scripts", "python.exe")

# Django-Einstellungen initialisieren
os.environ["DJANGO_SETTINGS_MODULE"] = "huebhof.settings"

try:
    django.setup()
except Exception as e:
    print(f"Fehler beim Initialisieren von Django: {e}")
    exit(1)

# JSON-Dateipfad
json_path = os.path.join(base_dir, "dbimport", "huebhof.json")
if not os.path.exists(json_path):
    print(f"Fehler: JSON-Datei nicht gefunden unter {json_path}")
    exit(1)

# Datenbank leeren
print("Lösche alle Daten aus der Datenbank...")
run([venv_path, "manage.py", "flush", "--noinput"], cwd=base_dir)

# Daten importieren
print("Importiere Daten aus der JSON-Datei...")
run([venv_path, "manage.py", "loaddata", json_path], cwd=base_dir)

print("Datenimport abgeschlossen.")
