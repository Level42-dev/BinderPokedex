# P10 – Generation VII: Flamiau-Korrektur

Stand: 22.09.2026. **Variante C ist vom Nutzer akzeptiert und exakt übernommen.**
Rückmeldung: „passt alles prima! mach damit weiter“.
[Dateigebundene Nutzerentscheidung](2026-09-22-p10-c-user-acceptance.json) ·
[Technische Übernahme und nächste Runde](2026-09-22-p10-adoption-and-next-round.md).

Flamiaus fehlender
schräger Beinabschnitt ist wieder vorhanden. Eine kleine dunkle Rundung der
dahinterliegenden Pfote bleibt stärker sichtbar als in der Quelle; die
Überdeckung ist also noch nicht vollständig identisch. Flamiau fällt zudem
größer aus als in der kleinen Positionsvorgabe. Alle Figuren bleiben innerhalb
ihrer tatsächlichen Schnittkarte. Die genannten Unterschiede sind für genau C
akzeptiert; keine numerische Layout- oder vollständige Release-Freigabe.

Alle drei Versuche wurden vollständig geprüft. C ist der dritte und letzte
automatische Versuch dieser Runde; kein mehrstufiger Ersatzweg. Während der
Versuche blieben alle 42 Master unverändert. Nach der Freigabe wurde nur P10
durch das pixelidentische C ersetzt; die übrigen 41 Master und die vorhandenen
Release-PDFs/-Archive bleiben erhalten.

## C – Gesamtbild und direkte Quellenvergleiche

![P10 C – neues vollständiges Panorama](../../tmp/oneshot-trials/p10-source-detail-20260922-c/review/artwork-300dpi.png)

### Flamiau · r3c2

Der schmale rot-dunkle Beinabschnitt unter dem Kinn ist jetzt sichtbar.
Die kleine verbleibende Rundung unmittelbar bildlinks neben dem langen
Vorderbein ist die offengelegte und inzwischen akzeptierte Quellenabweichung;
keine Behauptung vollständiger Pixelidentität. Gesicht, Ohren, Schwanz und
Zeichnung bleiben quellnah.

| Neuer tatsächlicher Kartenausschnitt C | Unveränderte Originalquelle |
| --- | --- |
| ![Flamiau – Karte C](../../tmp/oneshot-trials/p10-source-detail-20260922-c/review/cards/card_r3_c2.png) | ![Flamiau – Original](../../tmp/poster-workspaces/Pokedex/sections/gen7/sources/cutouts/pokemon_725_litten.png) |

### Bauz · r3c1

Silhouette, Gesicht, zweifarbiger Schnabel, Blattfliege, Flügel und beide Füße
sind quellnah. Kleine Kontur- und Glanzlichtabweichungen; kein sicherer neuer
Anatomiefehler. Die spätere C-Rückmeldung akzeptiert diese neuen Pixel separat.

| Neuer tatsächlicher Kartenausschnitt C | Unveränderte Originalquelle |
| --- | --- |
| ![Bauz – Karte C](../../tmp/oneshot-trials/p10-source-detail-20260922-c/review/cards/card_r3_c1.png) | ![Bauz – Original](../../tmp/poster-workspaces/Pokedex/sections/gen7/sources/cutouts/pokemon_722_rowlet.png) |

### Robball · r3c3

Nase, Auge, Maul mit Zunge, Halskrause und vier Flossen bleiben quellnah.
Das Vordergrundblatt am äußeren rechten Flossenrand ist räumlich plausibel.
Auch hier gilt die C-Nutzerentscheidung ausschließlich für diese neue Fassung.

| Neuer tatsächlicher Kartenausschnitt C | Unveränderte Originalquelle |
| --- | --- |
| ![Robball – Karte C](../../tmp/oneshot-trials/p10-source-detail-20260922-c/review/cards/card_r3_c3.png) | ![Robball – Original](../../tmp/poster-workspaces/Pokedex/sections/gen7/sources/cutouts/pokemon_728_popplio.png) |

