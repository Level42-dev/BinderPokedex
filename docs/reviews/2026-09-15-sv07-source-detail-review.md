# P01 – Stellarkrone: neuer One-Shot B

Stand: 15.09.2026. **Zwischenprüfung für Figurentreue und Bildaufteilung – noch keine fertige Druckfreigabe.**

**Nachfolgende Nutzerentscheidung:** „alles perfekt. der neue Flow scheint sehr gut zu greifen!“ Damit sind die gezeigten Figuren, die Szene und das Größenverhältnis von B visuell akzeptiert, einschließlich der offengelegten größeren Darstellung von Hopplo/Schiggy. Die Zustimmung ist an genau diesen Master und die gezeigten Karten gebunden; die Bild-/Quellenhashes wurden erneut geprüft. Die zuvor ausdrücklich vorbehaltene Schattenkorrektur bleibt vor technischer Übernahme offen. Die nachfolgenden ursprünglichen Prüfbefunde bleiben als Verlauf erhalten; sie werden nicht zu bestandenen technischen Prüfungen umetikettiert.

Die Szene und alle drei Pokémon wurden gemeinsam in einem einzigen 2-MP-Lauf erzeugt. Es wurden keine Pokémon nachträglich eingeklebt oder zurückkopiert. Danach erfolgten nur die deterministische Druckskalierung, das deutsche Logo, die Infokarte und der Zuschnitt.

Der erste Versuch A wurde wegen einer zusätzlichen Figur und angeschnittener Pokémon verworfen. B ändert ausschließlich die beiden führenden Anzahl-/Positionsabsätze; Quellen, Modelle, Seed und Landschaft blieben identisch.

## Gesamtbild B

![P01 – neues textfreies Panorama B](../../tmp/oneshot-trials/sv07-source-detail-20260915-b/review/artwork-300dpi.png)

[Deutsche Gesamtvorschau mit Logo und Infokarte](../../tmp/oneshot-trials/sv07-source-detail-20260915-b/review/poster-de.png)

## Echte Kartenausschnitte neben den Originalen

Links steht jeweils die unveränderte physische 750 × 1050-Pixel-Karte aus B. Rechts steht die exakte, tatsächlich eingesetzte Originalquelle. Die Gegenüberstellung passt nur die Anzeigegröße an; sie repariert oder übermalt keine Details.

### Hopplo · r3c3

Zwei Ohren, beide getrennten Augen, einzelner oberer Zahn und zwei getrennte Halsflecken sind jetzt deutlich quellnäher. Die Trittpose und die Sohlenzeichnung sind erkennbar erhalten. Hopplo ist allerdings größer und höher als in der Positionsvorlage: rund 25 % statt 17,8 % der gesamten Bildhöhe. Die Ohren bleiben mit ungefähr 45 Pixeln Abstand innerhalb der Karte – kein Anschnitt, aber eine klare Größenabweichung. Der schmale nach links laufende Bodenschatten passt nicht zur Lichtquelle links oben.

| Neuer Kartenausschnitt B | Tatsächlich verwendete Quelle |
| --- | --- |
| ![Hopplo – neue Karte B](../../tmp/oneshot-trials/sv07-source-detail-20260915-b/review/cards/card_r3_c3.png) | ![Hopplo – Originalquelle](../../tmp/poster-workspaces/SV07/sources/cutouts/pokemon_813_scorbunny.png) |

### Bisasam · r3c1

Augen, eckige Flecken, Knospenkontur und sichtbare Pfoten/Krallen wurden direkt verglichen. Kein klarer neuer Identitätsfehler wurde festgestellt; kleine Linien- und Schattierungsunterschiede bleiben sichtbar.

| Neuer Kartenausschnitt B | Tatsächlich verwendete Quelle |
| --- | --- |
| ![Bisasam – neue Karte B](../../tmp/oneshot-trials/sv07-source-detail-20260915-b/review/cards/card_r3_c1.png) | ![Bisasam – Originalquelle](../../tmp/poster-workspaces/SV07/sources/cutouts/pokemon_001_bulbasaur.png) |

