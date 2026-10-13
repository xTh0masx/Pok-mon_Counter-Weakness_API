# Projektstand und technische Nachweise

Stand: 29.09.2026. Lokaler MVP mit Browser-Oberfläche; vom Benutzer als
funktionierend bestätigt. GitHub-CI-Ergebnis und öffentliche Render-URL
sind noch nicht nachgewiesen.

## Architektur

```text
Browser auf 127.0.0.1:8765
  -> FastAPI: statische HTML/CSS/JS-Oberfläche unter /
  -> POST /api/v1/analyze
  -> Pydantic-Validierung und AnalysisService
  -> PokeAPIClient -> begrenzter TTL-/Stale-Cache -> PokéAPI
                  -> lokale Typentabelle bei Ausfall
  <- JSON mit Schwächen, Counter-Scores und Betriebswarnungen
```

Request-Middleware begrenzt Anfragen und Body-Größe und protokolliert Dauer,
Status und Correlation-ID. Konfiguration kommt aus Umgebungsvariablen und
optional `.env`. Uvicorn betreibt Frontend und API im selben Prozess.

## Umgesetzte Entscheidungen

| Entscheidung | Nutzen und Grenze |
| --- | --- |
| FastAPI/Pydantic | API-Validierung und Swagger; benötigt ASGI-Server |
| HTML/CSS/JavaScript ohne Build-Schritt | Oberfläche ohne Node.js oder zusätzliche Laufzeit-Abhängigkeiten |
| Englische PokéAPI-Namen | Eindeutige Eingaben; deutsche Namen noch nicht unterstützt |
| Typfaktoren und gewichtete Basiswerte | Erklärbarer Score; keine Kampfsimulation |
| Höchstens drei Angriffstypen und fünf Kandidaten je Typ als Standard | Begrenzte externe Last; keine globale Bestenauswahl |
| Asynchroner HTTP-Client, fünf gleichzeitige Aufrufe | Begrenzte Parallelität und Verbindungswiederverwendung |
| In-Memory-Cache | Keine Datenbank nötig; Verlust bei Neustart, keine Instanzsynchronisierung |
| Lokale Tabelle aller 18 modernen Typen | Typanalysen bei Ausfall; unbekannte Pokémon offline nicht auflösbar |
| Windows-Launcher | Selbstständiger Start und Einrichtung; Python muss vorhanden sein |
| Eigener lokaler Port 8765 | Trennung von BeerScales Offline-Cache auf 8000 |
| GitHub Actions und Render-Blueprint | Automatisierung vorbereitet; Cloud-Nachweise noch offen |

Details zu Score, Konfiguration und Fehlercodes stehen in der [README](../README.md).

## Nachweisstand

| Datum | Prüfung | Ergebnis und Reichweite |
| --- | --- | --- |
| 23.09.2026 | Automatisierte API-Tests | 54 bestanden |
| 23.09.2026 | `pip check` | Keine Abhängigkeitskonflikte |
| 23.09.2026 | `pip-audit` nach Paketupdates | Keine damals bekannten Schwachstellen; kein dauerhafter Sicherheitsnachweis |
| 23.09.2026 | Echte PokéAPI und Fallback-Tabelle | Live-Test erfolgreich, alle 18 Typbeziehungen abgeglichen |
| 23.09.2026 | Einzelner Cache-Aufruf | Ungefähr 4 ms lokal; kein Lasttest oder p95 |
| 29.09.2026 | Suite mit Oberflächen-/Asset-Test | 55 bestanden; Warnungen zu TestClient und pytest-Cache-Schreibrechten |
| 29.09.2026 | Browserbedienung | Charizard, Water, Top 3 und unbekanntes Pokémon erfolgreich geprüft |
| 29.09.2026 | Responsive Darstellung | Schmaler und Desktop-Viewport geprüft, kein horizontaler Überlauf bei den gemessenen Größen |
| 29.09.2026 | Launcher `--check` | Abhängigkeiten und Port-Erkennung erfolgreich |
| 29.09.2026 | Port 8000 untersuchen | Direkte Antwort war Pokémon; Browser zeigte alte BeerScale-Offlineseite |
| 29.09.2026 | Umstellung auf 8765 | HTTP 200, Pokémon-Titel, kein BeerScale in der Serverantwort |
| 29.09.2026 | Benutzerbestätigung | Anwendung funktioniert nach Umstellung und Cache-Anleitung |