### Kurze Entscheidung

- [x] Flamiaus Beinüberdeckung in C trotz der genannten Restabweichung akzeptiert.
- [x] Flamiaus Größe und die neue Gesamtszene mit Bauz und Robball akzeptiert.
- [x] Exakte technische Übernahme und Produktionsvalidierung erfolgt.
- [ ] Vollständige Pokédex-Druckausgabe und Release-Prüfung bleiben separat.

[Deutsche Vorschau](../../tmp/oneshot-trials/p10-source-detail-20260922-c/review/poster-de.png) ·
[Bildgebundener Prüfbericht C](2026-09-22-p10-source-detail-c.json).

## Korrekturziel

Flamiaus rechtes Vorderbein ist in der Originalquelle teilweise sichtbar:
unter dem Kinn, bildlinks hinter dem langen aufgesetzten Vorderbein, als
schmaler schräger dunkler Abschnitt mit roter Zeichnung. In der bisherigen
Panoramafassung fehlt dieser Abschnitt. Die erneute Ansicht bestätigt den
Nutzerhinweis; dort verdeckt kein Vordergrundgras das Bein.

Es sollen keine vollständig sichtbaren zusätzlichen Beine erfunden werden.
Die tatsächlich verdeckten Teile bleiben entsprechend der Originalpose
verdeckt. Bauz und Robball sowie der Alola-Charakter der Szene sollen erhalten
bleiben. Die Zustimmung zum bisherigen Bild wird nicht auf neue Pixel übertragen.

## Ausführung

- Bestehender Projektweg: FLUX.2 Klein 4B, gemeinsamer `joint_scene`-One-shot,
  `spatial_source_detail_joint` v11, vier Referenzbilder, ein Bildlauf.
- Ein gemeinsames Positionsbild und drei separate genaue Originalreferenzen;
  keine nachträglich eingefügten Pokémon, keine Masken-/Compositing-Reparatur.
- Auflösung 1200 × 1664; danach deterministische 300-dpi-Aufbereitung ohne
  zusätzlichen KI-Lauf. Bisheriger Seed 260726058, Szene und Modellprüfsummen
  bleiben erhalten.
- Die neue, quellgebundene Flamiau-Beschreibung nennt ausdrücklich den
  fehlenden Beinabschnitt. Bauz und Robball haben eigene, direkt aus ihren
  tatsächlichen Originalbildern abgeleitete Merkmalsbeschreibungen.
- Die vollständige gespeicherte Render-Konfiguration wurde wiederverwendet.
  Verbindung und alle drei Modellprüfsummen sind frisch geprüft; keine
  Modelle oder Laufzeitumgebungen heruntergeladen.
- Der bestehende Transport wird ausschließlich für P10 aufgerufen. Seine
  bisherige Implementierung und ältere Jobs bleiben unverändert; der neue
  Aufruf und alle Quellen sind in der Eingabeprüfung erfasst.
- 119 bestehende Tests des relevanten Render-/Quellen-/Prüfpfads bestanden;
  zusätzliche Prüfungen bestätigten die P10-Beschränkung, sichere Varianten,
  Pokédex-Datenbindung, erfasste Hilfsdateien und 42 geschützte Bestandsmaster.

## Vorbereitete Referenzen

Alle drei Originale und alle vier tatsächlich verwendeten Referenzbilder
wurden vor dem Start betrachtet. Dateibindungen der Originale:

| Figur | SHA-256 der Originalquelle |
| --- | --- |
| Bauz | `5456dc8d55b3fd305bb7ddd4b1f94f07b51e3691414abaf4d60c7a7745f09c36` |
| Flamiau | `02391ac457888baf123accfc5ce446fc75df4790b3b000865a21c0f21b622600` |
| Robball | `3bfa3104b894f212985122732497b17c78979c6bc9304bd7396e781677f2d7a3` |

