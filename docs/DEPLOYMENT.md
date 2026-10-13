# GitHub und Render einrichten

Diese Anleitung veröffentlicht die Pokémon-API aus diesem Projekt.
GitHub speichert den Code und prüft ihn mit GitHub Actions. Render betreibt
anschließend die API unter einer öffentlichen HTTPS-Adresse.

## 1. Ausgangslage

Lokal ist `origin` bereits auf dieses Repository eingestellt:
[xTh0masx/Pok-mon_Counter-Weakness_API](https://github.com/xTh0masx/Pok-mon_Counter-Weakness_API).
Der Ausgangsbranch ist `main`. Die API-Basis ist bereits im lokalen Commit
`dffcf30` (First Local Demo Version) enthalten. Am 29.09.2026 waren die neue
Browser-Oberfläche, der Launcher und Dokumentationsänderungen noch lokal
uncommitted. Vor dem Fortfahren mit `git status` den tatsächlichen Stand prüfen.
Ein neues Repository oder erneutes `git init` ist nicht erforderlich.

Vorbereitet sind `.github/workflows/ci.yml`, `render.yaml`, `.python-version`
und `scripts/smoke_test.py`. Eine Datenbank wird für diese API nicht benötigt.

## 2. Code auf GitHub bereitstellen

Öffne das Terminal in PyCharm. Führe die Befehle nacheinander aus und fahre
bei einem Fehler erst nach dessen Behebung fort:

```powershell
Set-Location 'C:\Users\thoma\PycharmProjects\Pok-mon_Counter-Weakness_API'
git status
git remote -v
.\.venv\Scripts\python.exe -m pytest -q
git switch -c codex/cloud-setup
git add App Tests scripts docs Start-Pokemon.bat README.md requirements.txt requirements-dev.txt pytest.ini .github .env.example .gitignore .python-version render.yaml
git diff --cached --stat
git commit -m "Add Pokemon interface, local launcher and documentation"
git push -u origin codex/cloud-setup
```

Die Dateiliste vor dem Commit prüfen. `.env`, `.venv` und IDE-Dateien werden
ignoriert; `.env.example` ist die freigegebene Konfigurationsvorlage.
Wenn `codex/cloud-setup` bereits existiert, zunächst `git status` prüfen und
mit `git switch codex/cloud-setup` zum vorhandenen Branch wechseln.

Wenn Git nach Name/E-Mail fragt, trage deine tatsächlichen Werte lokal für
dieses Repository ein und wiederhole den Commit:

```powershell
git config user.name "DEIN NAME"
git config user.email "DEINE GITHUB-E-MAIL ODER NOREPLY-ADRESSE"
```

Bei einer GitHub-Anmeldung den angebotenen Browser-Login abschließen.
Alternativ kannst du das GitHub-Konto in PyCharm unter
**Settings → Version Control → GitHub** hinzufügen und über **Git → Push** pushen.
Bei `Repository not found` prüfen, ob du im richtigen GitHub-Konto angemeldet
bist und das verknüpfte Repository öffnen kannst.

Der Ablauf verwendet einen eigenen Branch und anschließend einen Pull Request.
Grundlage: [GitHub-Anleitung für lokalen Code](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github).

## 3. CI prüfen und nach main übernehmen

1. Öffne das Repository auf GitHub und wähle **Compare & pull request**.
   Falls die Schaltfläche fehlt: **Pull requests → New pull request**.
2. Setze **base: main** und **compare: codex/cloud-setup**.
3. Erstelle den Pull Request, beispielsweise mit dem Titel
   `Pokémon API mit Tests und Deployment-Konfiguration`.
4. Öffne **Actions → CI** oder die Checks des Pull Requests. Der Job `test`
   installiert Abhängigkeiten, führt `pytest` und anschließend `pip-audit` aus.
5. Erst bei erfolgreichem Job den Pull Request mit **Merge pull request**
   oder **Squash and merge** übernehmen.
6. Unter **Actions** auch den durch den Merge ausgelösten Lauf auf `main`
   prüfen. Dieser Commit soll später auf Render laufen.

Die Pipeline benötigt keine selbst angelegten Secrets. Falls Actions für das
Repository deaktiviert ist, unter **Settings → Actions → General** aktivieren
und die verwendeten GitHub-Actions zulassen. Bei Fehlern den fehlgeschlagenen
Schritt öffnen; Audit-Probleme durch Paketupdates beheben und erneut pushen.

Die CI lässt sich nach Übernahme auf `main` auch unter **Actions → CI → Run
workflow** manuell starten. Das Zeitlimit pro Job beträgt zehn Minuten.

Danach den lokalen Hauptbranch aktualisieren:

```powershell
git switch main
git pull --ff-only origin main
```

## 4. main schützen

Nach dem ersten erfolgreichen CI-Lauf unter **Settings → Branches → Add
classic branch protection rule** eine Regel für `main` erstellen:

- **Require a pull request before merging** aktivieren.
- **Require status checks to pass before merging** aktivieren und den
  tatsächlich angezeigten Check des Jobs `test` auswählen.
- **Require branches to be up to date before merging** aktivieren.
- Für ein Einzelprojekt keine verpflichtende fremde Review-Freigabe verlangen,
  solange kein zweiter Reviewer vorhanden ist.

Falls der Check noch nicht angeboten wird, zuerst einen vollständigen CI-Lauf
ausführen. Branch-Schutz ist bei GitHub Free für öffentliche Repositories
verfügbar; bei privaten Repositories hängt er vom Tarif ab. Ein privates
Repository muss dafür nicht ungeprüft öffentlich gemacht werden.
[Einrichtung](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule),
[Verfügbarkeit](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).

## 5. Render verbinden

1. Öffne das [Render-Dashboard](https://dashboard.render.com/) und melde dich an.
2. Wähle **New → Blueprint**.
3. Verbinde GitHub und erlaube Render Zugriff auf
   `Pok-mon_Counter-Weakness_API`.
4. Wähle beim Repository **Connect**.
5. Blueprint-Name: beispielsweise `pokemon-api`; Branch: `main`;
   Blueprint Path: `render.yaml`.
6. Prüfe die Vorschau: ein Web Service namens `pokemon-counter-api`, Plan
   **Free**, keine Datenbank. Dann **Deploy Blueprint** wählen.

Die Datei im Repository definiert die Infrastruktur; einen zusätzlichen
manuellen Web Service brauchst du nicht anzulegen.
[Render-Blueprint-Anleitung](https://render.com/docs/infrastructure-as-code).

## 6. Service-Einstellungen prüfen

| Einstellung | Wert in diesem Projekt |
| --- | --- |
| Runtime | Python |
| Branch | `main` |
| Root Directory | leer, Repository-Wurzel |
| Python | `3.12` aus `.python-version` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn App.main:app --host 0.0.0.0 --port $PORT --no-access-log` |
| Health Check Path | `/health` |
| Auto-Deploy | After CI Checks Pass (`checksPass`) |
| Instanz | Free, ein Worker |

`App` muss großgeschrieben sein. Den Startbefehl ohne `--reload` verwenden.
`$PORT` wird auf Render bereitgestellt; nicht durch den lokalen Port `8765`
oder den früher verwendeten Port `8000` ersetzen. Der Windows-Launcher ist
nur für den lokalen Betrieb vorgesehen und wird auf Render nicht gestartet.
PokéAPI benötigt keinen API-Key. Die Standardkonfiguration reicht für den
ersten Start; optionale Werte aus `.env.example` kommen unter **Environment**.

`.python-version` darf die Kurzform `3.12` enthalten. Eine separat gesetzte
Variable `PYTHON_VERSION` hätte Vorrang und müsste eine vollständige Version
enthalten. Für dieses Projekt die vorhandene Datei verwenden.
[Render-Python-Version](https://render.com/docs/python-version).

`checksPass` steuert automatische Code-Deployments nach neuen Commits. Daher
den ersten Blueprint erst nach einem grünen `main`-Lauf anlegen. Änderungen
der Blueprint-Konfiguration und manuelle Deployments separat prüfen.
Automatische Deployments erfordern die GitHub-Verbindung; nur eine öffentliche
Repository-URL zu hinterlegen genügt dafür nicht. Wenn Render keine Checks
findet oder ein Check fehlschlägt, erfolgt kein automatisches Code-Deployment.
[Render CI-Integration](https://render.com/docs/deploys).

## 7. Öffentliche Anwendung testen

Im Service unter **Events/Deploys** und **Logs** den Build verfolgen. Sobald
der Dienst läuft, die tatsächliche `https://…onrender.com`-Adresse aus dem
Dashboard kopieren. Der Name der URL kann einen Zusatz enthalten.

Im Browser nacheinander öffnen:

- `https://DEIN-SERVICE.onrender.com/health`: `{"status":"ok"}`.
- `https://DEIN-SERVICE.onrender.com/`: Pokémon Counter Lab mit Suchformular.
- `https://DEIN-SERVICE.onrender.com/docs`: Swagger mit Pokémon-Titel.
- `https://DEIN-SERVICE.onrender.com/ready`: `ready` oder begründet `degraded`.

Die Browser-Oberfläche befindet sich unter `/`; dort einen Namen eingeben und
**Find counters** anklicken. Alternativ in Swagger unter `/docs` bei
**POST /api/v1/analyze → Try it out** senden:

```json
{"query":"charizard","input_type":"auto","limit":3}
```

Erwartet: `fire` und `flying`, `rock` mit Faktor 4 sowie bis zu drei Counter.
Den gleichen Request wiederholen: `cache_used` sollte `true` werden.

Danach im lokalen Projektterminal die echte URL einsetzen:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_test.py --base-url https://DEIN-SERVICE.onrender.com
```

Ohne Fehler endet das Skript mit Exitcode 0. Es prüft Health, Swagger,
Charizard, Cache, 404, 422 und Ready. Für den Cloud-Test laufen die
Analyse-Aufrufe auf Render, nicht auf dem lokalen Server.

Free-Dienste schlafen nach 15 Minuten ohne eingehenden Traffic ein. Das
Aufwachen dauert ungefähr eine Minute: zuerst `/health` im Browser laden,
danach den Smoke-Test starten. Ein Kaltstart kann sonst dessen 60-Sekunden-
Timeout überschreiten. Cache-Daten gehen beim Neustart verloren.
[Render-Free-Betrieb](https://render.com/docs/free).

## 8. Re-Deployment und Abgabe nachweisen

Nach dem ersten Cloud-Test die echte Service-URL in der README ergänzen.
Dazu einen neuen Branch anlegen, die Änderung committen und pushen, einen
Pull Request öffnen, CI abwarten und nach `main` mergen. Render muss den
neuen Commit automatisch deployen. Anschließend den Smoke-Test wiederholen.

Folgende Nachweise im Projektbericht festhalten:

| Nachweis | Einzutragen |
| --- | --- |
| GitHub | Repository-URL und Link zum erfolgreichen CI-Lauf auf main |
| Deployment | Render-URL, Commit-SHA und Deployment-Zeitpunkt |
| Funktion | Charizard-Antwort mit rock ×4 und Counter-Liste |
| Cache | Wiederholte Anfrage mit cache_used true |
| Betrieb | Health, Ready und Log mit Correlation-ID/Status/Dauer |
| Automatisierung | Zweiter Commit mit grünem CI und anschließendem Render-Deployment |

Noch separat offen: Proxy-/Client-IP-Verhalten des Rate-Limits auf Render,
kontrollierter Ausfallnachweis, Lasttest mit p95 und Abschlussdokumentation.

## Häufige Probleme

| Problem | Nächster Schritt |
| --- | --- |
| Repository fehlt bei Render | GitHub-App-Zugriff auf dieses Repository freigeben |
| `No module named App` | Root Directory und Großschreibung im Startbefehl prüfen |
| Build findet ein Paket nicht | Python-Version und erste Fehlermeldung des pip-Schritts prüfen |
| Deployment wartet | CI-Lauf desselben main-Commits und GitHub-Verbindung prüfen |
| 404 bei `/` | Prüfen, ob der Commit mit `App/static` und der neuen Root-Route deployed wurde; `/docs` bleibt die API-Dokumentation |
| 503 bei Analyse | Render-Logs auf upstream_error prüfen; Typanalyse mit `water` testen |
| 429 bei wiederholten Tests | Retry-After abwarten; Proxy-/Client-IP-Konfiguration prüfen |
| Git meldet abweichenden Remote-Stand | Nicht erzwingen; Änderungen zunächst mit dem Remote-Branch abgleichen |

Stand dieser Anleitung: 29.09.2026. Ein erfolgreicher GitHub-CI-Lauf und eine
öffentliche Render-Bereitstellung sind noch nicht nachgewiesen. Die lokale
Bedienung und Cache-Bereinigung stehen in [LOCAL_USAGE.md](LOCAL_USAGE.md),
der Nachweisstand in [PROJECT_STATUS.md](PROJECT_STATUS.md).
