# P37: Identity-Lock-Kandidat A angenommen und übernommen

Stand: 27.09.2026. Kandidat `p37-il-20260927-a` ist der ausdrücklich visuell freigegebene Fallback für `ME03`. Die technische Promotion und die lokale deutsche PDF-Aktivierung folgten erst nach dieser Freigabe und erneuter Prüfung.

## Reproduzierbare Eingaben und Rückgaben

- Unveränderlicher Szenenjob SHA-256 `00b76b9cf727c031340376ced80caba0f89347968af8de7b2d2870627b5dc0f6`; 300-dpi-Upscale-Job SHA-256 `32840ce7155c524247b15dd9f5140182bf11b09d07afe5c2b9808c9f10202d9c`.
- Beide Jobs wurden vor GPU-Ausführung hashvalidiert. `run.json`, `comfyui.log` und jeweils genau ein Ausgabebild sind vollständig zurückgeholt; Run-Hashes `d0d473967445ef00a632ee530b2be28d51f6661221bd898796fafdfdd22fc72d` und `98a0dec789d57f21b673b3eae15d01a8c6dfe6248f22a5eae95e9eb7f47289d1`. Gerät MPS und Ausgabedateihashes sind bestätigt.
- Rohbild SHA-256 `20e88678fdbd21b074975e76f2c2352b8877a65f90001e5e8d13291862ffb523`: 54.082 vollständig opake Quellpixel geprüft, 0 verändert. Druckmaster 2368 × 3268 px SHA-256 `fc1df7acd8359153d53eabbaf23c22a189dbc8d694e58ed5cd8a7c3b683e7b76`; deutsche Vorschau SHA-256 `e15af85aec4c7ec991ffec414d29585161ec5580417153ac2e92cd96dfc4663f`. Alle neun physischen 750 × 1050-px-Karten liegen im ignorierten Kandidatenverzeichnis und wurden als Karte sowie im Gesamtbogen geprüft.

## Bildvergleich und offener Eindruck

Serpifeu (r3c1), Bauz (r3c2) und Mega-Zygarde (r3c3) entsprechen ihren exakten Official-Artwork-Quellen. Anders als in den abgelehnten B/C/D-One-shots ist Zygardes linkes violettes Emblem vollständig innerhalb von r3c3; auch Hände, rechter Kanonenrand und untere Ausläufer werden nicht abgeschnitten. Das deutsche Setlogo ist vorhanden. Die Landschaft bleibt über alle neun Karten kontinuierlich, ohne die bei P16 sichtbare gerade Unterkanten-Naht.

Der Bildstil ist allerdings flächig und ruhig; bei Serpifeu und Bauz sind Kontaktschatten nur schwach, Mega-Zygarde schwebt gemäß seiner Quellpose ohne deutliche Projektion. Diese bekannte Einschränkung wurde dem Nutzer mit Gesamtbild und allen drei beschrifteten Einleger-Quellbild-Paaren ausdrücklich zur visuellen Entscheidung vorgelegt. Der Nutzer antwortete mit "Ja, P37-A freigeben" und bestätigte anschließend, dass die PDF nach Freigabe der Ausschnitte auszutauschen bzw. zu aktualisieren ist. Die Freigabe betrifft genau diesen Master und diese bekannte Einschränkung, nicht andere Identitätslock-Kandidaten.

## Promotion und PDF

Vor der Promotion wurde die 848 × 1168-px-Rohszene gegen die 848 × 1170-px-Upscale-Eingabe geprüft: Letztere ist exakt die von `normalize_upscale_input` vorgesehene Lanczos-Anpassung auf das Druckseitenverhältnis, keine unbemerkte Änderung am freigegebenen Master. Der echte Upscale-Lauf, beide Workflow-/Run-Dateien und Logs wurden erneut abgeglichen. Der quellpixelgebundene Run-Nachweis hat SHA-256 `49e548bdee14374d9ad22de4a545c1cdf3c0f79c4088416f8e229453c24b4f89` und bestätigt 54.082 geschützte Pixel bei 0 Änderungen.

Die produktive textfreie Datei und die deutsche Vorschau sind **bytegleich** zum freigegebenen Kandidaten (`fc1df7acd8359153d53eabbaf23c22a189dbc8d694e58ed5cd8a7c3b683e7b76` bzw. `e15af85aec4c7ec991ffec414d29585161ec5580417153ac2e92cd96dfc4663f`). Alle neun physischen Einleger sind pixelgleich zu den geprüften Kandidatenkarten. Die produktive Provenienz hat SHA-256 `5f21c3f66472c46eea2aa743ecb7a0cab414744788cdeebee17ff47886087711`; `validate_promoted_poster.py --scope ME03` bestand. `pdf.enabled` wurde erst danach gesetzt.

Die getrennt gebauten deutschen PDF-Kandidaten mit Einleger- und Vollseitenpanorama haben je 16 A4-Seiten und 124 nummerierte Karten. Seite 1 wurde in beiden Modi einzeln geprüft, alle 16 Seiten als Raster-Kontaktbogen. Neun 750 × 1050-px-Einleger liegen mit 300 dpi im Einlegermodus; die Vollseitenvariante enthält den 2368 × 3268-px-Master bei 300 dpi. Seiten 2–16 sind zwischen den Modi pixelgleich. Die reguläre lokale PDF wurde erst danach neu gebaut; ihr 72-dpi-Raster ist auf jeder Seite pixelgleich zur Prüffassung. Neuer PDF-SHA-256: `e0ecd710a72cc8c340035fe7264c011af2c02f26a55b0a0aa740bcdd4201bfbc`; alter SHA-256: `7adc6723a3b8862c515208fbc8cade0559f2cd19e9dc93c28cba525b3d10ad95`. Die alte Fassung ist nur im ignorierten lokalen Prüfverzeichnis gesichert. Diese lokale PDF ist noch kein gesamtes v10-Release.
