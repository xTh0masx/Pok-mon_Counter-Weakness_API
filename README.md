# Pokémon Weakness and Counter API

FastAPI-Anwendung zur Analyse von Pokémon-Schwächen und passenden Countern.
Das MVP verwendet englische PokéAPI-Bezeichner wie `charizard` und `fire`.
Empfehlungen beruhen auf Typen und Basiswerten, nicht auf einer Kampfsimulation.

## Implementierter Stand

- Pokémon- und Typanalyse mit automatischer Erkennung sowie validierten JSON-Modellen.
- Multiplikative Schwächenberechnung für Einzel- und Doppeltypen einschließlich Immunitäten.
- Begründete, absteigend sortierte Counter-Rangliste ohne Duplikate oder Ziel-Pokémon.
- Asynchroner PokéAPI-Client mit Timeout, begrenzten Wiederholungen und parallelen Abfragen.
- Begrenzter TTL-Cache, zeitlich begrenzter Stale-Cache und lokale Tabelle aller 18 Typen.
- Health- und Ready-Checks, JSON-Logs und Correlation-ID pro Request.
- Rate-Limit, Body-Limit, sichere Fehlerantworten und automatisierte Tests.
- GitHub-Actions-Pipeline mit Tests und Dependency-Audit sowie Render-Konfiguration.

## Lokal starten

