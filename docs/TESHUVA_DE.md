# Sanhedrin: Fragen, Recherche und Teshuvot

[Frageeditor öffnen](https://shekhina.org/teshuva.html).

## Fragen und lokale Quellen

1. Frage in den Editor schreiben. Fett, Kursiv, Listen, RTL und LTR stehen in der Werkzeugleiste zur Verfügung. Der Sprachschalter ändert Oberfläche und Ausgabesprache zwischen Englisch und Hebräisch.
2. Optional genaue Suchwörter eingeben, etwa `schach mold` oder `סכך עובש`. Ein allgemeines Stichwort wie `sukkah` ist für diese Frage zu breit.
3. Zahl der Vorschauquellen wählen: 3, 6, 8, 12 oder 20.
4. **Find a source-based answer** anklicken und die gefundenen Quellen prüfen.

Die Vorschau vergleicht bis zu 120 Kandidaten und liest bis zu 60 vollständige Datensätze. Beim Speichern mit der neuen Suche wird der gesamte lokale Bestand erneut verglichen, einschließlich aller HTML-Dokumente unter `responsa/` und ihrer hebräischen Fußnoten. Häufige Fachbegriffe werden zwischen Englisch und Hebräisch verbunden; hebräische Präfixe werden berücksichtigt. Titel und Fragen ohne Antworttext werden nicht als Beleg übernommen.

Die API erstellt zunächst kurze Suchanfragen auf Englisch und Hebräisch und zerlegt die Frage in Teilfragen. Der Server prüft die besten 120 lokalen Kandidaten und wählt bis zu 12 passende Quellen. Mehrere Antworten bleiben erkennbar getrennt. Kurze Texte werden vollständig übernommen; sehr lange Texte erhalten einen relevanten Ausschnitt mit Kontext, bis zu 16.000 Zeichen pro Quelle. Das gesamte Quellenmaterial ist auf 100.000 Zeichen und 20 Quellen begrenzt. Die Anzahl in der Browser-Vorschau ist keine Vorgabe, ungeeignete Quellen in der fertigen Antwort zu verwenden.

Ohne OpenAI bleibt die lokale Suche verfügbar. Neue reine Quellenzusammenstellungen werden als offene Recherche gespeichert und nicht als fertige Teshuvot im Antwortarchiv veröffentlicht.

## Zuschaltbare externe Recherche

**Search outside our database** aktiviert die externe Recherche und schaltet gleichzeitig OpenAI ein. Sie wird beim Speichern ausgeführt, nicht beim Anzeigen der lokalen Vorschau. Bei Bedarf bis zu zehn öffentliche HTTPS-URLs in **Additional source URLs** eingeben, eine pro Zeile. URLs werden nur bei eingeschaltetem Recherchemodus abgerufen.

Sefaria ist ein fester Suchpunkt: Der Ablauf durchsucht die offizielle Bibliotheks-Such-API separat auf Hebräisch und Englisch und lädt konkrete Textstellen mit der offiziellen Text-API. Sefarias Exportdateien liegen inzwischen im öffentlichen Google-Cloud-Storage-Bucket `sefaria-export`, nicht in Google Docs. Der Katalog und die Download-Werkzeuge stehen weiterhin in [Sefaria-Export](https://github.com/Sefaria/Sefaria-Export). Ein vollständiger Massendownload ist für die Recherche nicht erforderlich.

[config/teshuva-research.json](../config/teshuva-research.json) enthält Sefaria sowie die 38 angegebenen Quellen-URLs. Der doppelte Meshiv-Eintrag wurde zusammengeführt. Eine zusätzliche OpenAI-Websuche sucht innerhalb dieser Domains und der Domains aus den eingegebenen URLs nach konkreten veröffentlichten Antworten. Es wird nicht jedes Archiv vollständig gespiegelt und kein Frageformular abgeschickt.

Suchtreffer und Links sind Hinweise. Als Beleg wird erst ein tatsächlich gelesener Text verwendet. Gesperrte Seiten, Bot-Verifikationen, reine Formulare, Archive mit Linklisten und fehlgeschlagene Abrufe werden ausgeschlossen und im Rechercheprotokoll vermerkt. Zugriffssperren werden nicht umgangen. Webseitenabrufe berücksichtigen robots.txt, Größen- und Zeitgrenzen. HTTPS-Verbindungen werden auf geprüfte öffentliche IP-Adressen festgelegt; lokale/private Ziele und entsprechende Weiterleitungen sind ausgeschlossen.

Bei externen Antwortseiten werden öffentlich nur ein kurzer zugeschriebener Auszug von höchstens 25 Wörtern, der Original-Link, Abrufzeit und Inhalts-Hash gespeichert. Sefaria-Ausgaben behalten ihre Editions-/Lizenzangaben. Die API darf externe Antworten zusammenfassen, aber nicht lange Passagen übernehmen.

## Speichern und Ergebnisprüfung

**Save in GitHub / Sanhedrin** öffnet eine vorbereitete GitHub-Anfrage. Auf GitHub prüfen und **Submit new issue** wählen. Lange Anfragen lassen sich vollständig kopieren und in das Issue einfügen. Frage und Recherche werden öffentlich gespeichert.

Der Workflow **Save Teshuva** lädt den dauerhaft gesicherten Bestand und übernimmt neue lokale Texte. Eine vollständige API-Antwort muss jede Aussage auf vorhandene Quellennummern beziehen. Ein zweiter API-Durchgang prüft die Unterstützung der Aussagen, die wesentlichen Teilfragen, Unterschiede zwischen Materialien und Behandlungen sowie fehlende Angaben und Einschränkungen.

Nur ein vollständiges Ergebnis mit erfolgreicher Prüfung wird als fertige Antwort veröffentlicht und unter **Saved Teshuvot** aufgeführt. Bei fehlenden Belegen bleibt die Anfrage offen. Bei entscheidenden fehlenden Angaben werden konkrete Rückfragen im GitHub-Issue und auf der Statusseite angezeigt. Die frühere Meldung „The optional API did not produce a usable draft“ und eine bloße Quellenliste erscheinen nicht mehr als fertige Teshuva. Auch ältere unvollständige API-Ergebnisse werden beim nächsten Publizieren aus dem Antwortarchiv ausgeschlossen.

Die Dateien bleiben nachvollziehbar unter `Sanhedrin/teshuva-<Issue>-<Hash>.json` und `.html` gespeichert. Eine offene Anfrage hat dort eine Recherche-Statusseite. **Check saved answer** unterscheidet eine fertige Antwort von einer offenen Recherche.

`publication_status` ist `ready`, `needs_research` oder `needs_clarification`. `openai_status` unterscheidet `draft`, `insufficient`, `needs_clarification`, `failed`, `unconfigured`, `disabled` und `owner_only`. Der JSON-Datensatz enthält Suchplan, lokale Trefferzahlen, Quellen-Hashes und das externe Abrufprotokoll. Geheimnisse und API-Fehlertexte werden nicht gespeichert.

Offene Recherche wiederholen: Als Moriahise unter **Actions → Save Teshuva → Run workflow** die offene Issue-Nummer eingeben und **retry_research** wählen. Das kann weitere API-Kosten verursachen. Ein bereits fertiges Ergebnis wird wiederverwendet. Fehlende Angaben über eine neue vorbereitete Anfrage ergänzen. Während der Recherche geschlossene oder geänderte Fragen werden nicht mit einer veralteten Antwort gespeichert; während eines erneuten Versuchs entfernte Dateien werden nicht wiederhergestellt.

## OpenAI einstellen – nur Moriahise

Unter [Settings → Secrets and variables → Actions](https://github.com/Moriahise/Sanhedrin/settings/secrets/actions):

- Secret `OPENAI_API_KEY`: vorhandenen geeigneten Projektschlüssel verwenden. Niemals in Chat, Issue oder Quellcode eintragen.
- Repository variable `OPENAI_ENABLED`: `true` erlaubt API-Nutzung, jeder andere oder fehlende Wert schaltet sie aus.
- Repository variable `OPENAI_MODEL`: gewünschtes Responses-API-Modell; Standard `gpt-4.1-mini`. Für externe Recherche muss das Modell das Werkzeug `web_search` und Structured Outputs unterstützen.

Die geprüften GitHub-Identitäten von Issue-Autor, auslösendem Nutzer und wiederholendem Nutzer müssen alle **Moriahise** sein. Die Freigabe eines fremden Issues gibt keinen Zugriff auf den API-Schlüssel. Öffentliche Besucher brauchen weiterhin eine Repository-Freigabe zur Verarbeitung ihrer Anfrage.

Eine neue lokale API-Ausarbeitung benötigt bis zu drei Modellaufrufe: Suchplan, Ausarbeitung, Prüfung. Mit externer Recherche kommt ein Websuche-Aufruf hinzu; dessen Werkzeugnutzung ist auf vier Aufrufe begrenzt. OpenAI-Websuche wird zusätzlich berechnet. HTTP-Abrufe sind auf 36 Anfragen und 12 Sekunden pro Verbindung begrenzt. Bei API-Fehlern gibt es keine unbegrenzten Wiederholungen. Eine API-Prüfung garantiert keine halachische Richtigkeit; die Quellen und die fertige Antwort bleiben fachlich zu prüfen.

Offizielle Dokumentation: [OpenAI-Websuche](https://developers.openai.com/api/docs/guides/tools-web-search), [Sefaria-Suche](https://developers.sefaria.org/reference/post-search-wrapper), [Sefaria-Texte](https://developers.sefaria.org/reference/get-v3-texts).

## Automatische Porträts und Veröffentlichung

Bilder stammen aus `Rav/`; der Dateiname ist der Anzeigename. Die Porträts wechseln der Reihe nach und beginnen nach dem letzten erneut von vorn. Der gemeinsame Zähler in `Sanhedrin/portrait-rotation.json`, Anfrage und Bild werden atomar gespeichert. Wiederholungen behalten Bild und Zähler; gleichzeitig eingereichte Fragen lesen nach einem Konflikt den aktuellen Stand. Das Bild ist ein Darstellungsprofil und schreibt die Antwort nicht dem abgebildeten Rabbiner zu.

Der Speicherworkflow startet anschließend **Publish durable library**. Eine fehlgeschlagene Veröffentlichung kann erneut gestartet werden, ohne die Recherche zu wiederholen. GitHub Pages muss aus **GitHub Actions** veröffentlichen. Die bisherigen vollständigen Texte und gespeicherten Antworten bleiben erhalten.

Die Veröffentlichung verwendet jeweils den neuesten Stand: Eine neuere Änderung ersetzt laufende oder wartende ältere Veröffentlichungen, damit entfernte oder erneut als offen markierte Antworten nicht aus einem veralteten Stand erscheinen. Bei einer angeforderten, fehlgeschlagenen externen Recherche wird keine reine Bibliotheksantwort als abgeschlossen ausgegeben. Bei praktischen Materialbehandlungen muss die Recherche den Gegenstand und das konkrete Problem gemeinsam belegen. Die Quellenprüfung bewertet jeden Absatz einzeln auf Unterstützung, Materialbezug, Fragebezug und unzulässige Übertragungen.

GPT-4.1-mini unterstützt Websuche, lehnt aber native Domainfilter ab. In diesem Fall wiederholt der Ablauf den abgewiesenen Suchaufruf genau einmal mit Suchanfragen auf den freigegebenen Domains. Modell und Freigaberegeln bleiben gleich; jeder Ergebnis-Link und sein Weiterleitungsziel werden serverseitig gegen die Quellenliste geprüft. Andere API-Fehler lösen diese Wiederholung nicht aus.
