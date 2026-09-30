# Sanhedrin – Einrichtung, Betrieb und Wiederherstellung

Diese Anleitung beschreibt die neue Umsetzung. Die Datenbank speichert den dauerhaften Bestand; die Website wird daraus als statisches Verzeichnis `dist` erzeugt. Browsererweiterungen, manuelle Exporte und das Aufteilen neuer JSON-Dateien sind für den automatischen Betrieb nicht erforderlich.

## Was erhalten bleibt

Alle **63.051 ursprünglichen öffentlichen IDs**, **260.640 historische Alias-Verweise**, sämtliche **246 Fragen des ersten Yeshiva-Uploads von 2026** und die **17 Responsa-Dokumente** werden geprüft. Die Migration aus dem Repository ergibt 64.264 Einträge. Erfolgreiche Quellenläufe erhöhen diesen Bestand.

Die Originalarchive und `responsa.json` bleiben als Eingaben und Rückfallbestand im Repository. Die neue Website lädt `responsa.json` nicht mehr. Neue Inhalte werden in der transaktionalen Datenbank gespeichert und als kleine, versionierte Dateien veröffentlicht.

## Website auf dem eigenen Rechner starten

Voraussetzungen: Git, Python ab 3.12, freier Speicher für Repository, Datenbank, Website und Sicherung. Die hier verwendeten Befehle gelten für Linux/macOS; unter Windows heißt der Python-Pfad im virtuellen Umfeld üblicherweise `.venv\Scripts\python.exe`.

```bash
git clone https://github.com/Moriahise/Sanhedrin.git
cd Sanhedrin
python3 -m venv .venv
.venv/bin/pip install -r requirements-test.txt
.venv/bin/python -m sanhedrin migrate
.venv/bin/python tools/audit_library.py --repeat
.venv/bin/python -m sanhedrin sync
.venv/bin/python -m sanhedrin build
.venv/bin/python -m sanhedrin verify-export
.venv/bin/python -m http.server 8000 --directory dist
```

Danach `http://localhost:8000` öffnen. Den Server mit Strg+C beenden. Bei Bedarf kann `sync` ausgelassen werden: Die Migration und Website funktionieren mit den lokalen Originaldaten. Die moderne Website muss aus **`dist`** ausgeliefert werden; ein Server im Repository-Hauptverzeichnis zeigt die alte Oberfläche.

Rückgabecodes: 0 = erfolgreich; 2 = Quellenlauf teilweise erfolgreich oder verschoben; 1 = Befehl fehlgeschlagen. Bei Code 2 bleiben vorhandene Texte erhalten und andere Quellen werden weiter bearbeitet. Ein neuer Website-Build ist weiterhin möglich.

## GitHub Pages und tägliche Automatik

Nach der Integration in `main`:

1. Im Repository **Settings → Pages → Build and deployment → Source → GitHub Actions** auswählen. Diese Einstellung ist einmalig erforderlich.
2. Unter **Actions → Publish durable library** den Lauf prüfen. Ein Push der relevanten Änderungen auf `main` startet die Veröffentlichung; **Run workflow** startet sie manuell.
3. Optional unter **Settings → Secrets and variables → Actions** den Secret **`STACKEXCHANGE_KEY`** setzen. Ohne Schlüssel gelten die anonymen API-Limits.
4. Der tägliche Lauf ist auf **03:17 UTC** eingestellt: 05:17 während der österreichischen Sommerzeit und 04:17 während der Winterzeit. GitHub kann den tatsächlichen Start verzögern.
5. Unter `status.html` stehen die letzten Quellenprüfungen. Im Actions-Lauf meldet der Job **health** Quellenfehler und fehlgeschlagene Veröffentlichungen.

Der Ablauf stellt zuerst die letzte geprüfte Datenbanksicherung aus GitHub Releases wieder her. Dann importiert er geänderte lokale Eingaben, prüft Quellen, kontrolliert alte IDs, erzeugt die Website, sichert den neuen Zustand und veröffentlicht erst danach. Die Sicherung geht nicht mit einem kurzlebigen Runner-Cache verloren.

