# Betrieb und Wiederanlauf

## Regelmäßiger Lauf

Das Projekt verwendet die Jahresdatei für 2024 als Referenz. Der Lauf wird so gestartet:

```sh
./scripts/run.sh 2024
```

Im laufenden Betrieb würden beispielsweise das aktuelle und das vorherige Jahr abgerufen. Für die gewählte Aufgabenstellung ist ein Aufruf zu Quartalsbeginn vorgesehen. EPA aktualisiert die AirData-Dateien nicht mit jeder einzelnen Messung. Deshalb kann ein erneuter Abruf dieselbe Datei liefern. Eine automatische Ausführung ist nicht eingerichtet.

Der Download wird zunächst unter einem temporären Namen gespeichert. Nach der ZIP- und Spaltenprüfung wird das Abrufprotokoll mit der Prüfsumme geschrieben. Bei einem Netzwerkfehler bleibt die bisherige Quelle erhalten. Der Aufruf endet mit einem Fehlercode und kann nach Behebung des Problems wiederholt werden.

## Verhalten bei Änderungen und Fehlern

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

Wenn das Speichern des lokalen JSON-Berichts nach dem Commit scheitert, bleibt der bereits abgeschlossene Datenbankstand gültig. In diesem Fall zeigen der `status`-Aufruf und der Eintrag in `pipeline_run`, ob die Ergebnisse übernommen wurden.

## Bisherige Läufe ansehen

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

Danach Zeilenzahlen und Ergebnis-Hash mit dem Original vergleichen. Die Testdatenbank kann anschließend mit `dropdb -U pm10_admin pm10_restore_test` entfernt werden. Niemals einen Restore-Versuch gegen die einzige Ergebniskopie ausführen.

`docker compose down` stoppt Dienste und entfernt das Netzwerk, erhält aber das Datenbank-Volume. **`docker compose down -v` löscht das Volume** und gehört nicht zum normalen Ablauf.

## Zugangsdaten und Weitergabe

`secrets/`, `.env` und `runtime/` bleiben lokal. Auf einem anderen Rechner erzeugt `setup.sh` neue Zugangsdaten. Das Repository enthält den Code, die Konfiguration, die Dokumentation und die Prüfergebnisse. Rohdaten und Zugangsdaten werden auf dem Zielrechner separat eingerichtet.