Die Ergebnisse sind dokumentierte Prüfläufe, keine bei jeder Dokumentations-
änderung erneut ausgeführten Tests. Die Launcher-Ersteinrichtung in einer
komplett frischen Windows-Umgebung wurde noch nicht separat nachgewiesen.
Die Benutzerbestätigung belegt die gelöste Anzeige; welche DevTools-Checkboxen
tatsächlich betätigt wurden, wurde nicht technisch aufgezeichnet.

## Abdeckung des Projektauftrags

| Bereich | Lokal vorhanden | Noch offen |
| --- | --- | --- |
| Softwareentwicklung/DevOps | Modulare API, Browser-UI, Modelle, Tests, Startdatei | Vollständig frische Installation nachweisen |
| CI/CD/Git | Git-Repository, Actions-Workflow, Render-Konfiguration | Grüner Online-CI-Lauf, Branch-Schutz, Deployment und Re-Deployment |
| AI Ops/Beobachtbarkeit | JSON-Logs, Health, Ready, Cache-/Fallback-Ereignisse | Dashboard, Alarme und Cloud-Lognachweise |
| Maturity Levels | Lokaler reproduzierbarer und getesteter MVP | Automatisierten Cloud-Betrieb belegen |
| Infrastrukturentscheidungen | Entscheidungen und Grenzen dokumentiert | Cloud-Messungen ergänzen |
| Security | Validierung, Limits, sichere Fehler, Audit-Schritt | Audit erneut vor Veröffentlichung, Proxy-Verhalten und Limits auf Render prüfen |

Dies ist eine projektspezifische Reifegradbewertung, keine externe Zertifizierung.
Das MVP enthält keine trainierte KI und keinen Sprachmodell-Aufruf; die
Counter-Rangfolge ist eine deterministische Heuristik.

## Bekannte Grenzen

- Counter-Pool in PokéAPI-Reihenfolge kann stärkere spätere Kandidaten auslassen.
- Fähigkeiten, Moves, Items und defensive Matchups sind nicht modelliert.
- Fallback kann Schwächen ohne Empfehlungen liefern; unbekannte Pokémon können
  bei Upstream-Ausfall HTTP 503 auslösen.
- Cache und Rate-Limit sind pro Prozess; mehrere Worker würden getrennte
  Zustände führen. Der vorgesehene MVP nutzt einen Worker.
- Ready mit frischem Cache ist kein aktueller Beleg der PokéAPI-Erreichbarkeit.
- Ein Health-Status sagt nichts über die Vollständigkeit einer Analyse aus.
- Direkte Pakete sind gepinnt, ein vollständiges transitives Lockfile fehlt.
- Die TestClient-Deprecation zur künftigen httpx2-Umstellung ist noch offen.
- Browser-Offline-Caches fremder Projekte werden nicht automatisch gelöscht.

## Nächste Schritte in Reihenfolge

1. Lokale UI-, Launcher- und Dokumentationsänderungen gemeinsam committen und
   pushen. Ausgangscommit der bereits gespeicherten API: `dffcf30`.
2. GitHub Actions für den betreffenden Commit prüfen, Audit bei Bedarf
   aktualisieren und Branch-Schutz für `main` einrichten.
3. Render anhand von `render.yaml` verbinden, deployen und die tatsächliche
   URL in der README dokumentieren.
4. Cloud-Smoke-Test sowie manuelle Prüfung von `/` durchführen; Proxy-IP,
   Rate-Limit, Logs, Cache/Fallback und automatisches Re-Deployment nachweisen.
5. Last-, p95- und Kaltstartmessungen sowie Betriebsgrenzen und Alarmschwellen
   dokumentieren; Abschlussbericht um die echten Cloud-Ergebnisse ergänzen.
6. Danach Abhängigkeiten vollständig locken, TestClient-Migration prüfen und
   bei mehreren Instanzen einen gemeinsamen Cache/Rate-Limiter vorsehen.

Die konkreten Schritte stehen in [DEPLOYMENT.md](DEPLOYMENT.md).
Aktuell sind keine Cloud-Ergebnisse oder öffentliche Service-URL erfunden
oder als erledigt markiert.
