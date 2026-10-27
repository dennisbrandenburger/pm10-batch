# Das Projekt in einfachen Worten

## Was eine Zeile bedeutet

Eine Zeile sagt beispielsweise: An einer bestimmten Messreihe wurden am 1. Januar 2024 um 00:00 Uhr 55,9 Mikrogramm PM10 pro Kubikmeter unter den angegebenen Standardbedingungen gemeldet. Dazu kommen Ortskennung, Messmethode, Uhrzeit in GMT und mögliche Hinweise zur Qualität. PM10 beschreibt eine Staubfraktion mit einem aerodynamischen Durchmesser bis ungefähr zehn Mikrometern.

Das sind historische Beobachtungen. Wir erfinden keine Messwerte und machen aus einem fehlenden Wert nicht automatisch eine Null.

## Was wir daraus bauen

1. **Abholen:** Die Pipeline lädt die Jahresdatei von EPA. Sie speichert das unveränderte Original und notiert, wann und in welcher Version es abgerufen wurde.
2. **Prüfen:** Sie kontrolliert Format, Zeiten, Kennungen und Qualitätsangaben. Gleiche Wiederholungen zählen nur einmal. Bei widersprüchlichen Stunden wird keine beliebige Zeile gewählt.
3. **Zusammenfassen:** Spark bildet für jede Messreihe und jeden lokalen Tag Mittelwert, Minimum, Maximum und Qualitätszähler.
4. **Bereitstellen:** PostgreSQL speichert die Tagesdatensätze. Neue Ergebnisse werden nur vollständig veröffentlicht. Eine abgebrochene Aktualisierung soll den bisherigen Stand nicht zerstören.

Spark ist der Rechenmotor. PostgreSQL ist der geordnete Ergebnisspeicher. Docker sorgt dafür, dass diese Programme in festgelegten Umgebungen starten. Git hält den Code und seine Änderungen fest.

## Ein kleines Rechenbeispiel

Angenommen, vier verwendbare Stundenwerte lauten 10, 20, 20 und 30. Ihr Mittelwert beträgt 20. Das ist ein gültiges Rechenbeispiel, aber nach unserer Projektregel noch kein ausreichend abgedeckter Tag für `model_candidates`, weil nur vier statt mindestens 18 Stunden vorliegen. Der Tagesdatensatz wird trotzdem gespeichert und entsprechend gekennzeichnet.

Die Grenze von 18 Stunden ist unsere dokumentierte Auswahl für spätere Analysen. Sie ist keine pauschale Aussage darüber, ob EPA diesen Tag regulatorisch anerkennen würde.

## Wozu das praktisch nützt

Wer Luftbelastung untersuchen oder ein Modell entwickeln möchte, braucht konsistente, nachvollziehbare Eingaben. Diese Arbeit lässt sich nicht durch einen einzelnen manuellen CSV-Import zuverlässig erledigen: Die Quelle kann sich ändern, Messungen können problematisch sein und Aktualisierungen können scheitern. Unsere Pipeline macht die Aufbereitung wiederholbar und hält die Herkunft sichtbar.

Ein späteres Modell könnte zum Beispiel Tageskonzentrationen vorhersagen. Dafür müssten zunächst eine konkrete Vorhersagefrage, zusätzliche Einflussgrößen wie Wetter und eine saubere zeitliche Validierung festgelegt werden. Eine gute Datenpipeline ist dafür eine Voraussetzung. Sie beweist noch keine Vorhersagegüte. Ein solches Modell gehört hier nicht zum umzusetzenden Umfang.

## Was du erklären können solltest

- Warum speichern wir das Originalarchiv zusätzlich zur Datenbank?
- Was ist der Unterschied zwischen einer Messstation und einer AQS-Messreihe?
- Warum werden negative Werte nicht automatisch gelöscht?
- Warum reicht ein hoher Messwert allein nicht als Beweis für einen Fehler?
- Was passiert, wenn ein Lauf während des Speicherns abbricht?
- Woran erkennt die Pipeline, dass ein erneuter Lauf nichts ändern muss?
- Welche Nachteile verursacht Spark bei einer lokalen Verarbeitung?
- Welche Arbeit wäre vor einem echten ML-Modell noch nötig?