[Vollständiger tatsächlich verwendeter Prompt C](../../tmp/oneshot-trials/p10-source-detail-20260922-c/workflows/source_detail_joint_prompt.generated.txt).
Die unveränderte Ausgangskonfiguration liegt als lokale Sicherung in
`tmp/p10-source-detail-20260922-baseline/poster.yaml`.

## Erster Versuch A – verworfen

Der zuvor fehlende Beinabschnitt einschließlich roter Zeichnung ist vorhanden.
Darunter erscheint jedoch eine kleine separate runde Pfote, die in der Quelle
hinter dem langen Vorderbein verborgen bleibt. Der Befund wurde im Rohbild
und tatsächlichen Schnittkartenausschnitt geprüft. Alle neun Karten, die
deutsche Vorschau und das Vollbild wurden angesehen; der technische
Prüflauf bestätigte Bild-/Jobbindungen, Schnittgeometrie und 42 unveränderte
Bestandsmaster. [Unveränderlicher Befund mit Bildprüfsummen](2026-09-22-p10-source-detail-a.json).

B ändert ausschließlich Flamiaus Merkmalsbeschreibung: Nur der schmale schräge
Beinabschnitt bleibt sichtbar, die dahinterliegende Pfote bleibt verdeckt.
Ein direkter A/B-Abgleich bestätigt vier bytegleiche Referenzbilder sowie
denselben Seed, dieselben Modelle, denselben Bildablauf und dieselbe Szene.
Die Beschreibung von Bauz und Robball wurde nicht verändert.

## Zweiter Versuch B – Quellenpunkt noch offen

B verkleinert die zusätzliche Pfotenrundung, beseitigt sie aber nicht.
Rohbild, Master, Vorschau und alle neun Karten wurden erneut betrachtet.
Der vollständige technische Prüfpfad besteht; alle 42 Bestandsmaster bleiben
unverändert. [Bildgebundener B-Befund](2026-09-22-p10-source-detail-b.json).

C ersetzt nur Flamiaus Beinteil-Beschreibung durch die genaue sichtbare
Geometrie: ein kurzer schräger rot-dunkler Streifen unter dem Kinn, der hinter
dem oberen Abschnitt des langen Vorderbeins verschwindet; unterhalb dessen
oberem roten Band soll die seitliche Kontur ohne zusätzlichen Pfotenhöcker
verlaufen. Referenzen, Seed, Modelle, Szene und die beiden anderen
Figurenbeschreibungen sind erneut bytegleich beziehungsweise unverändert
geprüft. Keine vierte automatische Wiederholung oder mehrstufige Reparatur.

## An C tatsächlich geprüft

- Rohbild, vollständiger textfreier Master und deutsche Vorschau angesehen.
- Alle neun tatsächlichen Schnittkarten sowie jedes Figuren-/Quellenpaar angesehen.
- Flamiaus schräger Beinabschnitt einschließlich roter Zeichnung vorhanden;
  verbleibende Pfotenrundung ausdrücklich offengelegt.
- Keine abgeschnittenen Figuren oder zusätzlich erzeugten Pokémon festgestellt.
- Vordergrundüberdeckungen und Schatten im Gesamtbild/Kartenausschnitt geprüft;
  kein sicherer neuer lokaler Tiefenbruch festgestellt.
- Vollständige Rückgabe von Bild, Laufnachweis und Protokoll verifiziert; richtige
  Kartenausschnitte/Druckauflösung und unveränderte 42 Bestandsmaster.

- Der kanonische Prüfpfad besteht; 119 relevante Tests erneut bestanden.

Die ursprüngliche Sichtprüfung ist eine Agentenprüfung; die spätere,
separat dokumentierte Nutzerentscheidung akzeptiert C. Es wurde kein
unabhängiger Zweitprüfer eingesetzt. Die numerischen kleinen
Positionsgrenzen werden nicht als erfüllt ausgewiesen, und technische
Prüferfolge ersetzen weder die eigene Nutzerentscheidung noch die spätere
vollständige Pokédex-Druck-/Release-Prüfung.
