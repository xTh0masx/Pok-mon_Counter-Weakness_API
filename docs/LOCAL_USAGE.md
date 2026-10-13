# Pokémon Counter Lab lokal verwenden

Stand: 29.09.2026. Die Anwendung wurde lokal geprüft und vom Benutzer als
funktionierend bestätigt. Die Oberfläche und die API laufen gemeinsam.

## Start per Doppelklick

1. Den Projektordner `Pok-mon_Counter-Weakness_API` im Explorer öffnen.
2. `Start-Pokemon.bat` doppelklicken.
3. Das Konsolenfenster geöffnet lassen. Die Anwendung öffnet sich im
   Standardbrowser unter **http://127.0.0.1:8765/**.
4. Falls eine andere Adresse im Fenster steht, diese verwenden.

Python 3.12 ist die getestete und empfohlene Version. Der Python-Launcher
akzeptiert Versionen ab 3.12; andere Versionen wurden hier nicht geprüft.
Die Batch-Datei sucht zuerst eine funktionierende Projektumgebung, dann
`py -3.12` und anschließend `python` im PATH.

Beim ersten Start erstellt der Launcher bei Bedarf `.venv`, prüft die
installierten direkten Paketversionen und installiert fehlende oder abweichende
Laufzeit-Abhängigkeiten aus `requirements.txt`. Eine fehlende `.env` wird aus
`.env.example` angelegt; vorhandene Konfiguration wird beibehalten.
Für Paketdownloads und aktuelle PokéAPI-Daten wird Internet benötigt.

Der Launcher startet keine Datenbank, keinen Docker-Container und keinen
separaten Frontend-Server. Er benötigt im normalen Benutzerbetrieb keine
Administratorrechte und installiert Python selbst nicht.

## Startoptionen

Im PowerShell-Terminal im Projektordner:

```powershell
.\Start-Pokemon.bat --check
.\Start-Pokemon.bat --no-browser
.\Start-Pokemon.bat --port 8100
```

| Option | Verhalten |
| --- | --- |
| ohne Option | Einrichtung prüfen, App starten und Browser öffnen |
| `--check` | Abhängigkeiten und Port prüfen; keine Installation und kein Serverstart |
| `--no-browser` | Server starten, Browser nicht automatisch öffnen |
| `--port 8100` | Ab diesem Port statt 8765 suchen |

Die Portsuche prüft den gewünschten Port und bis zu zehn folgende Ports.
Mit Standardwert sind das 8765–8775. Eine dort erkannte Pokémon-Oberfläche
wird wiederverwendet, ein anderer Server wird nicht beendet. Die Erkennung
verwendet den HTML-Titel der lokalen Antwort und ist keine Authentifizierung.

Bei erfolgreichem Check endet das Python-Skript mit Exitcode 0; fehlende
Abhängigkeiten ergeben 1. Für Skripte mit Exitcode-Auswertung direkt
`.\.venv\Scripts\python.exe scripts/start_local.py --check` verwenden.
Die Batch-Datei ist interaktiv und wartet am Ende auf einen Tastendruck.

## Anwendung bedienen

1. In **Pokémon or type** beispielsweise `charizard` eingeben.
2. **Search as** auf **Auto-detect** lassen oder gezielt Pokémon/Type wählen.
3. Unter **Counters** Top 3, Top 5 oder Top 10 auswählen.
4. **Find counters** anklicken oder im Eingabefeld Enter drücken.

Die Schnellwahl **Charizard**, **Pikachu** oder **Water** führt die jeweilige
Suche direkt im Modus Auto-detect aus. Englische Namen verwenden; `Glurak`
wird nicht automatisch übersetzt.

Das Ergebnis zeigt Zieltypen, Schwächen und Counter mit Score bis 10.
Beispiel Charizard: Feuer/Flug, Gestein ×4, Elektro ×2, Wasser ×2.
Bei eingeschränkten Daten erscheinen Warnungen. **View API response** zeigt
die JSON-Antwort. **API docs** öffnet die technische Swagger-Dokumentation.

Die Anzahl der Empfehlungen kann kleiner als die gewählte Obergrenze sein.
Die Auswahl basiert auf einem begrenzten Kandidatenpool, nicht auf allen
Pokémon oder einer vollständigen Kampfsimulation.

## Beenden und erneut starten

- Im Fenster, das den Server gestartet hat, **Strg+C** drücken.
- Danach kann die Batch-Datei noch auf einen Tastendruck warten; das Fenster
  anschließend schließen.
- Wurde nur ein bereits laufender Server erkannt, gehört dieser zum früheren
  Startvorgang. Das neue Launcher-Fenster beendet ihn nicht.
- Das Schließen des Browser-Tabs beendet keinen Server.
- Nach Codeänderungen den Server neu starten. Der Doppelklick-Launcher nutzt
  absichtlich keinen automatischen Reload.

Für die Entwicklung kann stattdessen folgender Befehl verwendet werden:

