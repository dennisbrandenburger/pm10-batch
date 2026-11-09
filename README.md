# PM10-Datenpipeline

Die Pipeline verarbeitet stündliche PM10-Messungen der US-Umweltbehörde EPA. Sie lädt die Daten herunter, prüft sie und fasst sie je Messreihe zu Tageswerten zusammen. Die Ergebnisse werden mit Angaben zu Herkunft und Qualität in PostgreSQL gespeichert und können später für Analysen oder Modellversuche genutzt werden.

Der geprüfte Datensatz für 2024 enthält **3.870.976 Beobachtungen**. Daraus wurden **163.381 Tagesdatensätze** berechnet und unabhängig nachgeprüft. Die Ergebnisse stehen im [Prüfbericht](evidence/Pruefbericht.md).

## Schnellstart

Benötigt werden Git, Python 3 und Docker mit Compose und Linux-Containern. Die folgenden Befehle sind für eine Shell unter Linux oder macOS gedacht. Unter Windows ist eine WSL-2-Distribution mit aktivierter [Docker-Integration](https://docs.docker.com/desktop/features/wsl/) vorgesehen. Für Docker sollten vier CPU-Kerne, 6 GiB RAM und 8 GiB freier Plattenplatz verfügbar sein.

Das Repository in dieser Shell klonen:

```sh
git clone https://github.com/dennisbrandenburger/pm10-batch.git
cd pm10-batch
```

Wer unter macOS Colima verwendet, startet vor dem ersten Lauf die Docker-VM:

```sh
colima start --profile de-pm10 --cpu 4 --memory 6 --activate=false
export DOCKER_CONTEXT=colima-de-pm10
```

Anschließend im Repository-Verzeichnis:

```sh
./scripts/setup.sh
docker compose build transform
./scripts/run.sh 2024
```

`setup.sh` erzeugt die Zugangsdaten und übernimmt die lokale Benutzer- und Gruppen-ID für die Dateirechte im Container. `run.sh` startet die Datenbank, lädt die Quelldatei und verarbeitet sie, wenn sich Daten oder Rechenrezept geändert haben. Auch veränderte Ergebnisdaten lösen eine Neuberechnung aus. Der Datenbankport wird nicht am Host freigegeben.

Ist Compose als `docker-compose` installiert, erkennen die Skripte das automatisch. In den Befehlen dieser Anleitung muss dann ebenfalls `docker-compose` statt `docker compose` stehen.

## Komponenten

| Dienst | Aufgabe | Dauerhafte Daten |
|---|---|---|
| `ingest` | Archiv herunterladen und Größe, ZIP-CRC, Dateiname, Spalten und SHA-256 prüfen | Original-ZIP und Abrufprotokolle in `runtime/raw` und `runtime/manifests` |
| `transform` | Daten mit Spark prüfen, Tageswerte berechnen und in PostgreSQL speichern | Laufberichte, zurückgestellte Datensätze und Tagesexporte in `runtime/runs` |
| `database` | Tageswerte und Verarbeitungsläufe speichern | Docker-Volume `postgres_data` |
| `test` | Qualitätsregeln und Datenbanktransaktionen an gezielten Beispielen prüfen | Separate Testdatenbank `pm10_test` |

Die Verarbeitungsdienste nutzen dasselbe Image, laufen aber in getrennten Containern. PostgreSQL hat ein eigenes Image. Die Basis-Images sind über Digests festgelegt, die Python-Pakete über Versionsnummern.

## Aufbau des Codes

`scripts/run.sh` führt Datenaufnahme und Verarbeitung nacheinander aus. Die zugehörigen Befehle sind in `pm10/__main__.py` definiert. Die Aufgaben verteilen sich auf drei Module: `pm10/ingest.py` lädt und prüft das Archiv, `pm10/transform.py` berechnet die Tageswerte und `pm10/store.py` prüft den vorhandenen Datenstand und speichert neue Ergebnisse in einer Datenbanktransaktion.

Die Dienste und ihre Verbindungen stehen in `compose.yaml`, die Qualitätsregeln in `config/quality.json` und das Datenbankschema in `sql/schema.sql`. Tests liegen unter `tests/`, Prüfprotokolle unter `evidence/`.

## Was gespeichert wird

Eine Messreihe wird durch Bundesstaat, County, Standort, Parameter und POC identifiziert. POC unterscheidet mehrere Messreihen am selben Standort. Ein Tagesdatensatz enthält unter anderem:

- Datum in **lokaler Standardzeit**, nicht nach Sommerzeit umgerechnet.
- Zahl beobachteter und verwendeter Stunden.
- Mittelwert, Minimum und Maximum der verwendeten Werte.
- Zahl negativer Werte, Qualitätskennzeichen und Ereignishinweise.
- Einen Vergleichsmittelwert vor dem Zurückstellen bekannter Qualitätsprobleme.
- Kennzeichnung, ob mindestens 18 verwendbare Stunden und genau eine Messmethode vorliegen.
- Verknüpfung zum Verarbeitungslauf und zum Originalarchiv.

Über die Datenbanksicht `model_candidates` lassen sich Tage mit mindestens 18 verwendbaren Stunden und genau einer Messmethode abfragen. Die Qualitätszähler sind dort ebenfalls enthalten. Die Auswahl dient der späteren Analyse und ist keine amtliche Gültigkeitsbewertung.

## Ergebnis ansehen

```sh
docker compose run --rm transform status
docker compose exec -T database psql -U pm10 -d pm10 -c \
  'SELECT state, county, site, poc, day, n_usable, mean_pm10, n_negative
   FROM model_candidates
   ORDER BY state, county, site, poc, day
   LIMIT 10;'
```

Alle Tagesdatensätze liegen in `daily_feature`. In `pipeline_run` stehen die erfolgreichen, fehlgeschlagenen oder unterbrochenen Läufe. `active_dataset` zeigt, welcher Stand aktuell verwendet wird.

## Tests und Nachweise

```sh
./scripts/test.sh
```

Die zehn Tests prüfen unter anderem Zeitgrenzen, Qualitätsregeln, doppelte und widersprüchliche Beobachtungen, unvollständige Tage sowie Rollback und Wiederholungsschutz. Die Datenbanktests laufen in der separaten Datenbank `pm10_test`. Die Nachrechnung des vollständigen Datensatzes und die Wiederherstellung einer Sicherung sind in `evidence/` dokumentiert.

Die Zeilenzahlen in diesem Projekt beziehen sich auf den geprüften EPA-Datenstand. Da die Jahresdatei bei jedem Aufruf von `run.sh` neu heruntergeladen wird, können spätere Änderungen der Quelle zu anderen Zahlen führen. Ob dieselbe Datei vorliegt, zeigt ein Vergleich der SHA-256-Prüfsummen in `runtime/source-2024.json` und `evidence/source-2024.json`. Die unabhängige Nachrechnung mit `scripts/reference_check.py` gilt nur für diesen Referenzbestand.

Nach dem vollständigen Lauf lässt sich diese Nachrechnung so ausführen:

```sh
docker compose run --rm --entrypoint /app/scripts/entrypoint.sh transform \
  python3 /app/scripts/reference_check.py
```

Weitere Erläuterungen:

- [Qualitätsregeln und Grenzen](docs/qualitaet.md)
- [Architektur und Entscheidungen](docs/architektur.md)
- [Betrieb, Wiederanlauf und Sicherung](docs/betrieb.md)
- [Quellen und Herkunft](docs/quellen.md)
- [Nachweise](evidence/)

## Projektgrenzen

Die Pipeline wurde auf einem ARM64-Mac getestet. Am 09.11.2026 wurde sie zusätzlich aus einer frischen GitHub-Kopie mit neuen Zugangsdaten und leerer Datenbank aufgebaut. Dabei entstanden [dieselben Ergebnisse wie beim ersten Lauf](evidence/reproduction-check.json). Ein zweiter Rechner, Windows/WSL und ein verteilter Spark-Cluster wurden bisher nicht getestet.

Ein ML-Modell gehört nicht zum Projekt. Vor einer solchen Erweiterung müssten unter anderem die Zielvariable, die zeitliche Aufteilung der Trainings- und Testdaten und der Einfluss der Qualitätsauswahl untersucht werden.
