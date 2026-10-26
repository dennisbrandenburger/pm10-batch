# Qualitätsregeln

## Quelle und Bedeutung

Verarbeitet wird EPA AirData `hourly_81102_2024.zip`. Parameter 81102 bezeichnet PM10 in der hier gelieferten Standardbedingungen-Einheit `Micrograms/cubic meter (25 C)`. Die Jahresdatei enthält Messungen aus AQS. Die Herkunft ist belastbar, liefert aber keine Garantie für die sachliche Richtigkeit jedes einzelnen Werts. Die stündliche Datei zeigt laut EPA nur das höchstrangige Qualitätskennzeichen, falls mehrere vorliegen. Ein leeres Kennzeichen ist daher kein Qualitätszertifikat.

Die Quelldatei bleibt unverändert als ZIP erhalten. `SHA-256` identifiziert die konkreten Bytes. Eine Prüfsumme beweist Integrität gegenüber diesem Ausgangsstand, nicht die physikalische Richtigkeit der Messung.

## Entscheidungen der Pipeline

| Fall | Behandlung | Begründung |
|---|---|---|
| Falscher ZIP-Inhalt, falscher Header oder abweichende Spaltenzahl | Lauf abbrechen | Eine unbemerkte Formatänderung darf nicht als fachlich gültige Eingabe weiterlaufen. |
| Unlesbare Zeit oder Zahl, falscher Parameter/Einheit, unplausible Koordinatenform, ungültige Kennungsform | Separater Parquet-Auszug `invalid` | Tageszuordnung und Messgröße müssen eindeutig sein. |
| Exakt gleiche Zeile mit allen 24 Quellfeldern | Einmal berücksichtigen und entfernte Wiederholungen zählen | Mehrfachübertragung soll keinen Mittelwert verändern. |
| Verschiedene Zeilen mit derselben Messreihe und Lokal- oder GMT-Stunde | Alle betroffenen Beobachtungen in `review` zurückstellen | Ohne weitere Informationen lässt sich kein richtiger Gewinner wählen. |
| Unbekanntes Qualitätskennzeichen | Lauf abbrechen | Neue Codes müssen anhand der EPA-Tabelle geprüft und in die versionierte Regel aufgenommen werden. |
| Bekannte QA-Probleme, etwa QX oder ein als Ausreißer markierter Wert | Für die Hauptaggregation zurückstellen, Quelle und Vergleichsmittelwert erhalten | Konservative Projektentscheidung. Das ist keine nachträgliche amtliche Invalidierung. |
| 1V, V, VB, MD und NS | Beibehalten und kennzeichnen | Die Beschreibungen weisen auf Validierung, niedrige Werte, Nachweisgrenze oder eine nahe Quelle hin. Sie begründen allein keinen Ausschluss. |
| INFORMATION / Antrag auf Ereignisausschluss | Beibehalten und Ereigniszähler erhöhen | Ein Ereignis ist Teil realer Luftbelastung. Ein Antrag ist nicht mit einer genehmigten amtlichen Ausnahme gleichzusetzen. |
| Negativer Wert | Beibehalten, sofern kein anderer Ausschlussgrund vorliegt, und zählen | Messtechnische Unsicherheit kann negative Konzentrationsschätzungen erzeugen. Pauschales Nullsetzen oder Löschen würde die Verteilung verändern. Keine nachträgliche Ersetzung durch MDL/2. |
| Sehr großer positiver Wert ohne ausschließendes Kennzeichen | Beibehalten | Ein statistischer Extremwert allein beweist keinen Messfehler. |
| Weniger als 18 verwendbare Stunden | Tageswert speichern, aus `model_candidates` ausschließen | Dokumentierte analytische Mindestabdeckung. Nicht als EPA-Zulässigkeitskriterium ausgeben. |
| Mehrere Methoden innerhalb eines Tages | Speichern, aus `model_candidates` ausschließen | Ein Methodenwechsel soll für spätere Modellversuche sichtbar bleiben. |

Die Tabelle `config/quality.json` ist die ausführbare Fassung. Alle QA-Codes außerhalb der ausdrücklich eingeschlossenen Liste werden zur Prüfung zurückgestellt. Diese vorsichtige Entscheidung kann bestimmte Standorte oder Ereignisse überproportional ausschließen. Die Ergebnisdokumentation muss deshalb die Mengen vor und nach dieser Auswahl nennen.

## Tagesberechnung

Gruppe: `state, county, site, parameter, poc, day`. `day` stammt aus der Lokalzeit des Quellrecords. GMT wird zusätzlich auf Lesbarkeit, Stundenraster, Abstand zur Lokalzeit und widersprüchliche Stunden geprüft. Am lokalen Jahresende ist GMT 2025 zulässig. Eine automatische Sommerzeitkorrektur findet nicht statt.

Der Mittelwert ist die Summe der verwendeten Stundenwerte geteilt durch deren Anzahl. Fehlende Stunden werden nicht aufgefüllt. `mean_observed` ist ein Vergleichswert aller strukturell gültigen, zeitlich eindeutigen Beobachtungen einschließlich der später wegen QA zurückgestellten Werte. Widersprüchliche Stunden werden auch dort nicht willkürlich gemittelt.

`n_observed` zählt unterschiedliche beobachtete Lokalstunden. `n_review` zählt zurückgestellte **Zeilen** und kann bei mehreren widersprüchlichen Zeilen größer als die Zahl betroffener Stunden sein. Die übrigen Qualitätszähler beziehen sich ebenfalls auf strukturell gültige Zeilen nach Entfernung exakter Wiederholungen. Vollständig fehlende Tage werden nicht künstlich erzeugt. Ohne Betriebsplan darf nicht jeder unbeobachtete Tag als Ausfall gelten.

Es gibt keine Unsicherheitsgewichtung. Die ausgewertete Quelle liefert dafür keine ausgefüllte Unsicherheitsspalte. Negative MDL-Metadaten werden nicht pauschal als Messfehler interpretiert.

## Grenzen der Prüfung

Die Regeln kontrollieren Schema, Konsistenz und dokumentierte Kennzeichen. Sie ersetzen keine Kalibrierprotokolle, Stationsprüfung oder Rückfrage beim Datenlieferanten. Für ein späteres Modell sind unter anderem eine Sensitivitätsanalyse zu negativen Werten und zurückgestellten QA-Fällen sowie eine zeitlich getrennte Evaluation erforderlich. Ein beobachteter Tageswert allein erlaubt noch keine belastbare Vorhersage.
