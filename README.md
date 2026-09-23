# Pokémon Weakness and Counter API

Grundgerüst gemäß Projektauftrag. Das MVP verwendet englische Bezeichner wie
`charizard` und `fire`.

## Stand

FastAPI mit `/health` und Swagger `/docs` ist vorbereitet. Die Dateien für
Analyse, Modelle, PokéAPI-Client, Cache, Konfiguration und Logging sind noch
Platzhalter. Fallback, Rate-Limit und `/ready` sind ebenfalls noch offen.

## Lokal starten

Python 3.12 verwenden. Im Projektverzeichnis unter PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn App.main:app --reload
```

Swagger: http://127.0.0.1:8000/docs

Health: http://127.0.0.1:8000/health

Die Großschreibung von `App` und `Tests` muss auch auf Linux erhalten bleiben.

## Struktur

```text
App/
  main.py                 FastAPI und Health-Check
  api/routes.py           Router für /api/v1
  core/config.py          Konfiguration (offen)
  core/logging.py         Strukturierte Logs (offen)
  models/schemas.py       Pydantic-Modelle (offen)
  services/
    pokeapi_client.py     Externe Abfragen (offen)
    analysis_service.py   Schwächen und Counter-Score (offen)
    cache_service.py      TTL-Cache (offen)
Tests/
  test_health.py          Health-Test
  test_analysis.py        Platzhalter
  test_security.py        Platzhalter
.github/workflows/ci.yml  Tests und Dependency-Audit
.env.example             Geplante Konfiguration
render.yaml              Cloud-Konfiguration
requirements.txt         Laufzeit-Abhängigkeiten
requirements-dev.txt     Test- und Audit-Werkzeuge
pytest.ini               Test-Konfiguration
.python-version          Python 3.12
```

## Prüfungen

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip_audit
```

CI führt beide Prüfungen bei Push und Pull Request aus. Die bestehenden
Paketversionen wurden beibehalten; bekannte Schwachstellen lassen den Audit
fehlschlagen und müssen vor der Freigabe durch Updates behoben werden.

## Konfiguration und Deployment

`.env.example` dokumentiert die vorgesehenen Variablen. Das Grundgerüst lädt
sie noch nicht. Zugangsdaten gehören nicht ins Repository.

Für Render das GitHub-Repository als Blueprint mit `render.yaml` verbinden.
Der Dienst startet `App.main:app`, verwendet `/health` und ist für automatische
Deployments nach erfolgreichen CI-Prüfungen auf `main` konfiguriert.
Es wurde noch kein Cloud-Dienst angelegt.

Referenz: [Render Blueprint-Spezifikation](https://render.com/docs/blueprint-spec).

## Nächste Umsetzungsschritte

1. Modelle und `POST /api/v1/analyze` implementieren.
2. PokéAPI-Client mit httpx, Schwächenberechnung und Counter-Score ergänzen.
3. Cache, Fallback, `/ready`, Logging und Rate-Limit implementieren.
4. Analyse- und Security-Tests ergänzen und Cloud-Abnahme durchführen.
