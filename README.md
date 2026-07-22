# Diashow – Slideshow Webapp

Self-hosted Slideshow-Webapp: mehrere unabhängige Slideshows, jede über eine
eigene URL im Vollbild-Browser aufrufbar. Bilder (PNG/JPG) und Videos (MP4)
werden lokal gespeichert. Verwaltung über eine passwortgeschützte Admin-Seite.

## Lokale Entwicklung (macOS/Linux)

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

cp .env.example .env
# SECRET_KEY generieren:
./venv/bin/python -c "import secrets; print(secrets.token_hex(32))"
# ADMIN_PASSWORD_HASH generieren:
./venv/bin/python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('deinPasswort'))"
# beide Werte in .env eintragen

./venv/bin/python run.py
```

Admin-UI: http://localhost:8000/admin (Login mit dem oben gesetzten Passwort)
Player-Beispiel: http://localhost:8000/show/<slug>

## Nutzung

1. Im Admin-Bereich eine neue Slideshow anlegen (Name + Bilddauer in Sekunden).
2. Bilder (PNG/JPG) und Videos (MP4) hochladen.
3. Reihenfolge per Drag & Drop anpassen.
4. Die öffentliche URL der Slideshow kopieren und im Kiosk-Browser öffnen.

Videos werden immer vollständig abgespielt, bevor zum nächsten Slide
gewechselt wird. Bilder werden für die konfigurierte Dauer angezeigt.
Übergänge laufen von rechts nach links. Slideshows loopen endlos.

## Deployment auf Raspberry Pi OS Lite

Auf dem Pi (nicht auf dem Entwicklungsrechner!):

```bash
sudo bash deploy/install.sh
```

Das Skript installiert die App nach `/opt/diashow`, legt ein virtualenv an
und richtet den systemd-Service `slideshow` ein (Autostart beim Booten).
Nach der Installation `ADMIN_PASSWORD_HASH` in `/opt/diashow/.env` setzen
(Anleitung wird vom Skript ausgegeben) und den Service starten:

```bash
sudo systemctl start slideshow
sudo systemctl status slideshow
journalctl -u slideshow -f
```

### Zwei Bildschirme an einem Pi

Ein Server-Prozess auf Port 8000 bedient beliebig viele Slideshows über
unterschiedliche Pfade. Für zwei Kiosk-Browser auf demselben Pi einfach
zwei unterschiedliche Slideshow-URLs öffnen, z. B.:

- `http://localhost:8000/show/wohnzimmer`
- `http://localhost:8000/show/kueche`

Das Starten der Kiosk-Browser selbst (X11/Chromium-Autostart) ist nicht
Teil dieser App.

### Backup

Der komplette Datenbestand (Konfiguration + Medien) liegt unter `data/`:

```bash
tar -czf backup.tgz data/
```

## Projektstruktur

```
app/
  __init__.py       App-Factory, Blueprint-Registrierung
  config.py         Konfiguration aus Umgebungsvariablen
  storage.py         Datenschicht (JSON pro Slideshow, atomare Writes)
  auth.py             Login/Logout, login_required
  admin.py            Admin-Routen (CRUD, Upload, Reorder)
  player.py           Öffentliche Player-Routen + Mediendateien
  templates/           Jinja-Templates
  static/css, static/js  Frontend (kein Build-Schritt nötig)
data/                  Laufzeitdaten (gitignored)
deploy/
  slideshow.service    systemd-Unit
  install.sh            Installationsskript für den Pi
wsgi.py                 Produktions-Einstiegspunkt (waitress)
run.py                  Lokaler Dev-Server
```