Python 3.12 verwenden. In PowerShell im Projektverzeichnis:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn App.main:app --reload --no-access-log
```

Eine bereits konfigurierte `.env` beibehalten. Umgebungsvariablen haben Vorrang
vor `.env`; ungültige Konfiguration verhindert den Start.
Für reinen Betrieb genügt `requirements.txt`.
Die Großschreibung von `App` und `Tests` ist unter Linux relevant.

Swagger: http://127.0.0.1:8000/docs

## Endpoints und Beispiel

| Endpoint | Verhalten |
| --- | --- |
| `POST /api/v1/analyze` | Schwächen und bis zu `limit` Counter |
| `GET /health` | Prozess lebt; kein externer Aufruf |
| `GET /ready` | Typdaten verfügbar, aus Cache oder begrenztem Fallback |
| `GET /docs` | Interaktive Swagger-Dokumentation |

```powershell
$body = @{ query = 'charizard'; input_type = 'auto'; limit = 3 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/analyze -ContentType 'application/json' -Body $body
```

`query` wird getrimmt und kleingeschrieben: 1–50 Zeichen, ASCII-Buchstaben,
Ziffern und einzelne Bindestriche zwischen Bestandteilen. `input_type` erlaubt
`auto`, `pokemon` und `type`. `limit` ist eine Ganzzahl von 1 bis 10, Standard 5.
Unbekannte Zusatzfelder werden abgelehnt. Deutsche Namen werden nicht übersetzt.

Die Antwort enthält `target`, `target_types`, `weaknesses`,
`recommended_pokemon` mit `name`, `score` und `reason`, sowie `source`,
`cache_used` und `warnings`. Charizard hat `rock: 4`, `water: 2`, `electric: 2`.
Bei Gleichstand werden Schwächen und Empfehlungen alphabetisch sortiert.

Fehlercodes: `404` unbekanntes Ziel, `422` ungültige Eingabe, `413` Body über
8 KiB, `429` Rate-Limit, `503` keine nutzbaren Pokémon-Daten oder Analyse-Timeout.
`429` und `503` enthalten `Retry-After`. Unerwartete Fehler liefern eine generische
`500`-Antwort; Details stehen nur im internen Log.

## Berechnung und Kandidatenauswahl

Die eingehenden Typfaktoren werden pro Zieltyp multipliziert: Schwäche ×2,
Resistenz ×0,5 und Immunität ×0. Nur Faktoren über 1 werden als Schwächen ausgegeben.

Aus den drei stärksten Angriffstypen werden standardmäßig jeweils bis zu fünf
verschiedene Kandidaten in PokéAPI-Reihenfolge ausgewählt. Ziel und Duplikate
werden übersprungen. Es gibt höchstens fünf gleichzeitige externe Aufrufe.
Der Standardpool enthält somit maximal 15 Kandidaten; er ist keine globale
Suche nach den stärksten Pokémon aller Generationen.

```text
type_score    = min(bester_typfaktor, 4) / 4 * 6
offense_score = min(max(attack, special_attack), 200) / 200 * 3
speed_score   = min(speed, 200) / 200 * 1
score         = round(type_score + offense_score + speed_score, 2)
```

Die Begründung nennt Angriffstyp, Faktor, offensiven Basiswert und Initiative.
Movesets, Fähigkeiten, Items und defensive Matchups sind nicht berücksichtigt.

## Konfiguration

| Variable | Standard | Bedeutung |
| --- | --- | --- |
| `POKEAPI_BASE_URL` | `https://pokeapi.co/api/v2` | HTTPS-Basisadresse ohne Zugangsdaten |
| `POKEAPI_TIMEOUT_SECONDS` | `5` | Frist pro externem Versuch |
| `POKEAPI_RETRIES` | `1` | Zusätzliche Versuche, maximal 2 |
| `CACHE_TTL_SECONDS` | `3600` | Frische Cache-Dauer |
| `CACHE_STALE_SECONDS` | `86400` | Zusätzliche Nutzungsdauer bei Ausfällen |
| `CACHE_MAX_ENTRIES` | `1000` | Maximale Anzahl gecachter Ressourcen |
| `CANDIDATES_PER_TYPE` | `5` | Kandidaten pro Angriffstyp, maximal 10 |
| `RATE_LIMIT_PER_MINUTE` | `30` | Requests pro Client und 60-Sekunden-Fenster |
| `LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR oder CRITICAL |

## Ausfälle, Sicherheit und Betrieb

Frische Cache-Daten vermeiden externe Aufrufe. Bei Timeout, HTTP-Fehlern außer
404 oder ungültigen Upstream-Daten folgen begrenzte Retries mit Backoff.
Nach erfolglosen Versuchen pausieren neue externe Abfragen für 15 Sekunden.
Vorhandene Stale-Daten werden mit Warnung genutzt. Andernfalls ermöglicht die
lokale Typentabelle weiterhin Typanalysen, gegebenenfalls ohne Empfehlungen.
Ein unbekanntes Pokémon lässt sich offline nicht auflösen und führt zu `503`.
Eine bestätigte Upstream-404 wird nicht durch alte Cache-Daten verdeckt.
Die gesamte Analyse ist auf 20 Sekunden begrenzt.

`source` ist `fallback`, sobald lokale Typdaten beteiligt sind, sonst `pokeapi`,
wenn mindestens eine Ressource live geladen wurde, andernfalls `cache`.
`cache_used` meldet jeden Cache-Anteil; Warnungen markieren Stale-Daten,
Fallback und fehlende Kandidaten.

`/ready` liefert auch im eingeschränkten Fallback-Betrieb HTTP 200 mit
`status: degraded`. Bei frischem Cache meldet es `ready` und `source: cache`;
das ist keine erneute Prüfung der aktuellen Upstream-Erreichbarkeit.

Das Rate-Limit gilt für `/api/`, einschließlich ungültiger Anfragen. Health
und Ready bleiben ausgenommen. CORS ist nicht aktiviert. Die Client-Adresse
stammt aus dem ASGI-Scope; hinter einem Proxy müssen ausschließlich tatsächlich
vertrauenswürdige Proxy-Adressen in Uvicorn konfiguriert werden. Andernfalls
können mehrere Nutzer dasselbe Limit teilen. Beliebige Forwarded-Header werden
von der Anwendung nicht selbst ausgewertet.

Cache und Rate-Limit gelten pro Prozess, gehen bei Neustart verloren und sind
nicht zwischen Instanzen synchronisiert. Für den MVP einen Worker verwenden.
Der Cache ist nach Einträgen begrenzt; maximal 10.000 aktive Client-Fenster
werden im Rate-Limiter gehalten. Bei voller Kapazität werden neue Clients
vorübergehend ebenfalls mit 429 abgewiesen.

JSON-Logs enthalten Zeitstempel, Correlation-ID, Endpoint, Status und Dauer.
Weitere Events sind `cache_hit`, `upstream_error`, `fallback_used` und
`security_event`. Die Antwort enthält `X-Correlation-ID`. IP-Adressen und
Request-Bodies werden von diesen Logs nicht gespeichert. `--no-access-log`
verhindert zusätzliche Uvicorn-Zugriffslogs mit Client-Adressen. Ein externes
Dashboard oder Alarmierung ist noch nicht eingerichtet.

## Struktur

```text
App/
  main.py                  App-Factory, Lebenszyklus, Health und Ready
  api/routes.py            Analyse-Endpoint und Fehlerzuordnung
  core/config.py           Validierte Umgebungsvariablen und .env
  core/logging.py           JSON-Logs und Correlation-ID
  core/middleware.py        Request-Logs, Rate-Limit und Body-Limit
  models/schemas.py         Anfrage- und Antwortmodelle
  services/
    pokeapi_client.py       HTTP, Ressourcenprüfung, Retries und Fallback
    analysis_service.py     Typfaktoren, Kandidaten und Score
    cache_service.py        Begrenzter TTL-/Stale-Cache
    type_chart.py           Lokale moderne Typentabelle
Tests/                     Offline-Tests mit simuliertem HTTP-Transport
scripts/smoke_test.py       Expliziter Live- und Cloud-Abnahmetest
.github/workflows/ci.yml    Tests und Audit auf Python 3.12
render.yaml                Render-Blueprint
```

## Tests und nachgewiesener Stand

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pip_audit
.\.venv\Scripts\python.exe scripts/smoke_test.py
```

Die Unit-/Integrationstests nutzen MockTransport ohne Netzwerk. Das separate
Smoke-Skript greift ausdrücklich auf die echte PokéAPI zu und gleicht zusätzlich
alle 18 lokalen Typbeziehungen ab. Der Audit benötigt Netzwerkzugriff.

Prüfstand vom 23.09.2026 unter Windows/Python 3.12:

- 54 Tests erfolgreich, einschließlich Doppeltypen, Immunitäten, Score, Cache,
  Stale-Fallback, Timeout, Retry-Grenzen, 404, 422, 429, 413 und sicherer 500-Antwort.
- `pip check`: keine Abhängigkeitskonflikte.
- `pip-audit`: keine bekannten Schwachstellen nach Updates der Pakete und von pip.
- Live-PokéAPI-Test erfolgreich; alle 18 lokalen Typen stimmen überein.
- Ein gemessener Cache-Aufruf dauerte lokal ungefähr 4 ms. Das ist eine
  Einzelmessung, kein Lasttest oder p95-Nachweis.
- Starlette meldet beim TestClient eine Deprecation-Warnung zur künftigen
  Umstellung von httpx auf httpx2; die Tests bestehen.

## CI und Render

Die [Schritt-für-Schritt-Anleitung für GitHub und Render](docs/DEPLOYMENT.md)
führt vom bereits verknüpften Repository über Commit, Pull Request und CI bis
zur öffentlichen API. Sie enthält die konkreten Einstellungen, Fehlerhilfe
und eine Checkliste für die Abgabenachweise.

GitHub Actions aktualisiert pip, installiert die Test-Abhängigkeiten und führt
Tests sowie Audit bei Push und Pull Request aus. Direkte Abhängigkeiten sind
auf getestete Versionen festgelegt; transitive Pakete werden noch nicht über
ein vollständiges Lockfile fixiert.

CI kann zusätzlich über **Actions → CI → Run workflow** manuell gestartet
werden, sobald der Workflow auf dem Standardbranch liegt.

Das Repository als Render-Blueprint mit `render.yaml` verbinden. Der Dienst
startet `App.main:app`, prüft `/health` und deployed Änderungen auf `main` nach
erfolgreichen CI-Prüfungen. Die Konfiguration ist vorbereitet; eine öffentliche
Cloud-URL und ein erfolgreicher GitHub-CI-Lauf wurden hier noch nicht nachgewiesen.

Nach Bereitstellung die tatsächliche Service-URL einsetzen:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_test.py --base-url https://DEIN-SERVICE.onrender.com
```

Dieser Test prüft Health, Swagger, Analyse, Cache, Fehlercodes und Ready und
legt keinen Cloud-Dienst an. Cloud-Kaltstarts separat messen.

## Nächste Umsetzungsschritte

1. [Deployment-Anleitung](docs/DEPLOYMENT.md), Schritte 2–4: Änderungen auf
   GitHub bereitstellen, Pull Request und CI prüfen und Branch-Schutz einrichten.
2. Schritte 5–8: Render mit dem Repository verbinden, Service bereitstellen und öffentliche
   URL mit dem Smoke-Skript abnehmen. Proxy-Konfiguration und Client-Limits
   auf Render verifizieren, anschließend ein Re-Deployment nachweisen.
3. Betriebsnachweise sammeln: Cloud-Logs, Cache-/Fallback-Beispiele und
   Latenzmessungen mit p95, Last und Kaltstart; Schwellen und Alarmierung festlegen.
4. Abschlussdokumentation zu Architektur, Infrastrukturentscheidungen,
   Reifegrad und Abnahmekriterien um die Cloud-Ergebnisse ergänzen.
5. Für weitere Härtung ein plattformübergreifendes Dependency-Lockfile und
   die TestClient-Migration prüfen. Bei mehreren Instanzen Cache und Rate-Limit
   zentralisieren, beispielsweise mit Redis.

## Referenzen

- [PokéAPI-Dokumentation](https://pokeapi.co/docs/v2)
- [HTTPX-Transports für Tests](https://www.python-httpx.org/advanced/transports/)
- [Render-Blueprint-Spezifikation](https://render.com/docs/blueprint-spec)
