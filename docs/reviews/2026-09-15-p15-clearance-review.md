# P15 – Rayquaza-Abstand: Versuch C zurückgehalten

Stand: 15.09.2026. **Die gewünschte Korrektur ist noch nicht erreicht; C wird nicht übernommen.**

Dein Okay ist festgehalten: P40-B bleibt für Figuren und Bildaufteilung akzeptiert.
Bei P15-B passen die Figuren und die übrige Szene; nur Rayquaza braucht mehr Platz.

## Rayquaza: bisher, neuer Versuch und Original

| B – bisheriger Ausschnitt | C – zurückgehaltener Versuch | Exakte Originalquelle |
| --- | --- | --- |
| ![Rayquaza B](../../tmp/oneshot-trials/p15-source-detail-20260915-b/review/cards/card_r3_c2.png) | ![Rayquaza C – Abstand weiterhin zu knapp](../../tmp/oneshot-trials/p15-clearance-20260915-c/review/cards/card_r3_c2.png) | ![Mega-Rayquaza Originalquelle](../../tmp/poster-workspaces/ExGen2/sections/mega/sources/cutouts/pokemon_384_artwork_10079_mega_rayquaza.png) |

C bringt rechts etwas mehr Platz, links jedoch praktisch keinen. Markante grünblaue
Körperpixel beginnen bei beiden Bildern bereits 10 Pixel vom linken Rand entfernt
(unter 1 mm bei 300 dpi). Die angestrebte freie Zone lag bei rund 60 Pixeln, also
5 mm. Kontur und Leuchteffekte reichen noch weiter nach außen.

Das ist eine Prüfung ausgewählter Körperfarben, **keine vollständige automatische
Silhouettenmessung**. Bereits diese innenliegenden Körperpixel widerlegen aber
den verlangten freien Rand. Der vollständige Kartenausschnitt bestätigt das sichtbar.

## Übrige Figuren erneut abgeglichen

Die Szene wurde als Ganzes neu erzeugt; deshalb wurden auch Mewtu X und Latios
erneut mit ihren Originalen verglichen. Es wurde kein neuer eindeutiger
Identitätsfehler festgestellt. Ihre bereits erteilte B-Freigabe wird dennoch
nicht auf die veränderten C-Pixel übertragen.

### Mega-Mewtu X

| Tatsächliche Karte C | Exakte Originalquelle |
| --- | --- |
| ![Mega-Mewtu X C](../../tmp/oneshot-trials/p15-clearance-20260915-c/review/cards/card_r3_c1.png) | ![Mega-Mewtu X Originalquelle](../../tmp/poster-workspaces/ExGen2/sections/mega/sources/cutouts/pokemon_150_artwork_10043_mega_mewtwo_x.png) |

### Mega-Latios

| Tatsächliche Karte C | Exakte Originalquelle |
| --- | --- |
| ![Mega-Latios C](../../tmp/oneshot-trials/p15-clearance-20260915-c/review/cards/card_r3_c3.png) | ![Mega-Latios Originalquelle](../../tmp/poster-workspaces/ExGen2/sections/mega/sources/cutouts/pokemon_381_artwork_10063_mega_latios.png) |

## Prüfung und nächster Schritt

Es wurde nur der zusätzliche Abstandshinweis für Rayquaza geändert. Quellen,
alle vier Referenzbilder, Seed, Modelle und Zuschnitt blieben identisch.
Landschaft und Figuren entstanden erneut gemeinsam in einem einzigen Lauf
auf dem bereits konfigurierten ComfyUI-Worker. Es gab kein nachträgliches
Einkleben, Übermalen oder Verschieben der Figur.

Rohbild, gesamter Master, deutsche Vorschau und alle neun tatsächlichen Karten
wurden betrachtet. Auftragsnachweise, Ausgabebild, Hashes, 300 dpi und
pixelgenaue Zuschnitte wurden erfolgreich geprüft. Die 60 fokussierten Tests
bestehen. Technische Reproduzierbarkeit bedeutet hier ausdrücklich **keinen
bestandenen Abstandscheck**.

Der wirkungslose zusätzliche Texthinweis wurde nach Sicherung von C und seines
exakten Manifests wieder entfernt. Der aktive P15-Quellstand entspricht B.
Alle bisherigen Bilder, die 42 installierten Master, PDFs und ZIPs bleiben
unverändert. Keine Promotion und kein weiterer Lauf.

**Vorgeschlagener nächster Ansatz:** Eine gezielte Größenoption für die
Positionsreferenz, sodass nur Rayquaza dort etwa 15–20 % kleiner erscheint.
Die unveränderte Originalquelle bleibt zusätzlich als Detailreferenz erhalten;
die gemeinsame One-Shot-Erzeugung bleibt bestehen. Die Landschaft wird nicht
nachträglich unter eine ausgeschnittene Figur geklebt. Auch danach werden
Gesamtbild und alle drei Figuren erneut überprüft.

Die Rückfrage dazu wurde gestellt. Gemäß dem Prüfhalt aus
Systematic Debugging
folgt kein weiterer reiner Prompt-Versuch ohne abgestimmte Änderung des Ansatzes.

[Vollständiger C-Master](../../tmp/oneshot-trials/p15-clearance-20260915-c/review/artwork-300dpi.png) · [Deutsche C-Vorschau](../../tmp/oneshot-trials/p15-clearance-20260915-c/review/poster-de.png) · [Hashgebundenes C-Prüfprotokoll](2026-09-15-p15-clearance-c.json)

[Tatsächlich verwendeter vollständiger C-Prompt](../../tmp/oneshot-trials/p15-clearance-20260915-c/workflows/source_detail_joint_prompt.generated.txt)
