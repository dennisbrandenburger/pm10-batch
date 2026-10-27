# PM10-Datenpipeline

Diese Batch-Pipeline bereitet stündliche PM10-Messungen der US-Umweltbehörde EPA für spätere Analysen und Modellversuche auf. Sie lädt Jahresdateien, prüft die Beobachtungen, berechnet Tagesmerkmale je Messreihe und veröffentlicht diese in PostgreSQL. Ein ML-Modell wird nicht trainiert.

## Schnellstart

Voraussetzungen: Docker mit Compose, Python 3 für das lokale Einrichtungsskript, etwa 6 GiB für die Docker-VM und 4 CPU-Kerne. Für eine Neuinstallation sind **8 GiB freier Speicher als Arbeitsreserve** sinnvoll. Messwerte zur geprüften Umgebung stehen in `evidence/`.

```sh
./scripts/setup.sh
docker compose build transform
./scripts/run.sh 2024
```

`setup.sh` erzeugt zwei zufällige lokale Passwörter und die UID/GID-Konfiguration. Diese Dateien gehören nicht ins Git-Repository. `run.sh` lädt die Quelle erneut und prüft, ob eine Verarbeitung nötig ist. Compose startet die Datenbank ohne einen nach außen geöffneten Port.

Bei Verwendung von Colima kann die Umgebung in einem eigenen Profil gestartet werden:

```sh
colima start --profile de-pm10 --cpu 4 --memory 6 --activate=false
export DOCKER_CONTEXT=colima-de-pm10
```

Wo `docker compose` nicht als Plugin installiert ist, verwenden die Skripte automatisch `docker-compose`. Die allgemeinen Befehle lassen sich entsprechend ersetzen.

## Komponenten

| Dienst | Aufgabe | Dauerhafte Daten |
|---|---|---|
| `ingest` | HTTPS-Download, Größenlimit, ZIP-CRC, Dateiname, Spalten und SHA-256 prüfen | Original-ZIP und Abrufprotokolle in `runtime/raw` und `runtime/manifests` |
| `transform` | Arbeitskopien erzeugen, Spark-Prüfungen und Tagesaggregation, PostgreSQL-Veröffentlichung | Laufberichte, ausgesonderte Datensätze und Tagesexporte in `runtime/runs` |
| `database` | Tagesmerkmale, aktive Version und Laufhistorie bereitstellen | Docker-Volume `postgres_data` |
| `test` | Synthetische Prüfbeispiele und Transaktionstests | Ausschließlich separate Datenbank `pm10_test` |

Die Einmal-Dienste sind getrennte Container. Sie teilen sich ein Image, damit Spark und Python nicht mehrfach installiert werden. `database` verwendet ein eigenes PostgreSQL-Image. Beide Basis-Images sind durch Version und Digest festgelegt. Python-Abhängigkeiten sind vollständig auf Versionen festgelegt.

## Was gespeichert wird

Eine Messreihe wird durch Bundesstaat, County, Standort, Parameter und POC identifiziert. POC unterscheidet mehrere Messreihen am selben Standort. Ein Tagesdatensatz enthält unter anderem:

- Datum in **lokaler Standardzeit**, nicht nach Sommerzeit umgerechnet.
- Zahl beobachteter und verwendeter Stunden.
- Mittelwert, Minimum und Maximum der verwendeten Werte.
- Zahl negativer Werte, Qualitätskennzeichen und Ereignishinweise.
- Einen Vergleichsmittelwert vor dem Zurückstellen bekannter Qualitätsprobleme.
- Kennzeichnung, ob mindestens 18 verwendbare Stunden und genau eine Messmethode vorliegen.
- Verknüpfung zum Verarbeitungslauf und zum Originalarchiv.

Die Sicht `model_candidates` enthält Tage, die diese Projektregel erfüllen. Das sind mögliche Eingaben für ein späteres Modell, **keine amtlich zertifizierten Tageswerte**. Die Qualitätsmerkmale bleiben auch in der Sicht sichtbar.

## Ergebnis ansehen

```sh
docker compose run --rm transform status
docker compose exec -T database psql -U pm10 -d pm10 -c \
  'SELECT state,county,site,poc,day,n_usable,mean_pm10,n_negative FROM model_candidates ORDER BY state,county,site,poc,day LIMIT 10;'
```

Für eigene Abfragen steht die Tabelle `daily_feature` zur Verfügung. `pipeline_run` dokumentiert erfolgreiche, fehlgeschlagene oder unterbrochene Läufe. `active_dataset` zeigt die aktuell veröffentlichte Version.

## Tests und Nachweise

```sh
./scripts/test.sh -q -p no:cacheprovider /app/tests
python3 scripts/measure_run.py
```

Die Messung verweigert einen Start unter 2 GiB freiem Host-Speicher und stoppt bei weniger als 1 GiB Reserve. Docker-Statistiken sind Stichproben und kein Nachweis des exakten Speichermaximums. Auf stark belasteten Rechnern ist mehr Reserve nötig.

Die Tests prüfen unter anderem Jahreswechsel zwischen Lokalzeit und GMT, negative Messwerte, Qualitätskennzeichen, widersprüchliche Beobachtungen, genaue Wiederholungen, unvollständige Tage, Rollback, Wiederholungsschutz, Ergebnisbeschädigungen und konkurrierende Schreiber. Die Testdatenbank ist vom produktiven Ergebnis getrennt.

Weitere Erläuterungen:

- [Qualitätsregeln und Grenzen](docs/qualitaet.md)
- [Architektur und Entscheidungen](docs/architektur.md)
- [Betrieb, Wiederanlauf und Sicherung](docs/betrieb.md)
- [Quellen und Herkunft](docs/quellen.md)
- [Nachweise](evidence/)

## Projektgrenzen

Der Nachweis erfolgt lokal auf einem ARM64-Mac. Ein zweiter physischer Rechner und ein verteilter Spark-Cluster werden damit nicht getestet. Docker erleichtert die Übertragbarkeit, ersetzt diesen Nachweis aber nicht. Das Projekt enthält keine behördliche Grenzwertbewertung, keine Prognosegüte und keine Anwendung zur Gesundheitsberatung. Für eine spätere ML-Studie wären Zielvariable, zeitliche Validierung, fehlende Zeiträume und Selektionswirkungen der Qualitätsregeln gesondert zu untersuchen.
