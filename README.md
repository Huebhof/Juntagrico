Juntagrico Heroku Template for cookiecutter
===========

This template sets up a project to be used with juntagrico.science as hosting.

# Setting up locally to test setup

On any environment install Python 3, and add it to your path

## UNIX

### Set your environment variables


### Installing requirements

    sudo easy_install pip
    sudo pip install virtualenv
    virtualenv --distribute venv
    source ./venv/bin/activate
    pip install --upgrade -r requirements.txt

### Setup DB

    ./manage.py migrate
    
### Setup Admin User

    ./manage.py createsuperuser
    ./manage.py create_member_for_superusers
    
### Create Tesdata (not required)

Simple

    ./manage.py generate_testdata

More complex

    ./manage.py generate_testdata_advanced
    
### Run the server

    ./manage.py runserver

## Windows

### Set your environment variables

This should do it for your local setup:


### Installing requirements

    pip install virtualenv
    virtualenv --distribute venv
    venv\Scripts\activate.bat
    pip install --upgrade -r requirements.txt

### Setup DB

    python -m manage migrate
    
### Setup Admin User

    python -m manage createsuperuser
    python -m manage create_member_for_superusers
    
### Create Tesdata (not required)

Simple

    python -m manage generate_testdata

More complex

    python -m manage generate_testdata_advanced
    
### Run the server

    python -m manage runserver
    
#Heroku

you have to login to a heroku bash and setup the db and create the admin user as desbribed in the UNIX section


python --version

Virtuelle Umgebung erstellen und aktivieren:

python -m venv venv
venv\Scripts\activate

requirements installieren und anzeigen:

pip install -r requirements.txt
pip list

setuptools installieren und anzeigen:

pip install setuptools
pip show setuptools

juntagrico DB migrieren:

python manage.py migrate

Umgebungsvariablen setzten:

$env:JUNTAGRICO_SECRET_KEY = "fake"
set JUNTAGRICO_SECRET_KEY=fake

$env:JUNTAGRICO_DEBUG= "True"
set JUNTAGRICO_DEBUG=True

Server starten:

python manage.py runserver

http://localhost:8000/

## Upgrade auf Juntagrico 2.0

Die folgenden Punkte haben sich bei diesem Projekt fuer das Upgrade auf `juntagrico~=2.0.0` und `juntagrico-billing~=2.0.0` als relevant erwiesen.

### Anforderungen aktualisieren

In `requirements.txt`:

```text
juntagrico~=2.0.0
juntagrico-billing~=2.0.0
gunicorn~=25.1.0
```

Danach lokal aktualisieren:

```powershell
.\venv\Scripts\python.exe -m pip install --upgrade -r requirements.txt
```

Versionen pruefen:

```powershell
.\venv\Scripts\python.exe -c "import importlib.metadata as m; print(m.version('juntagrico')); print(m.version('juntagrico-billing'))"
```

### Settings anpassen

In `huebhof/settings.py`:

- `django.contrib.admin` durch `juntagrico.apps.JuntagricoAdminConfig` ersetzen
- `fontawesomefree` entfernen
- `crispy_bootstrap4`, `django_select2` und `djrichtextfield` in `INSTALLED_APPS` fuehren
- `from juntagrico import defaults` importieren
- `DJRICHTEXTFIELD_CONFIG = defaults.richtextfield_config(LANGUAGE_CODE)` setzen
- `SESSION_SERIALIZER` entfernen
- `MAIL_TEMPLATE` entfernen, wenn das Template bereits unter `templates/mails/email.html` liegt
- `DEFAULT_MAILER` durch `EMAIL_BACKEND` ersetzen

Empfohlene Mail-Backend-Konfiguration:

```python
EMAIL_BACKEND = os.environ.get(
    'JUNTAGRICO_EMAIL_BACKEND',
    'juntagrico.backends.email.BatchEmailBackend'
)
```

Fuer lokales Testen:

```powershell
$env:JUNTAGRICO_EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend'
```

### Lokaler Start

```powershell
$env:JUNTAGRICO_SECRET_KEY="fake"
$env:JUNTAGRICO_DEBUG="True"
$env:JUNTAGRICO_EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend'
.\venv\Scripts\python.exe .\manage.py runserver
```

Falls `127.0.0.1` lokal verwendet wird, muss es in `ALLOWED_HOSTS` stehen.

### Migrationen

Beim Upgrade koennen Konflikte in den Migrations der Drittanbieterpakete auftreten, z. B. in:

- `juntagrico`
- `juntagrico_billing`

Lokal konnte dies mit einem Merge aufgeloest werden:

```powershell
.\venv\Scripts\python.exe .\manage.py makemigrations --merge juntagrico_billing juntagrico
.\venv\Scripts\python.exe .\manage.py migrate
```

Wichtig:

- Die dabei erzeugten Merge-Migrationen lagen im `venv\Lib\site-packages\...`
- Das ist ein lokaler Workaround, kein sauberer Repo-Fix
- Diese Dateien duerfen nicht committed werden

### Templates mit neuen Pfaden

Die folgenden Overrides wurden fuer 2.0 auf die neuen Pfade verschoben:

- `signup.html` -> `huebhof/templates/juntagrico/signup/member.html`
- `forms/no_subscription_field.html` -> `huebhof/templates/juntagrico/subscription/create/form/no_subscription_field.html`
- `depot.html` -> `huebhof/templates/juntagrico/my/depot/show.html`

### Mail-Templates

Das Projekt verwendet weiterhin ein eigenes Mail-Layout:

- `huebhof/templates/mails/email.html`
- `huebhof/templates/juntagrico/mails/signature.html`

Fuer 2.0 wurde das Template auf die neuen Blocks (`css`, `subject`, `all_content`, `content`, `signature`) umgestellt.

### Layout-Overrides

Fuer gleichmaessige Kartenabstaende und Hoehen wurden lokale Overrides hinzugefuegt:

- `huebhof/templates/juntagrico/snippets/subscription/type_container.html`
- `huebhof/templates/juntagrico/form/layout/bundle_container.html`
- `huebhof/templates/juntagrico/config/snippets/bundles.html`
- `huebhof/static/huebhof/css/customize.css`

Diese Dateien sind projekt-spezifisch und sollten bei kuenftigen Juntagrico-Upgrades erneut gegen die Paket-Templates geprueft werden.


