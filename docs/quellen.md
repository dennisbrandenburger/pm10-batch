# Quellen und Herkunft

## Datengrundlage

Die US-Umweltbehörde EPA führt die Jahresdatei für 2024 unter „Hourly Data“, PM10 Mass (81102). In der [Downloadübersicht](https://aqs.epa.gov/aqsweb/airdata/download_files.html) gibt sie den Datenstand mit 25. Juni 2026 an.

U.S. Environmental Protection Agency. (25. Juni 2026). *PM10 mass (81102), 2024* [Datensatz mit Stundenmessungen]. AirData. https://aqs.epa.gov/aqsweb/airdata/hourly_81102_2024.zip

Für den dokumentierten Lauf vom 26.10.2026 wurde die Datei direkt von der EPA heruntergeladen. Das ZIP umfasst 32.122.063 Bytes, die CSV darin 1.089.505.956 Bytes. Abrufzeit, HTTP-Metadaten und SHA-256 stehen in [source-2024.json](../evidence/source-2024.json).

U.S. Environmental Protection Agency. (1. Dezember 2015). *AirData download files documentation* (Version 3.0.0). https://aqs.epa.gov/aqsweb/airdata/FileFormats.html

Abschnitt 1.1 definiert eine Messreihe. Abschnitt 6.2 beschreibt unter anderem die lokale Standardzeit, GMT und die Beschränkung auf das jeweils höchstrangige Qualitätskennzeichen.

Die [AQS-Tabelle der Qualitätskennzeichen](https://aqs.epa.gov/aqsweb/documents/codetables/qualifiers.html) ist als [lokaler Datenstand vom 22.10.2026](epa_qualifiers.csv) gesichert. Die Beschreibungen wurden am 26.10.2026 mit der EPA-Tabelle abgeglichen. Die Entscheidungen über die Verarbeitung der Kennzeichen sind im Projekt in [quality.json](../config/quality.json) festgelegt. Die EPA beschreibt die Herkunft der Messungen in ihrer [Einführung in das Air Quality System](https://aqs.epa.gov/aqsweb/documents/about_aqs_data.html).

## Technische Dokumentation

- [Apache Spark 4.2.0](https://spark.apache.org/docs/4.2.0/) und [Spark-Containerimages](https://github.com/apache/spark-docker)
- [Zugangsdaten in Docker Compose](https://docs.docker.com/compose/how-tos/use-secrets/)
- [Sperren in PostgreSQL 17](https://www.postgresql.org/docs/17/explicit-locking.html) und [Transaktionen](https://www.postgresql.org/docs/17/tutorial-transactions.html)
- [COPY mit Psycopg 3](https://www.psycopg.org/psycopg3/docs/basic/copy.html)

Die Laufmessungen und Testergebnisse des Projekts stehen unter [evidence](../evidence/).
