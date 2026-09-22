# P04-B übernehmen und den Entwicklungsstand sichern

Stand: 22.09.2026. Auftrag: die exakt freigegebene P04-B-Version technisch
übernehmen, deutsche Druckproben prüfen und die Arbeit auf dem bestehenden
Entwicklungsbranch auch im Remote-Repository sichern.

## Umfang und Grenzen

- Die Freigabe gilt für `p04-source-detail-20260922-b`, nicht für neue Pixel.
- Keine neue Bildgenerierung, keine Änderung anderer installierter Master.
- Keine Veröffentlichung einer v10-Version, kein Tag, kein Merge und keine
  Freigabe der übrigen noch offenen Panoramen.
- Private Renderer-Konfiguration, heruntergeladene Quellen und temporäre
  Render-Arbeitsverzeichnisse werden nicht in Git aufgenommen.
- Bestehende PDF-/ZIP-Release-Kandidaten bleiben unverändert und unfreigegeben.

## Arbeitsliste

- [ ] Bestehende Commits auf `codex/v10-refresh` mit dem Remote abgleichen.
- [ ] Lokale Code-, Konfigurations- und Review-Arbeit auf sichere Inhalte prüfen,
  den Teststand erfassen und als Entwicklungsstand committen und pushen.
- [ ] P04-B-Freigabe und sämtliche gebundenen Dateien erneut verifizieren;
  bisherigen P04-Bestand rückholbar sichern.
- [ ] Genau P04-B regulär übernehmen; Master, Vorschau und alle neun Karten
  pixelgenau abgleichen und die übrigen 41 Master auf Unverändertheit prüfen.
- [ ] Zwei deutsche Panorama-Druckproben mit dem Produktionsrenderer erstellen;
  alle vier PDF-Seiten sowie Bildpixel, A4-Geometrie und Platzierungen prüfen.
- [ ] Ergebnis und offene Grenzen dokumentieren, gezielt committen und pushen;
  Remote-Commit abschließend unabhängig vergleichen.

## Ausführungsentscheidungen

Ruling: Im vorhandenen `codex/v10-refresh`-Checkout fortsetzen, keine neue
Arbeitskopie erstellen. Der Auftrag betrifft ausdrücklich den dort vorhandenen
uncommitteten Arbeitsstand und seine ignorierten Freigabe-Artefakte. Ein frischer
Checkout würde diese nicht enthalten. Risiko: parallele Änderungen; deshalb
Dateiabgleich vor und nach jedem gezielten Commit, kein pauschales Zurücksetzen.

Ruling: Ein Git-Sicherungsstand ist keine Release-Freigabe. Bereits vorhandene
Testfehler werden namentlich ausgewiesen, niemals durch erfundene Freigaben
behoben. Risiko: Entwicklungsbranch bleibt gegebenenfalls bewusst nicht grün.

Pre-flight: Übernahme benötigt die bereits freigegebenen Bild-/Quellenhashes;
Druckproben konsumieren den regulär übernommenen Master; Git enthält nur
öffentliche Projektdaten und den freigegebenen Master samt Herkunftsnachweis.
Es ist keine neue Produktionscode-Implementierung vorgesehen.
