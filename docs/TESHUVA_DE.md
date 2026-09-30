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

## Optionale OpenAI-Ausarbeitung – nur Moriahise

OpenAI kann ausschließlich von **Moriahise** verwendet werden. Der Workflow prüft die GitHub-Identität des Issue-Autors, des auslösenden Nutzers und des Nutzers, der einen Lauf wiederholt. Alle drei müssen Moriahise sein. Eine Freigabe fremder Fragen durch `teshuva-approved` erlaubt weiterhin nur die Bestandsantwort. Ein Textfeld im Issue kann diese Identitätsprüfung nicht ersetzen.

### Einmal einrichten

1. Bei [OpenAI API keys](https://platform.openai.com/api-keys) einen Schlüssel für dieses Projekt erstellen oder einen vorhandenen geeigneten Schlüssel verwenden. Die API benötigt eine eigene verfügbare Abrechnung; ein ChatGPT-Abonnement allein stellt kein API-Guthaben bereit.
2. Unter [GitHub → Settings → Secrets and variables → Actions](https://github.com/Moriahise/Sanhedrin/settings/secrets/actions) auf **New repository secret** klicken. Name: `OPENAI_API_KEY`; Secret: den Schlüssel direkt dort einfügen und speichern. Niemals in einen Chat, ein Issue, einen Upload oder eine HTML-Datei schreiben.
3. Unter [Actions → Variables](https://github.com/Moriahise/Sanhedrin/settings/variables/actions) eine **Repository variable** anlegen: Name `OPENAI_ENABLED`, Wert `true`. Ohne diese Variable oder bei jedem anderen Wert bleibt OpenAI ausgeschaltet.
4. Optional `OPENAI_MODEL` als Repository variable setzen. Der voreingestellte Wert ist `gpt-4.1-mini`.

### Im täglichen Betrieb

| Gewünschtes Verhalten | Einstellung |
|---|---|
| Diese Frage nur aus vorhandenen Texten zusammenstellen | Im Editor **Add an OpenAI formulation** nicht anhaken |
| Für diese Frage eine OpenAI-Ausarbeitung erstellen | Hauptschalter `OPENAI_ENABLED=true`; im Editor **Add an OpenAI formulation** anhaken; Issue als Moriahise einreichen |
| Alle neuen API-Aufrufe zentral sperren | In GitHub unter **Settings → Secrets and variables → Actions → Variables** `OPENAI_ENABLED` auf `false` ändern |
| API wieder erlauben | Dieselbe Variable auf `true` ändern |

Den Schlüssel musst du beim Umschalten nicht löschen oder erneut eingeben. Der Editor startet mit ausgeschalteter OpenAI-Option. Eine Vorschau im Browser löst keinen API-Aufruf aus; er erfolgt erst im GitHub-Speicherworkflow. Bereits laufende API-Anfragen lassen sich durch eine spätere Variablenänderung nicht zurücknehmen. Bereits gespeicherte Antworten bleiben erhalten und sind wie das übrige Repository öffentlich lesbar. Die Beschränkung betrifft das **Erzeugen mit deinem API-Schlüssel**, nicht das Lesen.

### Ablauf und Prüfung

Nach der Einreichung erzeugt **Save Teshuva** einen zusammenhängenden Entwurf ausschließlich aus den ausgewählten gespeicherten Passagen. Das HTML/JSON-Paar wird in `Sanhedrin` gespeichert und veröffentlicht. Der Schlüssel wird nur im Workflow übergeben; er steht nicht im Browser. Der Aufruf verwendet die Responses API, ein festes JSON-Schema und `store: false`.

Das gespeicherte JSON zeigt:

- `mode: openai` und `openai_status: draft`: API-Ausarbeitung erfolgreich.
- `openai_status: insufficient`: Die API meldet, dass die Quellen nicht ausreichen; die Bestandsantwort bleibt erhalten.
- `openai_status: disabled`: Hauptschalter aus.
- `openai_status: owner_only`: Anfrage oder auslösender Nutzer ist nicht Moriahise.
- `openai_status: unconfigured`: Schlüssel fehlt.
- `openai_status: failed`: API-Aufruf oder Antwortprüfung fehlgeschlagen. Bei einem HTTP-Fehler wird nur die Statusnummer gespeichert, niemals der geheime Schlüssel oder die HTTP-Antwort.

Bei einem echten erfolgreichen API-Aufruf werden außerdem `openai_response_id` und die verfügbaren Tokenzahlen unter `openai_usage` gespeichert. Diese Angaben ermöglichen die Unterscheidung zwischen einem echten API-Ergebnis und einer Quellenantwort. Quellenverweise werden auf vorhandene Nummern geprüft; die fachliche Richtigkeit des Entwurfs muss weiterhin geprüft werden.

Nach einer fehlenden Konfiguration, einer Sperre oder einem API-Fehler kann Moriahise unter **Actions → Save Teshuva → Run workflow** die offene Issue-Nummer erneut verarbeiten. Bei nun erlaubtem API-Zugriff wird die bisherige Quellenantwort aktualisiert. Ein bereits erfolgreicher API-Entwurf wird wiederverwendet und verursacht keinen erneuten Aufruf.

Offizielle Referenzen: [Quickstart](https://developers.openai.com/api/docs/quickstart), [Responses / Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [GPT-4.1 Mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini).

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
