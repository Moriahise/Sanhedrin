# DIN – manuelle JSON-Uploads

Hier die JSON-Exportdateien der DIN-Browsererweiterung bzw. deren JSON-Inhaltsteile hochladen und auf `main` committen. Die automatische Quellenabfrage ist für DIN deaktiviert; der Import hochgeladener Dateien bleibt aktiv.

Nach dem Commit startet **Publish durable library** automatisch und übernimmt Import, Suche, Sicherung und Website-Veröffentlichung. Original-URLs und Exportmetadaten beibehalten. Neue Exporte mit Datum/Uhrzeit oder eindeutiger Laufnummer ablegen. Alle Inhaltsteile eines Split-Exports hochladen; ZIPs, Split-Manifeste und Protokolle nicht hochladen.

Vollständige Anleitung: [UPLOADS_DE.md](../../../docs/UPLOADS_DE.md).
