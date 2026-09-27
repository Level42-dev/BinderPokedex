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

- [x] Bestehende Commits auf `codex/v10-refresh` mit dem Remote abgleichen.
- [x] Lokale Code-, Konfigurations- und Review-Arbeit auf sichere Inhalte prüfen,
  den Teststand erfassen und als Entwicklungsstand committen und pushen.
- [x] P04-B-Freigabe und sämtliche gebundenen Dateien erneut verifizieren;
  bisherigen P04-Bestand rückholbar sichern.
- [x] Genau P04-B regulär übernehmen; Master, Vorschau und alle neun Karten
  pixelgenau abgleichen und die übrigen 41 Master auf Unverändertheit prüfen.
- [x] Zwei deutsche Panorama-Druckproben mit dem Produktionsrenderer erstellen;
  alle vier PDF-Seiten sowie Bildpixel, A4-Geometrie und Platzierungen prüfen.
- [x] Ergebnis und offene Grenzen dokumentieren, gezielt committen und pushen;
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

Ruling: Die vier bereits ganz oder teilweise akzeptierten, aber noch nicht
produktiven Master zusätzlich in `assets/reviewed-candidates` archivieren.
Der aktuelle Sicherungsauftrag umfasst diese sonst nur lokal vorhandenen
Bildresultate. Das Archiv liegt außerhalb des Produktionsroutings und erhält
die genaue Teil-/Gesamtfreigabe. Risiko einer Verwechslung wird durch eigene
Archiv-Provenienz und ausdrücklich falsche Promotion-/Release-Flags begrenzt.

## Ergebnis der P04-Übernahme

Der Master ist bytegleich zu B; deutsche Vorschau und alle neun Schnittkarten
sind pixelgleich. Die übrigen 41 installierten Master sind unverändert.
Produktionsvalidierung, exakte eingebettete PDF-Bildpixel, physische Positionen
und alle vier gerasterten PDF-Seiten sind geprüft. Die beiden Ausgaben enthalten
jeweils eine Panorama-Seite und eine Herkunfts-/Hinweisseite. Bei 100 % drucken.

- [Deutsche Schnittkarten](../../output/pdf/v10-p04-b-20260922/v10_P04_B_Druckprobe_DE_Schnittkarten.pdf)
- [Deutsches Gesamtpanorama](../../output/pdf/v10-p04-b-20260922/v10_P04_B_Druckprobe_DE_Gesamtpanorama.pdf)
- [Hashgebundener Produktions- und PDF-Prüfnachweis](2026-09-22-p04-b-production.json)

Der volle Testlauf hat vor und nach der Übernahme dieselben drei bestehenden
Fehler bei widerrufenen Alt-Freigaben: 828 bestanden, 3 fehlgeschlagen,
1 übersprungen. Einzelheiten stehen im [Test-/Sicherungsbericht](2026-09-22-git-checkpoint-verification.md).
Der Entwicklungs-Checkpoint `82b23a9` ist gepusht. P04 und die vier
Review-Archiv-Master sind im getrennten Commit `6b1513a` ebenfalls gepusht.
Die unabhängige Remote-Abfrage bestätigte exakt
`6b1513a7acc11df3d22fec28e5e229d26da64674` auf `codex/v10-refresh`.
Alle fünf gesicherten Master stimmen mit ihren Git-Blobs überein.
Der nachfolgende Dokumentationsabschluss verändert keine Bild- oder Code-Datei.
