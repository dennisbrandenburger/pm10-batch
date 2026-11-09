# Architektur und Entscheidungen

## Ablauf

1. Python lädt das EPA-Jahresarchiv und speichert das unveränderte ZIP mit Abrufzeit und Prüfsumme.
2. Die enthaltene CSV wird für die Verarbeitung in kleinere, komprimierte Arbeitsdateien aufgeteilt.
3. Spark prüft die Beobachtungen und berechnet Tageswerte. Ungültige und zurückgestellte Datensätze sowie Prüfergebnisse werden separat gespeichert.
4. PostgreSQL übernimmt die vollständigen Tagesergebnisse in einer Transaktion. Anschließend stehen sie für Abfragen bereit.

Das Startskript führt Datenaufnahme und Verarbeitung nacheinander aus. Bei einem Fehler bricht es ab. Der vierteljährliche Aufruf ist vorgesehen, aber nicht automatisch eingerichtet.

## Python und Spark

Python übernimmt Download, Archivprüfung, Protokolle und Datenbankzugriff. Spark verarbeitet die stündlichen Beobachtungen. Die Spalten werden zunächst als Text eingelesen. Danach werden Zahlen und Zeitangaben umgewandelt und auf gültige Formate geprüft. Dafür werden die eingebauten Spark-Funktionen verwendet.

Das ZIP enthält eine einzelne große CSV. Sie wird beim Lauf in gzip-Dateien mit jeweils höchstens 100.000 Beobachtungen aufgeteilt. So können mehrere Spark-Aufgaben gleichzeitig lesen. Eine vollständige unkomprimierte Kopie auf dem Host ist dafür nicht nötig. Die Arbeitsdateien werden nach Abschluss oder einem behandelten Fehler entfernt, das Originalarchiv bleibt erhalten.

Spark verwendet lokal vier Threads. Für diese Datenmenge wäre auch eine einfachere Lösung möglich. Spark lässt sich später verteilt einsetzen, erhöht lokal aber den Betriebsaufwand. Die ZIP-Aufteilung läuft nacheinander, und nur ein Prozess schreibt nach PostgreSQL. Diese beiden Schritte begrenzen die Skalierung und müssten für einen Clusterbetrieb gesondert betrachtet und getestet werden.

## Speichern und Wiederanlauf

Vor der Verarbeitung wird für den jeweiligen Jahresdatensatz eine PostgreSQL-Sperre angefordert (Advisory-Lock). Ein zweiter Prozess kann denselben Datensatz dadurch nicht gleichzeitig ersetzen. Beim Verbindungsende gibt PostgreSQL die Sperre frei.

Die Tagesdateien werden zunächst in eine temporäre Tabelle kopiert. Dabei werden die Datenbankbedingungen und die Zeilenzahl geprüft. Danach werden in einer Transaktion die bisherigen Ergebnisse des Jahres ersetzt, die aktive Version gesetzt und der Lauf als erfolgreich markiert. Scheitert der Austausch zwischen Löschen und Einfügen, macht PostgreSQL ihn rückgängig. Der bisherige abgeschlossene Stand bleibt dann erhalten.

Bei einer Wiederholung wird nur dann auf die Berechnung verzichtet, wenn Quelle, Rechenrezept und gespeicherte Ergebnisse unverändert sind. Dazu werden ihre Prüfsummen verglichen. Die Ergebnisprüfsumme wird erneut aus PostgreSQL berechnet. Das Rechenrezept berücksichtigt Programmdateien, Regeln, Schema, Dockerfile, Abhängigkeiten sowie Python- und Spark-Version. Fehlende oder veränderte Ergebniszeilen lösen eine neue Verarbeitung aus.

## Speicherung und Zugriff

Rohdaten und Verarbeitungsergebnisse liegen in einem lokalen Verzeichnis, das in die Container eingebunden wird. Die Datenbank verwendet ein benanntes Docker-Volume. Das Repository enthält Code, Konfiguration, Dokumentation und Prüfprotokolle. Die Quelldateien werden beim ersten Datenlauf heruntergeladen.

Der Datenbanknutzer der Pipeline ist kein Superuser und darf keine Rollen oder Datenbanken anlegen. Der administrative Nutzer hat ein eigenes Passwort. Der Datenbankport wird nicht am Host freigegeben. Verarbeitet werden öffentlich zugängliche Umweltmessungen und Standortkoordinaten. Personenbezogene Datensätze sind nicht Bestandteil dieser Verarbeitung. Passwörter und Laufverzeichnisse sind von Git ausgeschlossen.

## Verhältnis zu Phase 1

Datenquelle, Batch-Ansatz, Python, Spark, PostgreSQL und Compose bleiben wie eingereicht. Präzisiert wurden die Qualitätsregeln, die Definition einer Messreihe, die Behandlung lokaler Zeit und der tatsächliche Wiederanlauf. Die Aufteilung in Arbeitsdateien ermöglicht das parallele Einlesen des Jahresarchivs.
