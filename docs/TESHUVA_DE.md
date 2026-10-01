# Sanhedrin: Fragen, Recherche und Teshuvot

[Frageeditor öffnen](https://shekhina.org/teshuva.html).

## Fragen und lokale Quellen

1. Frage in den Editor schreiben. Fett, Kursiv, Listen, RTL und LTR stehen in der Werkzeugleiste zur Verfügung. Der Sprachschalter ändert Oberfläche und Ausgabesprache zwischen Englisch und Hebräisch.
2. Optional genaue Suchwörter eingeben, etwa `schach mold` oder `סכך עובש`. Ein allgemeines Stichwort wie `sukkah` ist für diese Frage zu breit.
3. Zahl der Vorschauquellen wählen: 3, 6, 8, 12 oder 20.
4. **Find a source-based answer** anklicken und die gefundenen Quellen prüfen.

Die Vorschau vergleicht bis zu 160 Kandidaten und liest bis zu 60 vollständige Datensätze. Beim Speichern mit der neuen Suche wird der gesamte lokale Bestand erneut verglichen, einschließlich aller HTML-Dokumente unter `responsa/` und ihrer hebräischen Fußnoten. Häufige Fachbegriffe werden zwischen Englisch und Hebräisch verbunden; hebräische Präfixe werden berücksichtigt. Titel und Fragen ohne Antworttext werden nicht als Beleg übernommen.

Die API erstellt zunächst kurze Suchanfragen auf Englisch und Hebräisch und zerlegt die Frage in Teilfragen. Der Server prüft die besten 160 lokalen Kandidaten. Eine zusätzliche inhaltliche Prüfung wählt aus bis zu 40 Kandidaten höchstens 16 passende Quellen. Mehrere Antworten bleiben erkennbar getrennt. Kurze Texte werden vollständig übernommen; sehr lange Texte erhalten einen relevanten Ausschnitt mit Kontext, bis zu 16.000 Zeichen pro Quelle. Das gesamte Quellenmaterial ist auf 120.000 Zeichen und 20 Quellen begrenzt. Die Anzahl in der Browser-Vorschau ist keine Vorgabe, ungeeignete Quellen in der fertigen Antwort zu verwenden.

Ohne OpenAI zeigt und speichert die lokale Suche wieder passende Originalantworten mit Quellen und vollständigen Links. Diese Ausgabe heißt „Original answer texts“ und ist von einer neu formulierten Erklärung unterscheidbar. Ein API-Fehler oder eine blockierte externe Seite lässt passende interne Antworttexte nicht verschwinden.

## Zuschaltbare externe Recherche

**Search outside our database** aktiviert die externe Recherche und schaltet gleichzeitig OpenAI ein. Sie wird beim Speichern ausgeführt, nicht beim Anzeigen der lokalen Vorschau. Bei Bedarf bis zu zehn öffentliche HTTPS-URLs in **Additional source URLs** eingeben, eine pro Zeile. Auch öffentliche HTTPS-Links direkt im Fragetext werden erkannt. Alle diese URLs werden nur bei eingeschaltetem Recherchemodus abgerufen.

Sefaria ist ein fester Suchpunkt: Der Ablauf durchsucht die offizielle Bibliotheks-Such-API separat auf Hebräisch und Englisch und lädt konkrete Textstellen mit der offiziellen Text-API. Sefarias Exportdateien liegen inzwischen im öffentlichen Google-Cloud-Storage-Bucket `sefaria-export`, nicht in Google Docs. Der Katalog und die Download-Werkzeuge stehen weiterhin in [Sefaria-Export](https://github.com/Sefaria/Sefaria-Export). Ein vollständiger Massendownload ist für die Recherche nicht erforderlich.

[config/teshuva-research.json](../config/teshuva-research.json) enthält Sefaria sowie die 38 angegebenen Quellen-URLs. Der doppelte Meshiv-Eintrag wurde zusammengeführt. Bis zu zwei kurze englische/hebräische Websuchanfragen pro Rechercherunde suchen nach konkreten veröffentlichten Antworten. Die zugelassenen Domains umfassen diese Quellen, die angegebenen URLs sowie Chabad, Wikisource und Mi Yodeya als zusätzliche Text- und Antwortquellen. Bei nicht agentischer Websuche werden kurze Suchtexte statt großer JSON-Fragepakete übergeben. Es wird nicht jedes Archiv vollständig gespiegelt und kein Frageformular abgeschickt.

Suchtreffer und Links sind Hinweise. Als Beleg wird erst ein tatsächlich gelesener Text verwendet. Gesperrte Seiten, Bot-Verifikationen, reine Formulare, Archive mit Linklisten und fehlgeschlagene Abrufe werden ausgeschlossen und im Rechercheprotokoll vermerkt. Zugriffssperren werden nicht umgangen. Webseitenabrufe berücksichtigen robots.txt, Größen- und Zeitgrenzen. HTTPS-Verbindungen werden auf geprüfte öffentliche IP-Adressen festgelegt; lokale/private Ziele und entsprechende Weiterleitungen sind ausgeschlossen.

Bei externen Antwortseiten werden öffentlich nur ein kurzer zugeschriebener Auszug von höchstens 25 Wörtern, der Original-Link, Abrufzeit und Inhalts-Hash gespeichert. Sefaria-Ausgaben behalten ihre Editions-/Lizenzangaben. Die API darf externe Antworten zusammenfassen, aber nicht lange Passagen übernehmen.

## Speichern und Ergebnisprüfung

**Save in GitHub / Sanhedrin** öffnet eine vorbereitete GitHub-Anfrage. Auf GitHub prüfen und **Submit new issue** wählen. Lange Anfragen lassen sich vollständig kopieren und in das Issue einfügen. Frage und Recherche werden öffentlich gespeichert.

Der Workflow **Save Teshuva** lädt den dauerhaft gesicherten Bestand und übernimmt neue lokale Texte. Eine vollständige API-Antwort muss jede Aussage auf vorhandene Quellennummern beziehen. Ein zweiter API-Durchgang prüft die Unterstützung der Aussagen, die wesentlichen Teilfragen, Unterschiede zwischen Materialien und Behandlungen sowie fehlende Angaben und Einschränkungen.

Die Prüfung erfolgt für jeden Absatz und verlangt für die Aussagen konkrete Textstellen. Die überprüfende API muss die Aussage aus dem Absatz und einen kurzen, wörtlichen Beleg aus der zitierten Quelle zurückgeben. Der Server prüft, dass der Beleg tatsächlich im geladenen Quellentext vorkommt. Ein bloßes „supported=true“ reicht nicht. Die Belegausschnitte bleiben im JSON-Prüfprotokoll, statt zusätzliche lange Zitate in der Antwort darzustellen. Vollständige belegte Antworten werden mit `ready` veröffentlicht; belegte Teilantworten mit `partial` und einem eigenen Abschnitt für offene Punkte. Es bleiben nur die konkret geprüften Aussagen eines Absatzes erhalten; unbelegte Nachbarsätze werden entfernt. Kurze wörtliche Ausdrücke und typografische Unterschiede werden bei der Belegprüfung berücksichtigt. Eine gezielte zweite Recherche versucht fehlende Belege zu finden. Die Frage wird nicht pauschal als unbeantwortbar eingestuft, weil eine Teilfrage offen ist. Rückfragen betreffen nur entscheidende Tatsachen des Falls; die Recherche verlangt vom Nutzer keine bevorzugten Bücher oder Quellen. Gibt es keine geprüfte Formulierung, bleiben passende Originalantworten als `sources` lesbar. Nur wirklich ergebnislose Anfragen bleiben ohne Antwort im Recherchebereich. Die unerwünschten alten Entwurfshinweise werden nicht wieder eingeführt.

Die Dateien bleiben nachvollziehbar unter `Sanhedrin/teshuva-<Issue>-<Hash>.json` und `.html` gespeichert. **Check saved answer** erkennt vollständige Antworten, Teilantworten und Originaltexte. Eine ergebnislose Anfrage hat eine Recherche-Statusseite.

`answer_version: 7` kennzeichnet die neue Verarbeitung. `publication_status` ist `ready`, `partial`, `sources`, `needs_research` oder `needs_clarification`. `openai_status` unterscheidet `draft`, `partial`, `insufficient`, `needs_clarification`, `failed`, `unconfigured`, `disabled` und `owner_only`. Der JSON-Datensatz enthält Suchplan, lokale Trefferzahlen, Quellen-Hashes und das externe Abrufprotokoll. Geheimnisse werden nicht gespeichert. API-Fehler werden mit HTTP-Status und bereinigten Details im Diagnoseprotokoll aufgezeichnet, nicht als technische Fehlermeldung in der Antwort.

Offene Recherche wiederholen: Als Moriahise unter **Actions → Save Teshuva → Run workflow** die offene Issue-Nummer eingeben und **retry_research** wählen. Das kann weitere API-Kosten verursachen. Ein bereits fertiges Ergebnis wird wiederverwendet. Beim erneuten Verarbeiten eines älteren fehlgeschlagenen Issues wird die neue Version einmal angewandt; Identität, Porträt und Zähler bleiben erhalten. Teilantworten erfordern für weitere bezahlte Versuche ebenfalls `retry_research`. Fehlende Angaben über eine neue vorbereitete Anfrage ergänzen. Während der Recherche geschlossene oder geänderte Fragen werden nicht mit einer veralteten Antwort gespeichert; während eines erneuten Versuchs entfernte Dateien werden nicht wiederhergestellt.

## OpenAI einstellen – nur Moriahise

Unter [Settings → Secrets and variables → Actions](https://github.com/Moriahise/Sanhedrin/settings/secrets/actions):

- Secret `OPENAI_API_KEY`: vorhandenen geeigneten Projektschlüssel verwenden. Niemals in Chat, Issue oder Quellcode eintragen.
- Repository variable `OPENAI_ENABLED`: `true` erlaubt API-Nutzung, jeder andere oder fehlende Wert schaltet sie aus.
- Repository variable `OPENAI_MODEL`: gewünschtes Responses-API-Modell; Standard `gpt-4.1-mini`. Für externe Recherche muss das Modell das Werkzeug `web_search` und Structured Outputs unterstützen.

Die geprüften GitHub-Identitäten von Issue-Autor, auslösendem Nutzer und wiederholendem Nutzer müssen alle **Moriahise** sein. Die Freigabe eines fremden Issues gibt keinen Zugriff auf den API-Schlüssel. Öffentliche Besucher brauchen weiterhin eine Repository-Freigabe zur Verarbeitung ihrer Anfrage.

Ein Durchgang benötigt bis zu vier Modellaufrufe: Suchplan, Quellenauswahl, Ausarbeitung und Absatzprüfung. Externe Recherche ergänzt bis zu zwei Websuchaufrufe mit jeweils einem Werkzeugaufruf. Bei offenen Punkten folgt höchstens ein zweiter Durchgang: maximal acht lokale oder zwölf externe Modellaufrufe. Die Verarbeitung bleibt beim konfigurierten Modell; es erfolgt kein automatischer Wechsel auf ein teureres Modell. OpenAI-Websuche wird zusätzlich berechnet. Externe HTTP-Abrufe sind pro Durchgang auf 64 Anfragen und 12 Sekunden pro Verbindung begrenzt. Fehlgeschlagene bezahlte Aufrufe werden nicht blind wiederholt. Die Quellen und die fertige Antwort bleiben fachlich zu prüfen.

Offizielle Dokumentation: [OpenAI-Websuche](https://developers.openai.com/api/docs/guides/tools-web-search), [Sefaria-Suche](https://developers.sefaria.org/reference/post-search-wrapper), [Sefaria-Texte](https://developers.sefaria.org/reference/get-v3-texts).

## Automatische Porträts und Veröffentlichung

Bilder stammen aus `Rav/`; der Dateiname ist der Anzeigename. Die Porträts wechseln der Reihe nach und beginnen nach dem letzten erneut von vorn. Der gemeinsame Zähler in `Sanhedrin/portrait-rotation.json`, Anfrage und Bild werden atomar gespeichert. Wiederholungen behalten Bild und Zähler; gleichzeitig eingereichte Fragen lesen nach einem Konflikt den aktuellen Stand. Das Bild ist ein Darstellungsprofil und schreibt die Antwort nicht dem abgebildeten Rabbiner zu.

Der Speicherworkflow startet anschließend **Publish durable library**. Eine fehlgeschlagene Veröffentlichung kann erneut gestartet werden, ohne die Recherche zu wiederholen. GitHub Pages muss aus **GitHub Actions** veröffentlichen. Die bisherigen vollständigen Texte und gespeicherten Antworten bleiben erhalten.

Die Veröffentlichung verwendet jeweils den neuesten Stand. Neuere Änderungen ersetzen laufende oder wartende ältere Veröffentlichungen. Fehler bei der externen Recherche verhindern eine belegte interne Antwort nicht. Praktische Materialbehandlungen müssen durch passende Belege gestützt sein; allgemeine Grundsätze und sorgfältig bezeichnete Schlussfolgerungen dürfen weiterhin erläutert werden.

GPT-4.1-mini erhält von Anfang an kurze Suchanfragen mit `site:`-Einschränkungen, da das Modell native Domainfilter ablehnt. Für andere Modelle werden native Filter versucht und nur bei einem ausdrücklich nicht unterstützten Filter einmal ersetzt. Modell und Freigaberegeln bleiben gleich; jeder Ergebnis-Link und sein Weiterleitungsziel werden serverseitig gegen die zugelassenen Domains geprüft.
