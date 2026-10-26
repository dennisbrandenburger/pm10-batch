# Quellen und Herkunft

## Datengrundlage

U.S. Environmental Protection Agency. (o. J.). *AirData: Download files*. https://aqs.epa.gov/aqsweb/airdata/download_files.html

Verarbeitete Jahresdatei: https://aqs.epa.gov/aqsweb/airdata/hourly_81102_2024.zip

Die Erstprüfung im Projekt erfolgte am 22.10.2026. Für Phase 2 wird die Datei erneut direkt von EPA heruntergeladen. Abrufzeit, HTTP-Metadaten, Größe und SHA-256 stehen im jeweiligen `source-2024.json` und im Laufbericht. Das ZIP umfasst 32.122.063 Bytes, die enthaltene CSV 1.089.505.956 Bytes. Referenzhash: `2db9732577123284e7f94b581b135c30feae5c7c2d8623d1def66db722d78da4`.

U.S. Environmental Protection Agency. (o. J.). *AirData file formats*. https://aqs.epa.gov/aqsweb/airdata/FileFormats.html

Verwendet für Spaltenbedeutung, Messreihenkennung, lokale Standardzeit und GMT sowie die Einschränkung auf das höchstrangige Qualitätskennzeichen.

U.S. Environmental Protection Agency. (o. J.). *AQS qualifier codes*. https://aqs.epa.gov/aqsweb/documents/codetables/qualifiers.html

Die im Projekt am 22.10.2026 gesicherte CSV-Tabelle liegt unter `docs/epa_qualifiers.csv`. Die fachliche Zuordnung wurde am 26.10.2026 gegen die EPA-Seite geprüft. Die daraus abgeleitete **eigene** Auswahlregel ist in `config/quality.json` nachvollziehbar. Die EPA-Codebeschreibung und die Projektentscheidung sind unterschiedliche Dinge.

U.S. Environmental Protection Agency. (o. J.). *About AQS data*. https://aqs.epa.gov/aqsweb/documents/about_aqs_data.html

Verwendet zur Einordnung der Datenherkunft und der Grenzen einer automatischen Qualitätsprüfung.

## Technische Dokumentation

Apache Software Foundation. (2026). *Apache Spark 4.2.0 documentation*. https://spark.apache.org/docs/4.2.0/

Apache Software Foundation. (2026). *Spark Docker images*. https://github.com/apache/spark-docker

Docker, Inc. (o. J.). *Use secrets in Docker Compose*. https://docs.docker.com/compose/how-tos/use-secrets/

PostgreSQL Global Development Group. (o. J.). *PostgreSQL 17: Explicit locking*. https://www.postgresql.org/docs/17/explicit-locking.html

PostgreSQL Global Development Group. (o. J.). *PostgreSQL 17: Transactions*. https://www.postgresql.org/docs/17/tutorial-transactions.html

Psycopg Team. (o. J.). *Using COPY TO and COPY FROM*. https://www.psycopg.org/psycopg3/docs/basic/copy.html

Technische Dokumentation zuletzt geprüft am 26.10.2026. Fremde Konzepte sind belegt. Messwerte und Testergebnisse entstehen aus den dokumentierten lokalen Läufen und werden nicht aus Beispielen der Dokumentation übernommen.