Ein teilweiser Quellenfehler hält eine geprüfte Veröffentlichung nicht auf: Die vorhandenen Inhalte bleiben erreichbar. Der abschließende `health`-Job wird dann bewusst als fehlgeschlagen markiert, damit der Quellenfehler nicht übersehen wird.

## Quellen und ihre tatsächlichen Grenzen

| Quelle | Aktivierter Weg | Umfang |
|---|---|---|
| Mi Yodeya | Offizielle Stack-Exchange-API | Fragen und alle bestätigten nativen Antworten, Originalverweise, Autoren, Lizenz und belegte Annahme einer Antwort |
| DIN | WordPress-API | Neue/geänderte Metadaten und Originalverweise; vorhandene vollständige Texte bleiben erhalten |
| Aish | WordPress-API, Ask-The-Rabbi-Kategorie 3504 | Metadaten und Originalverweise; vorhandene Texte bleiben erhalten |
| Chabad | Offizieller Magazin-RSS-Feed, gemäß deiner Freigabe aktiviert | Titel, Veröffentlichungsdatum und Originalverweise; der Feed ist kein vollständiges historisches Q&A-Archiv |
| Yeshiva | Direkte Quellenprüfung und vorbereiteter Publisher-Feed-Adapter | Die Website liefert bei Direktabrufen teilweise HTTP 403; zuverlässige neue Erfassung benötigt einen zugelassenen Feed/API-Zugang |

Chabad-Feed: `https://www.chabad.org/tools/rss/magazine_rss.xml`. Er wurde real abgerufen und der Adapter hat erfolgreich Einträge übernommen. Die Artikelnummer aus `article.asp?aid=…` wird derselben Quelle zugeordnet wie `/aid/…`; vorhandene Texte werden dadurch nicht als neue Artikel dupliziert.

Für Yeshiva ist kein erfundener Zugang hinterlegt. Ein freigegebener Publisher-Feed lässt sich über `config/sources.json` mit `adapter: "json_feed"`, tatsächlichem HTTPS-Endpunkt und erlaubten Hosts einrichten. Das genaue JSON-Format steht in [operations.md](operations.md). Volltextbetrieb für eine weitere Quelle benötigt `mode: "full"` und eine dokumentierte `permission_reference`. Eventuelle Zugangsschlüssel gehören in Secrets bzw. die Ausführungsumgebung, nicht ins Repository.

## Suche und Ansicht

Die Suche durchsucht Fragen und Antworten vollständig. Hebräische Vokalzeichen werden ignoriert. Kontrollierte englische Schreibvarianten wie `shabbos` und `shabbat` treffen denselben Index. Es gibt keine automatische hebräische Wortstammerkennung.

**Veröffentlichungsjahr** und **Importjahr** sind getrennte Filter. So bleibt der erste Yeshiva-Import von 2026 auffindbar, ohne die ursprünglichen Fragen fälschlich auf 2026 zu datieren. Ein gestrichelter Kartenrahmen bedeutet **Kategorie muss geprüft werden**. Er bedeutet nicht, dass eine Antwort fehlt. „Keine Antworten laut Quelle“ setzt eine vollständige erfolgreiche Prüfung mit tatsächlichem Remote-Zähler 0 voraus.

Alte Links `qa.html?id=…&src=…` werden mit ihrem ursprünglichen Kontext aufgelöst. Eine nackte Nummer kann bei mehreren Quellen einen Auswahldialog anzeigen. Der Mi-Yodeya-Link bleibt ein Mi-Yodeya-Link, auch wenn eine alte Kennzeichnung ihn als Yeshiva bezeichnet hat.

## Sicherung und Rückkehr zum alten Stand

