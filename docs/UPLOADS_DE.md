# Sanhedrin – Browserexporte hochladen und automatisch veröffentlichen

Stand: 30. September 2026. Repository: [Moriahise/Sanhedrin](https://github.com/Moriahise/Sanhedrin), Branch **main**.

**Mi Yodeya wird automatisch abgefragt. Yeshiva, DIN, Aish und Chabad erfasst du mit deinen Browsererweiterungen. Nach dem Hochladen übernimmt die gemeinsame Pipeline die weitere Verarbeitung automatisch.**

## 1. Wo du die Dateien hochlädst

| Quelle | Upload-Ordner auf main | Erfassungsweg |
| --- | --- | --- |
| Mi Yodeya | Kein regelmäßiger manueller Upload erforderlich | Automatische Stack-Exchange-API-Abfrage |
| Yeshiva | [data/qa/yeshiva/](https://github.com/Moriahise/Sanhedrin/tree/main/data/qa/yeshiva) | `yeshiva-extension-v1.2` |
| DIN | [data/qa/din/](https://github.com/Moriahise/Sanhedrin/tree/main/data/qa/din) | `din-extension-v3` |
| Aish | [data/qa/aish/](https://github.com/Moriahise/Sanhedrin/tree/main/data/qa/aish) | `aish-extension-v2` |
| Chabad | [data/qa/chabad/](https://github.com/Moriahise/Sanhedrin/tree/main/data/qa/chabad) | `chabad-extension` |

Die Ordner sind vorbereitet. Die bisherigen Dateien direkt unter `data/qa/` bleiben ebenfalls Importquellen. Für neue Exporte verwendest du die passenden Unterordner. Die Quelle wird anhand der Original-URL erkannt; der Ordnername ersetzt die Original-URL nicht.

## 2. Exportdateien vorbereiten

1. Auf der jeweiligen Website mit der passenden Browsererweiterung erfassen und als **JSON** exportieren.
2. Original-IDs, Original-URLs, Frage-/Artikeltexte, Antworten und Exportdatum beibehalten. Die bestehenden Exportformate mit `questions`, `answer` bzw. `answers` werden eingelesen. Du musst das JSON nicht von Hand umschreiben.
3. Kleine Exporte kannst du direkt hochladen. Für große DIN-, Aish- und Chabad-Exporte kannst du deine vorhandenen quellspezifischen Splitter weiterverwenden:

| Quelle | Vorhandener Splitter |
| --- | --- |
| DIN | `DIN_JSON_SPLITTER_GITHUB_V3` |
| Aish | `AISH_JSON_SPLITTER_GITHUB_V3` |
| Chabad | `CHABAD_JSON_SPLITTER_GITHUB_V2` |

GitHub erlaubt beim Upload im Browser höchstens **25 MiB je Datei** und bis zu **100 Dateien je Upload**. Für geteilte Dateien empfehle ich höchstens **20 MB je Teil**. Es werden vollständige JSON-Dateien benötigt; eine Datei nicht mit einem Texteditor an beliebigen Stellen zerschneiden. Quelle: [GitHub – Adding a file to a repository](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository).

**Alle JSON-Inhaltsteile** eines Exports hochladen, beispielsweise `part_001_of_023.json` bis `part_023_of_023.json`. Wenn du Teile hochlädst, den zusätzlichen ungeteilten Gesamtexport nicht im selben Lauf hochladen. ZIP-Archive, Split-Manifeste, Paket-Manifeste, README-Dateien und Protokolle gehören nicht zu den Inhaltsdateien für den Import. Die vorhandenen Splitter-Pakete enthalten solche Hilfsdateien; lade nur die erzeugten Inhalts-JSONs hoch.

Neue Exporte mit Datum/Uhrzeit oder einer eindeutigen Laufnummer ablegen, zum Beispiel `din-qa-database-2026-09-30_part_001_of_003.json`. Bei zwei Exporten am selben Tag eine Uhrzeit oder Laufnummer ergänzen. Die Namen zusammengehöriger Teile beibehalten. Vorhandene Exporte nicht vorher löschen; ein neuer Upload ist ein zusätzlicher nachvollziehbarer Import.

## 3. In GitHub hochladen

1. Den passenden Ordner aus der Tabelle öffnen. Oben muss der Branch **main** ausgewählt sein.
2. **Add file → Upload files** wählen.
3. Die JSON-Datei bzw. alle Inhaltsteile auf das Upload-Feld ziehen oder mit **choose your files** auswählen. Vor dem Commit warten, bis alle Dateien hochgeladen sind.
4. Eine Commit-Nachricht eintragen, zum Beispiel **DIN-Upload 2026-09-30 – 3 Teile**.
5. **Commit directly to the main branch** auswählen und **Commit changes** bestätigen. Falls GitHub nur einen neuen Branch erlaubt, anschließend den Pull Request nach `main` zusammenführen; erst dessen Integration startet die Veröffentlichung.

Mehrere Teile einer Quelle möglichst in einem Commit hochladen. Bei mehreren Quellen deren Ordner nacheinander verwenden. Jeder Commit kann einen Lauf starten; die gemeinsame Pipeline führt Veröffentlichungen nacheinander aus.

## 4. Was danach automatisch geschieht

Der Commit unter `data/qa/` startet **Publish durable library** automatisch:

1. Letzte geprüfte Datenbanksicherung aus GitHub Releases wiederherstellen.
2. Neue oder veränderte Upload-Dateien einlesen, einschließlich der Unterordner.
3. Anbieter und stabile Identitäten anhand der Original-URLs bestimmen. Neue Einträge einfügen; bestehende Einträge um verfügbare Inhalte ergänzen. Identische bereits importierte Dateien werden über ihren Inhaltshash erkannt. Ein wiederholter Export ist keine Anweisung, vorhandene Texte zu löschen.
4. Nur **Mi Yodeya** automatisch abfragen. DIN, Aish, Chabad und Yeshiva werden von diesem Quellenlauf nicht im Internet abgefragt.
5. Bestand kontrollieren, Katalog und Volltextsuche erzeugen.
6. Geprüfte Datenbanksicherung dauerhaft speichern und die Website veröffentlichen.

**Du musst keine Python-Skripte auf deinem PC starten und keine Indexdateien von Hand bearbeiten.** `responsa.json`, `data/questions/`, Katalogdateien und Datenbanksicherungen werden nicht als Upload-Ziel verwendet. Die frühere Quelle ist weiterhin im historischen Bestand enthalten; die deaktivierte Automatik deaktiviert ausschließlich die Live-Abfrage.

### Wenn der Eintrag bereits ohne Volltext vorhanden ist

Dein Browserexport wird **nicht wegen der Dublette abgewiesen**. Ein vorhandener Quellenlink wird um den fehlenden Frage-/Artikeltext und die fehlenden Antworten ergänzt. Seine öffentliche ID und bestehende Links bleiben erhalten. Die Kennzeichnung wechselt von **Source links** zu **Questions & answers** bzw. **Articles**; der Hinweis **Full text not available locally** entfällt.

Das gilt für DIN, Yeshiva, Chabad und Aish. Yeshiva und Chabad werden über ihre Quellen-ID erkannt; DIN und Aish außerdem über die ursprüngliche URL, auch wenn der frühere API-Eintrag eine andere ID verwendet. Original-URLs im Export beibehalten. Der gleiche Titel allein reicht nicht zum Zusammenführen.

Eine vollständig identische Datei wird als bereits importiert übersprungen. Ein neuer Export mit nachgeliefertem Inhalt wird eingelesen. Bestehende nichtleere Fragetexte oder Antwortlisten werden im manuellen Ergänzungsmodus nicht pauschal ersetzt; dieser Ablauf füllt fehlende Inhalte. Wenn ein schon vorhandener Text nur ein Auszug ist oder berichtigt werden soll, muss dieser Fall gesondert geprüft werden.

**License not recorded in the original import** bezeichnet eine fehlende Lizenzangabe. Dieser Hinweis blockiert den Inhaltsimport nicht und ist unabhängig davon, ob der Volltext vorhanden ist.

## 5. Erfolg kontrollieren

1. [GitHub Actions](https://github.com/Moriahise/Sanhedrin/actions) öffnen.
2. Den zu deinem Upload-Commit gehörenden Lauf **Publish durable library** öffnen.
3. Die Jobs **prepare**, **deploy** und **health** prüfen. Ein Lauf kann mehrere Minuten dauern; ein wartender Lauf beginnt nach der vorherigen Veröffentlichung.
4. Wenn du Einzelheiten brauchst: unter **prepare → Migrate new local inputs** stehen die Importzahlen. Unter den Workflow-Artefakten enthält **publication-report** die `migration.json`: dort sind je Datei `records`, `inserted`, `updated`, `unchanged` und gegebenenfalls `quarantined` dokumentiert.
5. Nach erfolgreichem Deploy [shekhina.org](https://shekhina.org/) öffnen, gegebenenfalls **Strg+F5** drücken und nach einem Titel aus deinem Export suchen. Zusätzlich den passenden **Source**-Filter wählen. Ein einzelner neuer Export erhöht die Gesamtzahl nicht zwingend: vorhandene Datensätze können ergänzt worden sein.

`quarantined` bedeutet, dass ein Datensatz beim Import nicht veröffentlicht wurde und mit Fehlergrund erhalten bleibt, beispielsweise ein technischer Fehlerplatzhalter. Wenn ein Titel fehlt, zuerst den Importbericht prüfen. Bei Syntaxfehlern in einer JSON-Datei scheitert der Import; den fehlerhaften Export korrigieren, erneut committen und den anschließenden Lauf prüfen.

Ein grüner **Validate library**-Lauf prüft den Code und den Bestand. Die tatsächliche Veröffentlichung wird durch **Publish durable library → deploy** nachgewiesen.

## 6. Mi Yodeya läuft selbständig

Die tägliche Veröffentlichung ist auf **03:17 UTC** eingestellt: **05:17 Uhr** österreichischer Sommerzeit, **04:17 Uhr** Winterzeit. GitHub kann den Start verzögern. Bei jedem automatischen Lauf werden Mi-Yodeya-Quellenstände geprüft, Inhalte aktualisiert und Sicherung sowie Website erneuert. Ein API-Schlüssel ist optional; ohne Schlüssel gelten die anonymen Limits.

Die Abfrage behandelt neue/geänderte Fragen und rotiert durch ältere Einträge. Das ist kein täglicher Vollabruf aller historischen Fragen. API-Quoten, Backoff und Fortsetzungsstände werden berücksichtigt; verschobene Abfragen können in späteren Läufen fortgesetzt werden. Der Zustand liegt in der dauerhaft gesicherten Datenbank.

Die übrigen vier Quellen zeigen im automatischen Quellenstatus **Collection disabled**. Das bedeutet: automatische Online-Abfrage ausgeschaltet. Ihre vorhandenen Inhalte und deine manuellen Uploads werden weiterhin veröffentlicht.

## 7. Einmalige Pages-Einstellung

Im Repository **Settings → Pages → Build and deployment → Source → GitHub Actions** auswählen. Diese Einstellung ist aus der vorherigen Einrichtung noch offen. Sie verhindert, dass ein zusätzlicher alter Pages-Lauf die frühere Oberfläche aus dem Repository-Hauptverzeichnis veröffentlicht.

Die aktuelle Website wurde bereits mit der neuen Pipeline veröffentlicht. Die Einstellung konnte von der Assistenz bisher nicht umgestellt werden, weil der Browser nicht bei GitHub angemeldet war und die automatische Freigabeprüfung den Anmeldestart ohne ausdrückliche Anmeldefreigabe abgelehnt hat. Du kannst die Einstellung selbst in deinem angemeldeten GitHub vornehmen. Zugangsdaten gehören nicht in den Chat.

Nach dieser einmaligen Einrichtung genügt im Alltag: **Erfassen → JSON exportieren → passenden Ordner öffnen → auf main hochladen und committen → automatischen Lauf prüfen.**

Weitere Betriebs- und Wiederherstellungsdetails: [BETRIEB_DE.md](BETRIEB_DE.md).
