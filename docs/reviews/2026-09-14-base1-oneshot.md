# Base Set: One-Shot-Vergleich mit Schwerpunkt Mewtu

## Ergebnis

**B ist vom Nutzer visuell freigegeben; die technische Übernahme in die
Produktion steht noch aus.** Mewtu unten links ist deutlich näher an der Originalquelle
als im installierten Panorama: kantiges Auge mit dunklem Pupillendetail,
schmale Kopfform, drei runde Fingerkuppen und ein durchgehender Schwanzbogen.
Kleine Zeichenabweichungen bleiben. B hat eine eigene Nutzerfreigabe erhalten;
ExGen3 Cs Freigabe wurde nicht auf dieses andere Motiv übertragen.

Die Originale von Mewtu, Bisasam und Glumanda, alle vier Eingabereferenzen,
das Rohbild, der vollständige Druckmaster, die deutsche Vorschau und alle neun
physischen Karten von B wurden tatsächlich angesehen. Die Karten sind jeweils
750 × 1050 Pixel groß und entsprechen exakt ihren Ausschnittrechtecken.

- [Textfreies Panorama B](../../tmp/oneshot-trials/base1-source-detail-20260914-b/review/artwork-300dpi.png)
- [Mewtu-Karte B](../../tmp/oneshot-trials/base1-source-detail-20260914-b/review/cards/card_r3_c1.png)
- [Mewtu-Originalquelle](../../tmp/poster-workspaces/Base1/sources/cutouts/pokemon_150_mewtwo.png)
- [Deutsche Vorschau mit bestehendem Overlay](../../tmp/oneshot-trials/base1-source-detail-20260914-b/review/poster-de.png)
- [Hashgebundener Prüfbericht](2026-09-14-base1-oneshot.json)

## Kontrollierter Vergleich

Beide Versuche verwenden Klein 4B BF16, vier Schritte, den vorhandenen
Base1-Seed `260726503` und 1200 × 1664 Generierungspixel. Wie bei ExGen3 C
werden eine gemeinsame 608 × 832-Positionsvorlage und drei unvergrößerte
512 × 512-Detailreferenzen gemeinsam übergeben. Es gibt genau einen leeren
Ziel-Latent, einen Sampler und einen Decode. Die Druckaufbereitung auf
2368 × 3268 Pixel erfolgt mit Lanczos; es werden keine Figuren nachträglich
eingesetzt oder repariert.

| Versuch | Änderung | Ergebnis |
| --- | --- | --- |
| A | ExGen3-Cs Vorgehen auf die Base-Set-Quellen und die konfigurierte Wiesenlandschaft übertragen | Mewtu quellnäher, aber ein zusätzliches, verändertes Bisasam in der Bildmitte; verworfen |
| B | Nur eine vorangestellte Anweisung mit je genau einem Pokémon und figurenfreier oberer Landschaft ergänzen | Nur die drei vorgesehenen Figuren; alle neun Karten vom Agenten geprüft; anschließend vom Nutzer visuell akzeptiert |

Bei B sind sämtliche übrigen Graphknoten, Eingabebilder, Modellprüfsummen,
Seed und Raster unverändert gegenüber A. Der Zusatz wirkt in diesem
kontrollierten Vergleich; daraus folgt keine Garantie für andere Seeds oder
Sets. Beide vollständigen Jobs einschließlich `run.json`, `comfyui.log` und
aller Ausgaben wurden zurückgeholt. Die jeweiligen Renderlaufzeiten betrugen
etwa 68 Sekunden, ohne lokale Vorbereitung und Transfer.

Der vollständige Prompt besteht aus
[Layout-/Anzahlpriorität](../../tmp/oneshot-trials/base1-source-detail-20260914-b/layout-priority-prefix.txt)
und anschließend [Quellmerkmalen und Szene](../../tmp/oneshot-trials/base1-source-detail-20260914-b/source-detail-prompt.txt).

## Grenzen der Sichtprüfung

- Mewtu: feine Augen-, Schnauzen- und Zehenkonturen sind nicht identisch zur
  Quelle. Gräser überdecken kleine Fuß- und Schwanzränder plausibel; verdeckte
  Zehendetails lassen sich nicht unabhängig bestätigen.
- Bisasam: Knospenfalten, einige kleine Mund-/Krallenkonturen und Schattierung
  weichen leicht ab. Die zusätzliche Figur aus A ist in B nicht vorhanden.
- Glumanda: winzige Finger-, Mund- und Krallenkonturen sind vereinfacht;
  untere Fußränder sind teilweise durch Gras überdeckt.
- Das deutsche Informationsfeld passt in seine Karte. Das unverändert
  konfigurierte Titelbild trägt weiterhin den englischen Zusatz
  „TRADING CARD GAME“. Das ist keine Freigabe der deutschen Logo-/Releasefassung.

## Nutzerfreigabe

Am 14. September 2026 hat der Nutzer auf das gezeigte textfreie Panorama B
geantwortet:

> das sieht super aus!

Dies ist als visuelle Freigabe des unten hashgebundenen Druckmasters
festgehalten. Die zuvor benannten kleinen Konturabweichungen bleiben im
Agentenbericht dokumentiert. Eine zusätzliche vollständige Einzelkartenprüfung
durch den Nutzer oder eine Freigabe des bestehenden englischen Logozusatzes
wird daraus nicht abgeleitet. Andere Motive benötigen weiterhin ihre eigene
Quell- und Sichtprüfung.

## Stand nach dem Test und der Nutzerfreigabe

Rohbild B: `f655c8a01f8b8f2d4a26b978a29db89ced62e01a5b3dc61d3d7a48eefd16134a`.
Druckmaster B: `d06f69eb6e010b2670987a2209d3aec50848ac694aaefec64dc70d342ce0d9b4`.

Beide Jobs und je 15 Bild-/Quellprüfsummen wurden verifiziert. Alle 18
technisch erzeugten Kartenausschnitte sind geometrisch geprüft; die visuelle
Einzelkartenprüfung umfasst A nur bei Mewtu, B bei allen neun Karten.
Die fokussierten Renderjob-Tests melden `7 passed`; kein vollständiger
Release-Check wurde durchgeführt.

Das installierte Base1-Bild, seine bereits bestehenden Prüfvermerke, die
Generierungsmanifest-Datei, Kartendaten, PDFs und ZIPs bleiben unverändert.
Keine weiteren Sets, kein dritter Versuch und kein mehrstufiger Fallback wurden
gestartet. Der Prompt ist weiterhin ein isoliertes Experiment; eine Übernahme
in den gemeinsamen Generator und eine Produktionspromotion stehen aus.
