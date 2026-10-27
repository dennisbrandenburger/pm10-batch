# Quellen und Herkunft

## Datengrundlage

U.S. Environmental Protection Agency. (o. J.). *AirData: Download files*. https://aqs.epa.gov/aqsweb/airdata/download_files.html

Verarbeitete Jahresdatei: https://aqs.epa.gov/aqsweb/airdata/hourly_81102_2024.zip

Die Erstprüfung erfolgte am 22.10.2026. Für den dokumentierten Lauf wurde die Datei am 26.10.2026 erneut direkt von EPA heruntergeladen. Abrufzeit, HTTP-Metadaten, Größe und SHA-256 stehen in `evidence/source-2024.json` und im Laufbericht. Das ZIP umfasst 32.122.063 Bytes, die enthaltene CSV 1.089.505.956 Bytes. Referenzhash: `2db9732577123284e7f94b581b135c30feae5c7c2d8623d1def66db722d78da4`.

U.S. Environmental Protection Agency. (o. J.). *AirData file formats*. https://aqs.epa.gov/aqsweb/airdata/FileFormats.html

Verwendet für Spaltenbedeutung, Messreihenkennung, lokale Standardzeit und GMT sowie die Einschränkung auf das höchstrangige Qualitätskennzeichen.

U.S. Environmental Protection Agency. (o. J.). *AQS qualifier codes*. https://aqs.epa.gov/aqsweb/documents/codetables/qualifiers.html

Die am 22.10.2026 gesicherte CSV-Tabelle liegt unter `docs/epa_qualifiers.csv`. Die Codebeschreibungen wurden am 26.10.2026 gegen die EPA-Seite geprüft. `config/quality.json` ergänzt diese Beschreibungen um die im Projekt festgelegten Verarbeitungsregeln.

U.S. Environmental Protection Agency. (o. J.). *About AQS data*. https://aqs.epa.gov/aqsweb/documents/about_aqs_data.html

Verwendet zur Einordnung der Datenherkunft und der Grenzen einer automatischen Qualitätsprüfung.

## Technische Dokumentation

Apache Software Foundation. (2026). *Apache Spark 4.2.0 documentation*. https://spark.apache.org/docs/4.2.0/

Apache Software Foundation. (2026). *Spark Docker images*. https://github.com/apache/spark-docker

Docker, Inc. (o. J.). *Use secrets in Docker Compose*. https://docs.docker.com/compose/how-tos/use-secrets/

PostgreSQL Global Development Group. (o. J.). *PostgreSQL 17: Explicit locking*. https://www.postgresql.org/docs/17/explicit-locking.html

PostgreSQL Global Development Group. (o. J.). *PostgreSQL 17: Transactions*. https://www.postgresql.org/docs/17/tutorial-transactions.html

Psycopg Team. (o. J.). *Using COPY TO and COPY FROM*. https://www.psycopg.org/psycopg3/docs/basic/copy.html

Technische Dokumentation zuletzt geprüft am 26.10.2026. Die Laufmessungen und Testergebnisse liegen separat unter `evidence/`.
