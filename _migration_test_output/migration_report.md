# migration_report — Dry Run 06.07.2026 13:23:50
Ausgabe ausschließlich nach: _migration_test_output/ — Originaldaten unangetastet.

## Backup (vorbereitet — Kopie mit --backup)
- Umfang: 8 Dateien, 0.0 MB aus: responsa.json, qa_db.json, qa_db, miyodea/qa, data/qa

- Quellen gelesen: 15 Roh-Einträge, davon 4 Duplikate zusammengeführt -> 11 eindeutige Fragen. Pro Quelle: {'miyodea_raw': 6, 'yeshiva_years': 3, 'yeshiva_monolith': 4, 'generated': 2}
- Aus responsa.json angereichert (legacy number): 4 Einträge
- Kategorien aus Altbestand übernommen (legacy, high): 1
- Migriert: 11 Fragen in 3 Chunk-Datei(en)
- Kategorien definiert: 6, davon belegt: 6 (['general', 'halacha', 'history', 'kabbalah', 'talmud', 'tanach'])
- needs_review: 3

## Verifikation (automatisch)
- [OK] 1. Alle Fragen übernommen — Quelle: 11, migriert: 11
- [OK] 2. Alle Antworten übernommen — Antworten Quelle(max je Frage): 12, migriert: 12
- [OK] 3. IDs eindeutig
- [OK] 3b. IDs & Chunk-Zuordnung deterministisch (2. Lauf identisch)
- [OK] 4. Chunk-Dateien korrekt (Limits + Nummerierung) — 3 Chunks, max_per_chunk=4
- [OK] 5. index.json korrekt (Anzahl + Chunk-Verweise + Felder) — count=11
- [OK] 6. categories.json korrekt (6 Kategorien, Labels, Maps konsistent) — Kategorien: ['general', 'halacha', 'history', 'kabbalah', 'talmud', 'tanach']
- [OK] 7. by-category-Dateien korrekt (vollständige Partition) — Summe über Kategorien: 11
- [OK] 8. Unsichere Kategorien mit needs_review markiert (und nur diese) — needs_review: 3
- [OK] 9. Keine verlorenen Felder (url/tags/score/views/date/legacy) — Stichproben vollständig
- [OK] 10. Sonderzeichen/Hebrew/HTML/Markdown unversehrt — 11 Proben ok
- [OK] BONUS: Originaldaten unverändert (git status) — nur Output-Ordner neu

**Gesamtergebnis: ALLE PRÜFUNGEN BESTANDEN**
