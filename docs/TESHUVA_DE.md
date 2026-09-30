# Sanhedrin: Fragen eingeben und Teshuvot speichern

## Öffnen

[Frageeditor öffnen](https://shekhina.org/teshuva.html). Der Link **Ask a question / שאלה ותשובה** steht auch oben in der Bibliothek.

## Eine Antwort ohne API erstellen

1. Frage in das große Eingabefeld schreiben. Fett, Kursiv, Liste und Rückgängig stehen in der Werkzeugleiste zur Verfügung. **RTL** stellt den Editor auf hebräische Schreibrichtung, **LTR** auf englische. Der Sprachschalter ändert die Oberfläche und die Ausgabesprache.
2. Bei längeren Fragen unter **Search words / מילות חיפוש** einige genaue Suchwörter eintragen, beispielsweise `shabbat candles` oder `נרות שבת`. Die Suche berücksichtigt den vollständigen hebräischen und englischen Bestand. Eine gemeinsame Wortliste verbindet häufige Themen beider Sprachen; sie ist keine allgemeine Übersetzung jeder beliebigen Frage.
3. Rechts ein Rabbinerprofil und 3, 6 oder 8 Quellen wählen. Die 71 vorhandenen Bilder kommen aus `Rav`. Der Dateiname ohne Erweiterung ist der Anzeigename.
4. **Find a source-based answer / איתור תשובה מבוססת מקורות** anklicken.
5. Die Antwort zeigt relevante gespeicherte Antwortpassagen bzw. Artikel-/Dokumenttexte. Jeder Beleg enthält den Titel, die Herkunft, den gespeicherten Volltext und gegebenenfalls den Originalverweis. Ein längerer Text wird als Auszug gekennzeichnet.

Titel, reine Fragen ohne Antwort und Link-Platzhalter werden nicht als Antwortbelege verwendet. Ohne passende gespeicherte Texte erscheint eine klare Fehlanzeige. Die Funktion erfindet daraus keine Teshuva. Die Bestandsantwort ist eine Quellenzusammenstellung zur Prüfung; sie entscheidet nicht selbständig zwischen widersprechenden halachischen Positionen.

Das Bild ist ein Darstellungsprofil. Die ursprünglichen Autoren werden an den Quellen genannt. Das Profil behauptet nicht, dass der abgebildete Rabbiner den automatisch erzeugten Entwurf verfasst oder genehmigt hat.

## In GitHub speichern

1. Nach der Quellenantwort **Save in GitHub / Sanhedrin** anklicken.
2. Eine vorbereitete GitHub-Pflichtbestätigung öffnet sich als Issue. Die JSON-Anfrage enthält deine Frage, Sprache, Profil und die IDs der angezeigten Quellen. **Submit new issue** anklicken; erst damit wird sie eingereicht. Die Frage und Antwort werden öffentlich gespeichert.
3. Bei einer sehr langen Frage erscheint der Kopierweg: **Copy request**, anschließend **Open GitHub submission**, Inhalt ins große Issue-Feld einfügen und **Submit new issue** wählen. Die Seite zeigt die vollständige Anfrage auch als auswählbaren Text.
4. [GitHub Actions](https://github.com/Moriahise/Sanhedrin/actions) zeigt den Lauf **Save Teshuva**. Er lädt den dauerhaft gesicherten Bestand, übernimmt neue lokale Uploads und erzeugt das HTML/JSON-Paar in [Sanhedrin](https://github.com/Moriahise/Sanhedrin/tree/main/Sanhedrin).
5. Anschließend startet er ausdrücklich **Publish durable library**. Nach erfolgreichem Deploy erscheint die Teshuva unten im Frageeditor unter **Saved Teshuvot**. Das Issue erhält einen Link zu den Dateien und zur veröffentlichten Antwort.
6. Zur Rückkehr nach einem abgebrochenen Vorgang kann im Editor die **GitHub issue number** eingetragen und **Check saved answer** gewählt werden. Eine wiederholte Verarbeitung verwendet eine bereits gespeicherte Antwort. Eine geänderte Frage bekommt eine neue Datei; die vorige bleibt erhalten.

Dateinamen: `Sanhedrin/teshuva-<Issue-Nummer>-<Anfrage-Hash>.html` und `.json`.

Ein Besucher mit GitHub-Konto kann eine Anfrage einreichen. Automatisch verarbeitet werden Anfragen, deren Verarbeitung ein Repository-Inhaber oder Nutzer mit Schreibrechten auslöst. Öffentliche Besucher benötigen Freigabe: Als Repository-Verantwortlicher das Label **teshuva-approved** hinzufügen oder unter **Actions → Save Teshuva → Run workflow** die Issue-Nummer eingeben. Ein externer Besucher kann den API-Schlüssel dadurch nicht eigenständig verwenden. Nach einer weiteren Änderung an seiner Frage ist eine erneute Freigabe erforderlich.

## Optionale OpenAI-Ausarbeitung

Die Option **Add an OpenAI formulation** ist zunächst aus. Die Vorschau im Browser bleibt eine Bestandsantwort. Wenn die Option eingeschaltet ist, erstellt der GitHub-Workflow nach der bestätigten Einreichung zusätzlich einen zusammenhängenden Entwurf ausschließlich aus den ausgewählten gespeicherten Passagen.

Einmalig im Repository:

1. [Settings → Secrets and variables → Actions](https://github.com/Moriahise/Sanhedrin/settings/secrets/actions) öffnen.
2. Unter **Repository secrets → New repository secret** einen Schlüssel namens **OPENAI_API_KEY** anlegen.
3. Optional unter **Variables** die Variable **OPENAI_MODEL** anlegen. Ohne diese Variable wird `gpt-4.1-mini` verwendet.

Der Schlüssel gehört nicht in JSON-Uploads, HTML-Dateien oder den Browsereditor. Er wird nur im Workflow verwendet. Der API-Aufruf nutzt die Responses API mit einem festen JSON-Schema und `store: false`. Quellenverweise werden auf vorhandene Nummern geprüft. Diese technische Prüfung garantiert nicht die inhaltliche Richtigkeit jeder Schlussfolgerung; der Entwurf und seine Anwendung benötigen weiterhin Prüfung.

Wenn der Schlüssel fehlt, die API nicht erreichbar ist, die Antwort abbricht oder ungültige Quellenverweise enthält, werden die gespeicherten Quellenpassagen als Bestandsantwort ausgegeben. Der Status steht im gespeicherten JSON und im Ergebnis des Issues. Es wurde kein kostenpflichtiger API-Test mit einem privaten Schlüssel durchgeführt; die API-Schnittstelle wurde mit simulierten gültigen und fehlerhaften Antworten geprüft.

Offizielle Referenzen: [Responses / Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [GPT-4.1 Mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini).

## Bilder und frühere Platzhalter

Neue Portraits mit dem gewünschten Anzeigenamen als PNG, JPG, JPEG, WEBP oder GIF in [Rav](https://github.com/Moriahise/Sanhedrin/tree/main/Rav) hochladen. Nach Veröffentlichung stehen sie in der Auswahl. Bereits für gespeicherte Antworten verwendete Bilder sollten erhalten bleiben.

Frühere Platzhalter werden nicht als gespeicherte Teshuvot veröffentlicht. Nur die vom neuen Workflow erzeugten JSON-Dateien werden in den Antwortkatalog übernommen. Die HTML-Ausgabe wird beim Publizieren erneut aus der geprüften JSON-Datei erzeugt.

## Veröffentlichung und Fehlerbehebung

Die öffentliche Website benötigt **Settings → Pages → Build and deployment → Source → GitHub Actions**. Solange GitHub stattdessen aus dem Branch veröffentlicht, kann sein alter Pages-Lauf die erzeugte Website überschreiben. Die vorhandene GitHub-Verbindung kann diese Administrationseinstellung nicht ändern.

- Keine passende Antwort: genauere Suchwörter verwenden und prüfen, ob vollständige Antworttexte bereits importiert wurden.
- Speicherung noch nicht sichtbar: das Issue und den Lauf **Save Teshuva** prüfen, dann **Publish durable library**.
- Öffentlicher Besucher wartet: das Issue mit **teshuva-approved** freigeben oder den Speicherworkflow mit der Issue-Nummer starten.
- Speicherung erfolgreich, Veröffentlichung fehlgeschlagen: **Publish durable library** erneut starten. Das HTML/JSON-Paar bleibt im Repository erhalten.
- API nicht verfügbar: Bestandsmodus funktioniert weiterhin.