```powershell
.\.venv\Scripts\python.exe -m uvicorn App.main:app --reload --host 127.0.0.1 --port 8765 --no-access-log
```

## Lokale Adressen

| Adresse | Zweck |
| --- | --- |
| `http://127.0.0.1:8765/` | Browser-Oberfläche |
| `http://127.0.0.1:8765/docs` | Swagger/API ausprobieren |
| `http://127.0.0.1:8765/health` | Prozessstatus ohne PokéAPI-Aufruf |
| `http://127.0.0.1:8765/ready` | Datenbereitschaft oder eingeschränkter Betrieb |

Bei einem Ausweichport alle Adressen entsprechend anpassen. Die Bindung an
127.0.0.1 beschränkt den Launcher auf diesen Computer. Eine öffentliche URL
entsteht erst durch das gesonderte Render-Deployment.

## BeerScale oder eine alte Seite erscheint

### Beobachtung und Ursache

Unter `http://127.0.0.1:8000/` erschien im Browser BeerScale mit Offline-Anzeige.
Ein direkter HTTP-Abruf lieferte gleichzeitig HTTP 200 und den Titel
`Pokémon Counter Lab`, ohne BeerScale-Inhalt. Im BeerScale-Projekt wurde eine
Registrierung für `/service-worker.js` und der Cache `beerscale-v9` gefunden.
Diese Befunde erklären die Anzeige als alte Offline-Seite im Browser und
nicht als falsche Pokémon-Serverantwort.

Die Pokémon-Anwendung selbst registriert keinen Service Worker. Der lokale
Standardport wurde auf **8765** umgestellt. Dadurch verwenden die beiden
Projekte unterschiedliche Browser-Ursprünge und teilen diese Offline-Caches
nicht mehr. Launcher, Startanleitung und lokale API-Beispiele wurden angepasst.
Der Benutzer bestätigte anschließend, dass es funktioniert.

### Alten Cache in Chrome gezielt entfernen

1. Genau `http://127.0.0.1:8000/` öffnen, also den betroffenen alten Ursprung.
2. **F12** oder **Strg+Umschalt+I** drücken.
3. **Application** öffnen, bei Bedarf über das Menü **»**.
4. Links **Storage** auswählen.
5. **Unregister service workers** und **Cache storage** auswählen.
   Cookies, Local Storage und IndexedDB abwählen, um dort gespeicherte
   Einstellungen und Daten zu erhalten.
6. **Clear site data** anklicken.
7. Alle Tabs dieses Ursprungs schließen und bei Bedarf erneut öffnen.

Die Bereinigung betrifft den gewählten Ursprung, nicht sämtliche Websites.
Ein normales Neuladen allein entfernt einen registrierten Service Worker
nicht zuverlässig. `localhost:8000` und `127.0.0.1:8000` sind unterschiedliche
Ursprünge; bei Problemen auf beiden Adressen die Schritte jeweils wiederholen.
Beim erneuten Besuch einer laufenden BeerScale-App kann diese ihren Worker
wieder registrieren. Pokémon deshalb weiterhin auf 8765 verwenden.

Quelle für die DevTools-Funktionen:
[Chrome-Dokumentation zu Service Workern und Cache](https://developer.chrome.com/docs/devtools/progressive-web-apps).

### Browser-Cache und API-Cache unterscheiden

Der Browser-Cache speichert Webseiten und kann alte Oberflächen anzeigen.
Der Pokémon-TTL-Cache speichert PokéAPI-Ressourcen im Arbeitsspeicher des Servers.
`cache_used: true` ist normales API-Verhalten und kein BeerScale-Problem.
Der API-Cache wird durch Serverneustart geleert, nicht durch Chrome DevTools.

## Weitere Fehlerhilfe

| Symptom | Vorgehen |
| --- | --- |
| Python nicht gefunden | Python 3.12 samt Launcher/PATH installieren, erneut starten |
| Unvollständige `.venv` | Server stoppen, alten Ordner zur Sicherung umbenennen, neu starten |
| Paketinstallation schlägt fehl | Internetverbindung und Fehlermeldung im Fenster prüfen |
| Browser öffnet sich nicht | Im Fenster ausgegebene URL manuell öffnen |
| Verbindung abgelehnt | Launcher starten; richtigen Port aus dessen Ausgabe verwenden |
| Keine Pokémon-Daten | Englisch schreiben; bei Ausfall eine Typanalyse wie `water` versuchen |
| Zu viele Anfragen/429 | Angezeigte Wartezeit abwarten |
| Neue Codeänderung erscheint nicht | Bestehenden Server beenden und neu starten, Browser neu laden |

## Danach

Die lokale Bedienung ist bestätigt. Als Nächstes die Änderungen committen,
GitHub CI prüfen, Render bereitstellen und die Cloud-Abnahme durchführen.
Siehe [Deployment-Anleitung](DEPLOYMENT.md) und [Projektstatus](PROJECT_STATUS.md).
