# Betrieb und Wiederanlauf

## Regelmäßiger Lauf

Das Projekt nutzt 2024 als festen Referenzdatensatz. Der ausführbare Befehl ist:

```sh
./scripts/run.sh 2024
```

In einem laufenden Betrieb würden die fachlich relevanten Jahresdateien geprüft, beispielsweise das laufende und das vorherige Jahr. Ein Aufruf zu Quartalsbeginn reicht für die gewählte Aufgabenstellung. EPA aktualisiert AirData-Dateien nicht mit jeder einzelnen Messung. Ein unveränderter Abruf ist deshalb ein erwarteter Fall. Eine automatische Ausführung ist nicht eingerichtet.

Der Download wird zunächst unter einem temporären Namen gespeichert. Erst nach ZIP-, Header- und Hashprüfung entsteht ein gültiges Abrufprotokoll. Bei einem Netzwerkfehler bleibt die bisherige Quelle verfügbar, der neue Befehl endet mit einem Fehlercode. Nach Behebung kann derselbe Befehl wiederholt werden.

## Fehlerbilder

| Situation | Verhalten / Vorgehen |
|---|---|
| Unveränderte Quelle, Regeln, Programm und Ergebnis | `skipped`, keine neue Berechnung |
| Neue Quelldatei, geänderte Regeln oder Code | Neue Verarbeitung und atomarer Ersatz der Jahrespartition |
| Ergebniszeile fehlt oder wurde verändert | Integritätsprüfung erkennt die Abweichung, erneute Berechnung |
| Datenbank nicht bereit | Compose wartet auf den Healthcheck |
| Zweiter Schreiber derselben Jahrespartition | Advisory-Lock verhindert konkurrierende Verarbeitung |
| Fehler vor Commit | Neue Transaktion wird zurückgerollt, bisheriger Stand bleibt verfügbar |
| Prozess hart beendet | PostgreSQL rollt offene Transaktionen zurück und gibt den Lock frei. Der nächste Lauf kennzeichnet den vorigen offenen Lauf als unterbrochen. |
| Quelldatei lokal verändert | SHA-256-Prüfung bricht ab |
| Neuer EPA-Qualifier | Abbruch, Code anhand der EPA-Dokumentation prüfen, Regelversion ändern |
| Host-Speicher knapp | `measure_run.py` startet nicht unter 2 GiB und stoppt bei weniger als 1 GiB Reserve |

Ein bereits festgeschriebener Datenbankstand bleibt auch dann gültig, wenn danach das lokale Schreiben einer JSON-Berichtskopie scheitert. Der Datenbankstatus ist maßgeblich. Ein erneuter `status`-Aufruf und der Laufdatensatz klären diesen seltenen Fall.

## Sicht auf die Laufhistorie

```sh
docker compose exec -T database psql -U pm10 -d pm10 -c \
  'SELECT run_id,status,started_at,finished_at,error FROM pipeline_run ORDER BY started_at;'
```

Laufverzeichnisse enthalten `report.json` oder `failure.json`, Tagesexporte sowie Parquet-Dateien für strukturell ungültige oder zurückgestellte Beobachtungen. Bei einem harten Abbruch können temporäre Arbeitsdateien verbleiben. Sie dürfen erst entfernt werden, wenn der betreffende Container beendet ist. Das Original-ZIP bleibt erhalten.

## Sicherung

Die Datenbank und die Originalarchive müssen getrennt gesichert werden. Ein Datenbankdump allein enthält keine Rohdaten.

```sh
mkdir -p runtime/backups
docker compose exec -T database pg_dump -U pm10 -d pm10 -Fc > runtime/backups/pm10.dump
```

Zur Kontrolle wird der Dump in eine **andere Datenbank** eingespielt:

```sh
docker compose exec -T database createdb -U pm10_admin -O pm10 pm10_restore_test
docker compose exec -T database pg_restore -U pm10 -d pm10_restore_test --no-owner < runtime/backups/pm10.dump
```

Danach Zeilenzahlen und Ergebnis-Hash mit dem Original vergleichen. Die Testdatenbank kann anschließend ausdrücklich mit `dropdb -U pm10_admin pm10_restore_test` entfernt werden. Niemals einen Restore-Versuch gegen die einzige Ergebniskopie ausführen.

`docker compose down` stoppt Dienste und entfernt das Netzwerk, erhält aber das Datenbank-Volume. **`docker compose down -v` löscht das Volume** und gehört nicht zum normalen Ablauf.

## Zugangsdaten und Weitergabe

`secrets/`, `.env` und `runtime/` bleiben lokal. Auf einem anderen Rechner erzeugt `setup.sh` neue Zugangsdaten. Das Repository enthält den Code, die Konfiguration, die Dokumentation und die Prüfergebnisse. Rohdaten und Zugangsdaten werden auf dem Zielrechner separat eingerichtet.