### Schiggy · r3c2

Augen, Panzersegmente, Hand-/Fußkonturen und eingerollter Schwanz sind quellnah. Auch Schiggy ist etwas größer/höher als geplant. Der Schwanz bleibt vollständig in der Karte, mit ungefähr 28 Pixeln Abstand zum rechten Rand.

| Neuer Kartenausschnitt B | Tatsächlich verwendete Quelle |
| --- | --- |
| ![Schiggy – neue Karte B](../../tmp/oneshot-trials/sv07-source-detail-20260915-b/review/cards/card_r3_c2.png) | ![Schiggy – Originalquelle](../../tmp/poster-workspaces/SV07/sources/cutouts/pokemon_007_squirtle.png) |

## Kleine Review-Checkliste

- [x] **Figuren:** Hopplo, Bisasam und Schiggy im direkten Quellenvergleich akzeptiert.
- [x] **Bildaufteilung:** Die gezeigte größere Darstellung von Hopplo und Schiggy akzeptiert; kein allgemeiner Größenfreibrief für andere Bilder.
- [x] **Szene:** Die gezeigte Landschaft und Einbindung visuell akzeptiert; der ausdrücklich reservierte Schattenpunkt bleibt separat offen.

**Noch keine Gesamtfreigabe erbeten:** Hopplos schmalen Bodenschatten würde ich vor einer Übernahme korrigieren und erneut zeigen. Wenn die Größen geändert werden sollen, ist zuerst die Bildaufteilung zu lösen; eine lokale Schattenreparatur vorher würde unnötig einen Zwischenstand bearbeiten. Die verbindlichen Positionsgrenzen werden nicht stillschweigend als bestanden markiert.

## Prüfstand und nächste Motive

Hauptprüfung und unabhängige Gegenprüfung haben Rohbild, vollständigen Master, deutsche Vorschau, alle neun echten Karten und alle drei Originalquellen tatsächlich betrachtet. Alle Figuren liegen innerhalb ihrer Karten; das ist von der noch nicht eingehaltenen kleineren Positionsvorlage zu unterscheiden. Ein eindeutig falscher Vegetations-Tiefensprung wurde bei B nicht belegt – es werden daher nicht vorsorglich zusätzliche Halme erfunden.

Die Bild-/Quellenhashes, ungefähren Größenbefunde und offenen Punkte stehen im [B-Prüfprotokoll](2026-09-15-sv07-source-detail-b.json). Die Größenwerte sind visuelle Schätzungen, keine automatische Segmentierung.

Der neue Renderer-Vertrag und die Quellenbindung sind implementiert und unabhängig geprüft. 27 neue fokussierte Tests bestehen; der breitere Lauf hat 356 bestandene Tests und drei bereits vorhandene Fehler wegen widerrufener/veralteter Bildfreigaben. Das ist keine vollständige Release-Freigabe.

**Danach fest eingeplant:** P15 Mega-Latios und P40 Miraidon. Ihre Originalquellen wurden bereits geprüft; neue Bilder dafür starten erst nach diesem P01-Checkpoint. Alle 42 installierten Master, bisherigen dateigebundenen Bildfreigaben, PDFs und Archive bleiben unverändert. Keine Promotion, kein Commit und kein Push.

Der P01-Checkpoint ist mit der oben dokumentierten Nutzerantwort erfüllt. Die beiden nächsten Transferproben werden mit ihren eigenen Quellen und neuen, getrennten Bildfreigaben fortgesetzt.

Die früher akzeptierten ExGen3-Mega-C-/Basis-Set-B-Bilder und die Dschungel-Pikachu-E-Teilfreigabe werden nicht auf diesen neuen Kandidaten übertragen.
