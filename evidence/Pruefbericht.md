# Prüfbericht vom 26.10.2026

## Ergebnis

Die vollständige lokale Verarbeitung des EPA-Jahresarchivs ist erfolgreich. Die abschließende Fassung besteht **10 automatisierte Tests**. Eine unabhängige Python-/Decimal-Referenz bestätigt **alle 163.381 Tagesdatensätze**.

| Größe | Gemessener Wert |
|---|---:|
| Eingabezeilen | 3.870.976 |
| Messreihen | 478 |
| Exakt doppelte Zeilen | 0 |
| Strukturell ungültige Zeilen | 0 |
| Widersprüchliche Stundenzeilen | 0 |
| Für Hauptaggregation verwendete Zeilen | 3.675.791 |
| Wegen QA zur Prüfung zurückgestellte Zeilen | 195.185 |
| Negative Quellwerte | 31.283 |
| Zeilen mit Qualifier | 260.887 |
| Veröffentlichte Tagesdatensätze | 163.381 |
| Tage mit mindestens 18 verwendbaren Stunden und einer Methode | 152.985 |
| Tage mit 24 verwendbaren Stunden | 140.235 |
| Verarbeitungsdauer einschließlich Aufteilung und Veröffentlichung | 94.509 s |
| Gemessene Container-Gesamtdauer | 97.57 s |
| Höchster beobachteter Container-RAM in Stichproben | 3.58 GiB |
| Niedrigster beobachteter freier Host-Speicher im letzten Lauf | 3.25 GiB |
| Größte Abweichung der Mittelwerte zur Dezimalreferenz | 1.14e-13 |

Der erste erfolgreiche Lauf benötigte rund 81 Sekunden, die abschließende Fassung rund 95 Sekunden. Das sind einzelne Messungen auf einem gemeinsam genutzten Rechner, kein statistischer Leistungsbenchmark. Die Referenz toleriert 1e-9 absolute beziehungsweise 1e-10 relative Abweichung. Alle ganzen Zähler und Auswahlentscheidungen stimmen exakt überein.

## Funktionale Nachweise

- `tests.log`: 10 Tests bestanden. Enthalten sind ZIP-Inhalt, Hash und CRC, Zeit-/Einheitenprüfung, unvollständige Tage, Methodenwechsel, negative Werte, Ereignis- und QA-Kennzeichen, widersprüchliche und gleiche Zeilen sowie unbekannte Codes.
- Datenbanktest: Fehler nach DELETE und vor INSERT führt zum Rollback. Alte Ergebnisprüfsumme bleibt erhalten. Geänderte Eingaben/Regeln, beschädigte oder fehlende Ergebnisse werden erkannt. Konkurrierender Schreiber wird abgewiesen. Die Pipeline-Rolle ist kein Superuser.
- `repeat.log`: unveränderte Quelle, Rezept und Ergebnisse führen zu `skipped`.
- `restart-check.log`: nach Neustart der PostgreSQL-Instanz weiterhin derselbe vollständige Stand.
- `restore-check.log`: Restore in eine getrennte Testdatenbank mit 163.381 Zeilen und identischem Ergebnishash.
- `reference-check.json`: unabhängige Berechnung sämtlicher Tagesdatensätze aus dem Originalarchiv. Keine fehlenden Tage, keine Abweichungen außerhalb der Toleranz.

## Geprüfte Umgebung

Die lokale Ausführung erfolgte auf einem ARM64-Mac mit einer Colima-VM, vier CPU-Kernen und 6 GiB RAM. Spark verwendete vier lokale Threads. Die eingesetzten Versionen und Messwerte stehen in `validation-summary.json` und `resources.json`.

## Provenienz

- Run-ID: `1d24e7b7-c7fd-4ebd-a2f5-120469f0c104`
- Quellhash: `2db9732577123284e7f94b581b135c30feae5c7c2d8623d1def66db722d78da4`
- Rezepthash: `a005c8383974db3134868b2e92cbbb528a23ef4de3911aeed2a8cb9c6e8c817a`
- Ergebnishash: `a0f65aeaf86ff9f6501cddafbd6e40f18cee7bff5592def8c87013d5462c71bc`

Der Ergebnishash umfasst sortierte fachliche Tagesfelder. Lauf-IDs und Zeitstempel sind darin nicht enthalten. Das Rechenrezept umfasst die im Programm definierten Code-, Regel- und Versionsbestandteile. Git dokumentiert den zugehörigen Quellstand. Die Quellenangaben stehen in `docs/quellen.md`.

## Was dieser Bericht nicht nachweist

Getestet wurde auf einem physischen ARM64-Mac, nicht auf einem zweiten Rechner oder einem verteilten Cluster. Messwertprüfung ist keine Kalibrierprüfung. Die Auswahl der 18 Stunden ist eine analytische Projektentscheidung. Es wird keine ML-Prognose oder deren Güte behauptet.

Redaktionell überarbeitet am 27.10.2026. Messwerte, Laufprotokolle und der geprüfte Programmstand bleiben unverändert.

## Erneute Einrichtung am 09.11.2026

Eine frische Kopie des GitHub-Commits `20da4854fade9821fa43f1500d9708638a636bab` wurde mit neuen Zugangsdaten, leerem Laufverzeichnis und eigenem Datenbank-Volume eingerichtet. Das Anwendungsimage wurde ohne Build-Layer-Cache neu gebaut. Die Basis-Images und die vorhandene Docker-VM wurden weiterverwendet. Der Test erfolgte auf demselben physischen ARM64-Mac.

Der erneute EPA-Download, das Rechenrezept und die veröffentlichten Ergebnisse haben dieselben Prüfsummen wie der ursprüngliche Lauf. Aus 3.870.976 Beobachtungen entstanden wieder 163.381 Tagesdatensätze. Alle zehn Tests bestanden. Die unabhängige Nachrechnung bestätigte sämtliche Tagesergebnisse. Wiederholungsschutz, README-Abfrage, Datenbankneustart und Restore in eine separate Datenbank funktionierten ebenfalls. Die Verarbeitung einschließlich Aufteilung und Veröffentlichung dauerte 114,556 Sekunden, ohne den vorgelagerten Download.

Die Ergebnisse stehen in [reproduction-check.json](reproduction-check.json). Danach wurden die Startanleitung, die Regel für Shell-Zeilenenden und die Nachweisdokumentation ergänzt. Verarbeitungscode, Schema und fachliche Regeln sind unverändert. Die Ausführung auf AMD64-Hardware und unter Windows/WSL wurde nicht praktisch geprüft.
