# Qualitätsregeln

## Quelle und Bedeutung

Verarbeitet wird die EPA-AirData-Datei `hourly_81102_2024.zip` mit Messungen aus AQS. Parameter 81102 steht für PM10. Die Werte werden in `Micrograms/cubic meter (25 C)` unter den angegebenen Standardbedingungen geliefert. Auch diese amtliche Quelle kann fehlerhafte Einzelwerte enthalten. Laut EPA enthält die Stundendatei bei mehreren Qualitätskennzeichen nur das höchstrangige. Ein leeres Kennzeichen bestätigt deshalb nicht automatisch die Fehlerfreiheit eines Messwerts.

Die Quelldatei bleibt unverändert als ZIP erhalten. Mit ihrer SHA-256-Prüfsumme lässt sich prüfen, ob später noch dieselbe Datei vorliegt. Über die physikalische Richtigkeit der Messungen sagt diese Prüfung nichts aus.

## Entscheidungen der Pipeline

| Fall | Behandlung | Begründung |
|---|---|---|
| Falscher ZIP-Inhalt, falscher Header oder abweichende Spaltenzahl | Lauf abbrechen | Eine unbemerkte Formatänderung darf nicht als fachlich gültige Eingabe weiterlaufen. |
| Unlesbare Zeit oder Zahl, falscher Parameter oder falsche Einheit, Koordinaten außerhalb gültiger Wertebereiche, ungültiges Kennungsformat | Separater Parquet-Auszug `invalid` | Tageszuordnung und Messgröße müssen eindeutig sein. |
| Exakt gleiche Zeile mit allen 24 Quellfeldern | Einmal berücksichtigen und entfernte Wiederholungen zählen | Mehrfachübertragung soll keinen Mittelwert verändern. |
| Verschiedene Zeilen mit derselben Messreihe und Lokal- oder GMT-Stunde | Alle betroffenen Beobachtungen in `review` zurückstellen | Ohne weitere Informationen ist nicht feststellbar, welche Beobachtung korrekt ist. |
| Unbekanntes Qualitätskennzeichen | Lauf abbrechen | Neue Codes müssen anhand der EPA-Tabelle geprüft und in die versionierte Regel aufgenommen werden. |
| Bekannte QA-Probleme, etwa QX oder ein als Ausreißer markierter Wert | Für die Hauptaggregation zurückstellen, Quelle und Vergleichsmittelwert erhalten | Vorsichtige Auswahl für dieses Projekt. Die amtliche Bewertung des Werts wird dadurch nicht geändert. |
| 1V, V, VB, MD und NS | Beibehalten und kennzeichnen | Die Beschreibungen weisen auf Validierung, niedrige Werte, Nachweisgrenze oder eine nahe Quelle hin. Sie begründen allein keinen Ausschluss. |
| Informationskennzeichen oder Antrag auf Ereignisausschluss | Beibehalten und Ereigniszähler erhöhen | Ein Ereignis ist Teil realer Luftbelastung. Ein Antrag ist nicht mit einer genehmigten amtlichen Ausnahme gleichzusetzen. |
| Negativer Wert | Beibehalten, sofern kein anderer Ausschlussgrund vorliegt, und zählen | Messtechnische Unsicherheit kann negative Konzentrationsschätzungen erzeugen. Pauschales Nullsetzen oder Löschen würde die Verteilung verändern. Keine nachträgliche Ersetzung durch MDL/2. |
| Sehr großer positiver Wert ohne ausschließendes Kennzeichen | Beibehalten | Ein statistischer Extremwert allein beweist keinen Messfehler. |
| Weniger als 18 verwendbare Stunden | Tageswert speichern, aus `model_candidates` ausschließen | Die Mindestabdeckung ist eine Projektregel und kein EPA-Zulässigkeitskriterium. |
| Mehrere Methoden innerhalb eines Tages | Speichern, aus `model_candidates` ausschließen | Ein Methodenwechsel soll für spätere Modellversuche sichtbar bleiben. |

Die Regeln sind in `config/quality.json` hinterlegt. Bekannte QA-Codes außerhalb der ausdrücklich eingeschlossenen Liste werden zur Prüfung zurückgestellt. Diese Auswahl kann bestimmte Standorte oder Ereignisse stärker betreffen als andere. Deshalb werden die Zeilenzahlen vor und nach der Auswahl dokumentiert.

## Tagesberechnung

Zusammengefasst wird nach `state, county, site, parameter, poc, day`. Das Datum `day` stammt aus der lokalen Standardzeit der Quelldatei. Die GMT-Angaben werden zusätzlich auf Lesbarkeit, Stundenraster, Abstand zur Lokalzeit und widersprüchliche Stunden geprüft. Am lokalen Jahresende darf die GMT-Angabe bereits in 2025 liegen. Eine automatische Sommerzeitkorrektur findet nicht statt.

Der Mittelwert ist die Summe der verwendeten Stundenwerte geteilt durch deren Anzahl. Fehlende Stunden werden nicht aufgefüllt. `mean_observed` ist ein Vergleichswert aller strukturell gültigen, zeitlich eindeutigen Beobachtungen einschließlich der später wegen QA zurückgestellten Werte. Widersprüchliche Stunden werden auch dort nicht willkürlich gemittelt.

`n_observed` zählt unterschiedliche beobachtete Lokalstunden. `n_review` zählt zurückgestellte **Zeilen** und kann bei mehreren widersprüchlichen Zeilen größer als die Zahl betroffener Stunden sein. Die übrigen Qualitätszähler beziehen sich ebenfalls auf strukturell gültige Zeilen nach Entfernung exakter Wiederholungen. Vollständig fehlende Tage werden nicht künstlich erzeugt. Ohne Betriebsplan darf nicht jeder unbeobachtete Tag als Ausfall gelten.

Es gibt keine Unsicherheitsgewichtung. Die ausgewertete Quelle liefert dafür keine ausgefüllte Unsicherheitsspalte. Negative MDL-Metadaten werden nicht pauschal als Messfehler interpretiert.

## Grenzen der Prüfung

Die Regeln kontrollieren Schema, Konsistenz und dokumentierte Kennzeichen. Sie ersetzen keine Kalibrierprotokolle, Stationsprüfung oder Rückfrage beim Datenlieferanten. Für ein späteres Modell sind unter anderem eine Sensitivitätsanalyse zu negativen Werten und zurückgestellten QA-Fällen sowie eine zeitlich getrennte Evaluation erforderlich. Ein beobachteter Tageswert allein erlaubt noch keine belastbare Vorhersage.
