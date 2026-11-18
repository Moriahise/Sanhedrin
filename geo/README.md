# Shekhina GEO-Monitor

Die Software läuft mit Python 3 ohne Zusatzpakete. GitHub prüft täglich die öffentliche Auslieferung. Die persönliche ChatGPT-Aufgabe erzeugt den Messplan, erhebt die zugänglichen Antworten und aktualisiert denselben privaten HTML-Bericht. Dieser enthält die vollständige Historie und öffnet offline. Nutzungsstatistiken und Antworten gehören ausschließlich in den privaten Bericht.

## Ein Durchlauf

```sh
python3 geo/monitor.py Shekhina_GEO_Monitor.html --plan --day 2026-11-19
python3 geo/monitor.py Shekhina_GEO_Monitor.html --rows beobachtungen.json --connections zugaenge.json --accounts
python3 -m unittest discover -s geo
```

Vor jedem Lauf die neueste Berichtsversion laden. Die Ausgabe für denselben Tag wieder einzulesen ist idempotent. Eine abgeschlossene Beobachtung kann im selben Tagesplatz nicht durch ein anderes Ergebnis überschrieben werden. Bei Versionskonflikt die neueste Datei laden, eigene Beobachtungen erneut importieren und die geschützte Dateiversion ersetzen. Ein neuer Fragenkatalog erfordert eine getrennte Serie.

Für jede der sechs festen Abfragen eine frische Unterhaltung öffnen, den Suchmodus wählen und den exakten Prompt ohne Markenhinweis absenden. Keine Antworten oder Quellen aus dem laufenden Projekt vorgeben. Für zugängliche Dienste die beiden geplanten Zusatzproben jeweils in einer weiteren frischen Unterhaltung ausführen. Die Sprache, Suchoberfläche und der kontofreie bzw. unpersonalisierte Modus sollen über die Zeit gleich bleiben. Änderungen des Modus dokumentieren und den Vergleich entsprechend kennzeichnen. Webtreffer, allgemeine Quellenlisten und recherchierte URLs sind keine Antwortzitate. Nur in der Antwort ausdrücklich zugeordnete anklickbare Quellen übernehmen. Den Beleg öffnen und eine unpassende Zuschreibung im Beobachtungsfeld kennzeichnen. Bei einer vollständig geprüften Antwort ohne Verweis ist die URL-Liste leer. Ist der Quellenbereich unlesbar, den Versuch als unavailable erfassen.

Die Eingabe ist eine JSON-Liste. Jeder Eintrag hat day (ISO-Datum Wien), engine (chatgpt-search, copilot, perplexity, gemini, openai-search-api oder web-discovery), id, lang, variant und prompt aus dem Plan, status (ok oder unavailable), urls (tatsächlich zitierte Adressen), mentions (eindeutig im Antworttext genannte Angebote aus der Vergleichsgruppe), sentiment (positive, neutral, critical, mixed oder unknown) und evidence (kurze Beobachtung samt Modus und Belegstelle). Anbieter höchstens einmal je Antwort zählen. Für Shekhina keine theologische Begriffsverwendung werten. Keine privaten Chat-Links, Kontodaten oder personenbezogenen Fragen aufzeichnen. Bei web-discovery maximal drei sichtbare Treffer, leere mentions und unknown verwenden. Die Messung ist eine Stichprobe.

## Entwicklung und Wirkung

Der Kern rotiert drei der neun Themenpaare pro Tag. Für jedes verfügbare System erprobt ein eigenständiger Durchlauf eine von zwei Zusatzformulierungen pro Sprache. Gepaarte Antworten müssen denselben Kalendertag, Dienst, dasselbe Thema und dieselbe Sprache haben. Ausgewertet wird, ob die Zusatzfrage weitere Quelldomains erschlossen hat. Nach mindestens sechs Paaren pro Variante an jeweils drei oder mehr Tagen folgt die Auswahl dem bisherigen Quellengewinn. Jeder vierte Tag prüft erneut eine schwächer abgedeckte Variante. Diese Ergebnisse werden bei der festen Zitierquote ausgeschlossen.

Für einen begründeten Website-Versuch eine kleine rücknehmbare Änderung und einen gleichzeitig beobachteten Kontroll-Daf dokumentieren. Mit `--experiment versuch.json` die Felder start, engine, lang, topic, control, url, control_url, change und revision registrieren. Beide Seiten und der vorherige Git-Stand müssen identifizierbar sein. Die Vergleiche messen dieselben Zielseiten vor und nach der Änderung mit einem unveränderten Kontroll-Daf. Mindestens sechs gemeinsame Messtage je Zeitraum. Die 25-Prozentpunkte-Schwelle ist ein Entscheidungshinweis, kein statistischer Kausalitätsnachweis. Die redaktionelle Freigabe der Lerntexte bleibt maßgeblich.

## Kontodaten

- **Bing**. Die zugehörige verifizierte Property in AI Performance öffnen. Eine verfügbare Tabelle der zitierten Seiten kann lokal als CSV über GEO_BING_CSV eingelesen werden. Erwartet werden URL, Citations und Date oder Start Date/End Date. Bei einem Export ohne Datumsfeld GEO_BING_PERIOD im Format JJJJ-MM-TT/JJJJ-MM-TT übergeben. Überlappende Berichtszeiträume werden einzeln angezeigt. Fehlende Exporte liefern keinen Nullwert.
- **GA4**. GEO_GA4_PROPERTY und entweder GEO_GA4_ACCESS_TOKEN oder GEO_GA4_CLIENT_ID, GEO_GA4_CLIENT_SECRET und GEO_GA4_REFRESH_TOKEN nur in der privaten Laufzeit bereitstellen. Erforderlich sind Leserechte für die richtige Property, vorhandene Website-Messung und Analytics-Data-API-Zugriff. Der Bericht erfasst für die Domain zugeordnete Sitzungen nach sessionSource, einschließlich utm_source=chatgpt.com. Fehlende Referrer und ungetaggte Direktzugriffe können keinem Dienst zugerechnet werden.
- **Optionale OpenAI-API**. Erst nach ausdrücklicher Kostenfreigabe GEO_ALLOW_BILLABLE=yes, GEO_OPENAI_KEY und GEO_OPENAI_MODEL setzen und `python3 geo/openai_probe.py Shekhina_GEO_Monitor.html` ausführen. Ergebnisse erscheinen ausschließlich in der Reihe openai-search-api. Der Standardablauf ruft keine kostenpflichtige API auf.