Der ursprüngliche `main` wird vor der Integration als eigener Backup-Branch gesichert. Backup-Branch: `backup/main-before-modernization-2026-09-30-c18ee5c`. Gesicherter Commit: `c18ee5c8771fd0e1e2bb0ee3c72f29d6d25f507a`. Eine lokale Kopie ist mit `git clone --branch <Backup-Branch> ...` möglich. Ein späterer Produktions-Rollback sollte mit einem nachvollziehbaren Revert-Commit erfolgen; den aktuellen `main` nicht ungeprüft gewaltsam zurücksetzen.

Die laufenden Datenbanksicherungen stehen in GitHub Releases unter Tags `sanhedrin-state-...`. Jede enthält `library.sqlite.gz` und `snapshot.json`. Beide Dateien zusammen herunterladen. Eine unvollständige oder beschädigte letzte Sicherung stoppt den automatischen Restore; der Publisher setzt den Bestand dann nicht stillschweigend zurück.

Lokale Sicherung:

```bash
.venv/bin/python -m sanhedrin snapshot --directory .sanhedrin/snapshot
```

Wiederherstellung: Zuerst Publisher und andere Datenbankzugriffe beenden. Dann:

```bash
.venv/bin/python -m sanhedrin restore --directory .sanhedrin/snapshot
.venv/bin/python -m sanhedrin verify
.venv/bin/python tools/audit_library.py
.venv/bin/python -m sanhedrin build
.venv/bin/python -m sanhedrin verify-export
```

Die Wiederherstellung prüft komprimierte und unkomprimierte SHA-256, Größe, Datenbankintegrität, ursprüngliche IDs, Revisionen und logischen Bestands-Hash, bevor sie die aktuelle Datenbank ersetzt. Die Standard-Mindestzahl beträgt 63.051. Alte Sicherungen werden nicht automatisch gelöscht. Für längeren Betrieb mehrere geprüfte Generationen und eine unabhängige Kopie aufbewahren.

## Tests und Fehlerdiagnose

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/audit_library.py --repeat
.venv/bin/python -m playwright install chromium
.venv/bin/python tools/browser_checks.py
```

Berichte und Screenshots stehen unter `test-results/`; GitHub stellt sie als Workflow-Artefakte bereit. Der Browser-Test prüft echte Navigation, Suche, Quellkollisionen, alte Links, Dokumente, Mobilansicht und verständliche Fehleranzeigen. Die Unit-Tests prüfen unter anderem Transaktionsabbrüche, unvollständige Antworten, Quoten, wiederholte API-Seiten, HTML-Sicherheit und beschädigte Sicherungen.

Bei **HTTP 403** ist die Quellenprüfung blockiert; vorhandene Inhalte bleiben erhalten. Bei **quota/backoff/budget** wird die Arbeit am gespeicherten Cursor fortgesetzt. Bei **Snapshot checksum mismatch** die Dateien nicht überschreiben, sondern eine andere vollständig geprüfte Sicherung gezielt wiederherstellen. Bei **Another publisher holds the state lock** den laufenden Prozess prüfen; kein zweites Schreibprogramm parallel starten.

## Dauerhafter Serverbetrieb als Alternative

Für einen eigenen Linux-Server liegen systemd-Service und Timer unter `ops/systemd/`. Sie verwenden `/srv/sanhedrin/repository`, `/var/lib/sanhedrin` und `/srv/sanhedrin/public/current`. Die Veröffentlichung wechselt den `current`-Link erst nach Prüfungen und Sicherung. Die genaue Installation steht in [operations.md](operations.md).

GitHub kann Zeitpläne öffentlicher Repositories nach 60 Tagen ohne Repository-Aktivität deaktivieren. Wenn ein unterbrechungsfreier Zeitplan erforderlich ist, den eigenen Host als **einzigen Publisher** wählen und dessen Berichte überwachen. Der Server ist vorbereitet, aber nicht automatisch bereitgestellt. Actions und Server dürfen nicht mit zwei voneinander getrennten Beständen gleichzeitig veröffentlichen.
