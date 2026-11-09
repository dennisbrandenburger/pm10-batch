# PM10-Datenpipeline

Die Pipeline lädt stündliche PM10-Messungen der US-Umweltbehörde EPA, prüft die Daten und berechnet Tagesmerkmale je Messreihe. Die Ergebnisse stehen in PostgreSQL für Analysen und spätere Modellversuche bereit.

Der geprüfte Datensatz für 2024 umfasst **3.870.976 Beobachtungen**. Daraus entstehen **163.381 Tagesdatensätze**, die unabhängig nachgerechnet wurden. Ergebnisse und Testprotokolle stehen im [Prüfbericht](evidence/Pruefbericht.md).

## Schnellstart

Voraussetzungen: Git, Python 3 und eine laufende Docker-Umgebung mit Compose und Linux-Containern. Die Shell-Befehle sind für Linux und macOS vorgesehen. Unter Windows werden sie in einer WSL-2-Distribution mit aktivierter [Docker-Integration](https://docs.docker.com/desktop/features/wsl/) ausgeführt. Für die Docker-VM sind 6 GiB RAM und vier CPU-Kerne vorgesehen. Empfohlen werden 8 GiB freier Plattenplatz.

Repository in dieser Shell holen und in das Verzeichnis wechseln:

```sh
git clone https://github.com/dennisbrandenburger/pm10-batch.git
cd pm10-batch
```

Optional unter macOS mit Colima, vor dem ersten Lauf:

```sh
colima start --profile de-pm10 --cpu 4 --memory 6 --activate=false
export DOCKER_CONTEXT=colima-de-pm10
```

Im Repository-Verzeichnis:

```sh
./scripts/setup.sh
docker compose build transform
./scripts/run.sh 2024
```

`setup.sh` erzeugt lokale Zugangsdaten und die UID/GID-Konfiguration. `run.sh` startet die Datenbank, lädt die Quelle und verarbeitet sie bei Änderungen erneut. Der Datenbankport bleibt innerhalb des Compose-Netzwerks.

Wo `docker compose` nicht als Plugin installiert ist, verwenden die Skripte automatisch `docker-compose`. Die allgemeinen Befehle lassen sich entsprechend ersetzen.

## Komponenten

| Dienst | Aufgabe | Dauerhafte Daten |
|---|---|---|
| `ingest` | HTTPS-Download, Größenlimit, ZIP-CRC, Dateiname, Spalten und SHA-256 prüfen | Original-ZIP und Abrufprotokolle in `runtime/raw` und `runtime/manifests` |
| `transform` | Arbeitskopien erzeugen, Spark-Prüfungen und Tagesaggregation, PostgreSQL-Veröffentlichung | Laufberichte, ausgesonderte Datensätze und Tagesexporte in `runtime/runs` |
| `database` | Tagesmerkmale, aktive Version und Laufhistorie bereitstellen | Docker-Volume `postgres_data` |
| `test` | Synthetische Prüfbeispiele und Transaktionstests | Ausschließlich separate Datenbank `pm10_test` |

Die Verarbeitungsdienste laufen als getrennte Container mit einem gemeinsamen Image. PostgreSQL verwendet ein eigenes Image. Beide Basis-Images sind über Digests festgelegt, die Python-Abhängigkeiten über feste Versionsnummern.

## Orientierung im Code

`scripts/run.sh` startet die Datenbank und führt Aufnahme und Verarbeitung nacheinander aus. Die Befehle sind in `pm10/__main__.py` verbunden. `pm10/ingest.py` lädt und prüft das Archiv, `pm10/transform.py` berechnet mit Spark die Tagesmerkmale, `pm10/store.py` prüft den bisherigen Stand und veröffentlicht neue Ergebnisse in einer Datenbanktransaktion.

`compose.yaml` beschreibt die Dienste und ihre Verbindungen. Die Auswahlregeln stehen in `config/quality.json`, Tabellen und Sichten in `sql/schema.sql`. `tests/` enthält die automatisierten Prüffälle, `evidence/` die Nachweise des vollständigen Datenlaufs.

## Was gespeichert wird

Eine Messreihe wird durch Bundesstaat, County, Standort, Parameter und POC identifiziert. POC unterscheidet mehrere Messreihen am selben Standort. Ein Tagesdatensatz enthält unter anderem:

- Datum in **lokaler Standardzeit**, nicht nach Sommerzeit umgerechnet.
- Zahl beobachteter und verwendeter Stunden.
- Mittelwert, Minimum und Maximum der verwendeten Werte.
- Zahl negativer Werte, Qualitätskennzeichen und Ereignishinweise.
- Einen Vergleichsmittelwert vor dem Zurückstellen bekannter Qualitätsprobleme.
- Kennzeichnung, ob mindestens 18 verwendbare Stunden und genau eine Messmethode vorliegen.
- Verknüpfung zum Verarbeitungslauf und zum Originalarchiv.

Die Sicht `model_candidates` enthält Tage mit mindestens 18 verwendbaren Stunden und genau einer Messmethode. Diese Auswahlregel dient der späteren Analyse und ist keine amtliche Gültigkeitsbewertung. Die Qualitätszähler bleiben in der Sicht erhalten.

## Ergebnis ansehen

```sh
docker compose run --rm transform status
docker compose exec -T database psql -U pm10 -d pm10 -c \
  'SELECT state, county, site, poc, day, n_usable, mean_pm10, n_negative
   FROM model_candidates
   ORDER BY state, county, site, poc, day
   LIMIT 10;'
```

Für eigene Abfragen steht die Tabelle `daily_feature` zur Verfügung. `pipeline_run` dokumentiert erfolgreiche, fehlgeschlagene oder unterbrochene Läufe. `active_dataset` zeigt die aktuell veröffentlichte Version.

## Tests und Nachweise

```sh
./scripts/test.sh
```

Die zehn Tests decken unter anderem Zeitgrenzen, Qualitätsregeln, doppelte und widersprüchliche Beobachtungen, unvollständige Tage sowie Rollback und Wiederholungsschutz ab. Datenbanktests verwenden die separate Datenbank `pm10_test`. Die unabhängige Nachrechnung des vollständigen Datensatzes und die Wiederherstellung einer Sicherung sind zusätzlich in `evidence/` dokumentiert.

Die genannten Zeilenzahlen beziehen sich auf den geprüften EPA-Datenstand. Beim Start wird die Jahresdatei erneut heruntergeladen. Falls EPA sie aktualisiert, können andere Zahlen entstehen. Der Quellhash in `runtime/source-2024.json` lässt sich mit `evidence/source-2024.json` vergleichen. Die unabhängige Nachrechnung in `scripts/reference_check.py` ist ausdrücklich auf den dokumentierten Referenzbestand begrenzt.

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

Geprüft wurde auf einem ARM64-Mac, einschließlich eines frischen Aufbaus aus GitHub mit neuen Zugangsdaten und leerer Datenbank am 09.11.2026. Die [Ergebnisse dieser Wiederholung](evidence/reproduction-check.json) stimmen mit dem ursprünglichen Lauf überein. Die Ausführung auf einem zweiten Rechner, unter Windows/WSL und in einem verteilten Spark-Cluster steht noch aus. Ein ML-Modell gehört nicht zum Projekt. Dafür müssten unter anderem Zielvariable, zeitliche Validierung und der Einfluss der Qualitätsauswahl gesondert untersucht werden.
