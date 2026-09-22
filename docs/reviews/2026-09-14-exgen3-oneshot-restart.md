# ExGen3: One-Shot bleibt vorrangig

## Nutzerentscheidung vom 14. September 2026

Der echte One-Shot bleibt der bevorzugte Weg. Der mehrstufige
Identity-Lock-/Schattenansatz bleibt ausschließlich als Reserve erhalten und
wird nicht nach einzelnen Fehlschlägen automatisch weiterverfolgt. Die zuvor
diskutierte automatische Tiefenanalyse für diesen Ersatzweg wird vorerst nicht
implementiert. Aus begrenzten erfolglosen Versuchen folgt kein Nachweis, dass
One-Shot grundsätzlich unlösbar ist.

Die Originalfiguren sind die Referenz für Anatomie, Gesicht, Form, Proportionen,
Farben und Zeichnung. Eine räumlich plausible Überdeckung durch vorhandene,
szenenpassende Vordergrundelemente ist keine Veränderung dieses Aussehens und
ausdrücklich erwünscht. Fehlende Merkmale ohne erkennbare Überdeckung bleiben
ein Fehler; Landschaft darf keine Ausrede für falsch gezeichnete Anatomie sein.

Es wird zunächst nur `ExGen3/sections/mega` untersucht. Kein weiterer
Setlauf, keine Promotion und keine Änderung der PDF-/Release-Artefakte vor
einem überzeugenden Vergleichsbild und der anschließenden Nutzerprüfung.

## Begrenzter erster Versuch

Die beiden September-One-Shots verloren definierende Details. Der gespeicherte
Spatial-/Identity-Versuch verwendet tatsächlich eine gemeinsame Positionsvorlage
und drei separate 512-Pixel-Detailreferenzen; die Originalmerkmale sind dort
vorhanden. Die Anweisung ist allerdings lang und verbietet gleichzeitig jede
Vordergrundüberdeckung.

Hypothese: Eine kürzere, konkret an diesen drei Originalbildern orientierte
Anweisung kann ihre identitätsrelevanten Merkmale deutlicher gewichten und die
widersprechende Überdeckungsvermeidung beseitigen. Das ist eine zu prüfende
Hypothese, kein bereits nachgewiesener Lösungsweg.

Der erste Versuch übernimmt deshalb die vier Bildreferenzen, den Seed
`260751036`, Klein 4B BF16, vier Schritte und das 848 × 1168-Pixel-Ziel des
vorherigen Spatial-/Identity-Versuchs unverändert. Nur der positive Bildprompt
wird ersetzt. Der vollständige neue Prompt liegt im ignorierten Versuch unter
`tmp/oneshot-exgen3-20260914/source-detail-prompt.txt` und wird mit seinem Hash
in das unveränderliche Renderpaket übernommen.

Prüfgrenzen: genau ein leerer Ziel-Latent, ein Sampler, ein Decode; keine
Figurenkomposition, Maskenreparatur oder Modellvergrößerung nach der Generierung.
Die Druckaufbereitung erfolgt ausschließlich deterministisch. Originalquellen,
Rohbild, vollständiger Druckmaster und alle neun Kartenfelder werden verglichen.
Ein technischer Erfolg des Workers ist keine visuelle Freigabe.

## Erstes Ergebnis und kontrollierter Layoutvergleich

Versuch A ist vollständig samt `run.json`, `comfyui.log` und Rohbild
zurückgeholt; Eingaben, Modellzuordnung und Ausgabedatei sind hash-geprüft.
Das Rohbild hat SHA-256
`71cc2c6df4accddde135c21b97f77c02835c7e9eca81a30c86a87001f1cbc153`.
Beim tatsächlich betrachteten Gesamtbild ist Lucarios zentraler Bruststachel
vorhanden und die drei Figuren sind näher an den Detailvorlagen. Sie sind aber
massiv vergrößert und liegen weit oberhalb ihrer erlaubten Kartenpositionen.
Der Kandidat ist deshalb wegen Kartencontainment verworfen, unabhängig von
seiner verbesserten Detailtreue. Keine vollständige anatomische Freigabe wird
aus dieser ersten Gesamtbildsicht abgeleitet.

Der nächste kontrollierte Vergleich B behält alle Referenzen, den bisherigen
Prompt, Seed, Modell und Raster. Er ergänzt lediglich einen vorangestellten
Absatz, der IMAGE 1 als verbindliche Größen-/Positionsvorlage priorisiert:
74 Prozent Landschaft oberhalb der Figuren, Figuren nur im unteren Viertel,
Detailansichten ausdrücklich ohne Einfluss auf ihre Größe im Endbild. Dies
prüft die aus Versuch A beobachtete Konkurrenz zwischen Detailreferenzen und
Bildaufteilung; keine nachträgliche Skalierung oder Einsetzung der Figuren.

Versuch B ist zurückgeholt. Rohbild-SHA-256:
`83f183ae577f8cec754d800e58860f5b20bbaf5c55fa92ac99d330db74fe0bd1`.
Das Gesamtbild, die deutsche Vorschau und die drei unteren Kartenfelder wurden
betrachtet. Die Figuren passen wieder vollständig in ihre zugewiesenen Karten.
Lucarios drei Brust-/Schultermerkmale und weitere definierende Körpermerkmale
sind vorhanden. Kleine Details sind jedoch noch vereinfacht, insbesondere
Diancies Gesicht und Kopfgemmenfacetten. Eine bloße Erkennbarkeit ist noch
keine uneingeschränkte Freigabe für die gewünschte Quelltreue.

Vergleich C verändert ausschließlich die Generierungsauflösung von 1 auf 2 MP
(leerer Ziel-Latent und zugehörige Scheduler-Dimensionen). Prompt, Referenzdateien,
Seed, Modell und vier Schritte bleiben identisch. Damit wird die noch offene
Frage geprüft, ob die kleinen Figuren bei mehr tatsächlichen Bildpixeln Details
besser bewahren. Die vorher schon getestete Vergrößerung von Eingabereferenzen
wird hier nicht wiederholt. Nach C wird dieser begrenzte Dreiervergleich
ausgewertet, nicht automatisch durch weitere Seeds oder den Ersatzweg ergänzt.

## Ausgewähltes Vergleichsbild C

C ist vollständig zurückgeholt und wurde gegen alle drei Originale, das
Rohbild, den textfreien Druckmaster, die deutsche Vorschau und alle neun
physischen Kartenfelder geprüft. Das Rohbild hat 1200 × 1664 Pixel und SHA-256
`a1f96425dc1b7beb7f7cb3d5c35c62cb6e9dd708a2d8187cca2f7b2cb9cc813c`.
Der deterministisch vergrößerte Druckmaster hat 2368 × 3268 Pixel und SHA-256
`eb61f272fd22bd400b2c2555cb2a490fad47c85b3947087a88b96b2e9dce3ebd`.
Alle neun Ausschnitte entsprechen ihren tatsächlichen 750 × 1050-Pixel-
Rechtecken. Die drei echten Renderlaufzeiten lagen bei etwa 45, 42 und 66
Sekunden; Vorbereitung/Transfer sind darin nicht enthalten.

**C ist vom Nutzer visuell freigegeben; die technische Übernahme in die
Produktion steht noch aus.** Die wesentlichen Merkmale der drei Originalformen
sind vorhanden, und alle Figuren passen in ihre Karten. Bei Lucario sind
insbesondere die drei hellen Brust-/Schultermerkmale einschließlich des
zentralen Kegels sichtbar. Gräser/Blätter überdecken kleine Randbereiche an
seinen Füßen und an Latias' unterer Spitze. Das ist die gewünschte
szenenbezogene Überdeckung, keine nachträgliche Figurenkomposition.

Feine Linien und Konturen sind weiterhin leicht interpretiert. Besonders
Diancies Kristallfacetten und einzelne Rundungen unterscheiden sich von der
Vorlage. Der Nutzer hat dieses Maß an Abweichung für das gezeigte Bild
akzeptiert; die konkrete Freigabe ist unten getrennt von der Agentenprüfung
festgehalten.

- [Deutsche Gesamtvorschau](../../tmp/oneshot-trials/exgen3-source-detail-20260914-c/review/poster-de.png)
- [Textfreies Artwork](../../tmp/oneshot-trials/exgen3-source-detail-20260914-c/review/artwork-300dpi.png)
- [Latias-Karte](../../tmp/oneshot-trials/exgen3-source-detail-20260914-c/review/cards/card_r3_c1.png)
- [Diancie-Karte](../../tmp/oneshot-trials/exgen3-source-detail-20260914-c/review/cards/card_r3_c2.png)
- [Lucario-Karte](../../tmp/oneshot-trials/exgen3-source-detail-20260914-c/review/cards/card_r3_c3.png)
- [Hashgebundener Prüfbericht](2026-09-14-exgen3-oneshot-c.json)
- Prompt, unverändert zwischen B und C: [Layoutpriorität](../../tmp/oneshot-exgen3-20260914/layout-priority-prefix.txt), danach [Quellmerkmale und Szene](../../tmp/oneshot-exgen3-20260914/source-detail-prompt.txt).

Der geerbte Rohdateiname in C enthält noch `1mp`, weil die unveränderliche
Graph-Kopie nur Ziel-/Scheduler-Abmessungen geändert hat. Tatsächliches Raster,
Generierungsmetadaten und Prüfreport weisen korrekt 2 MP aus; der Dateipräfix
ist kein Auflösungsnachweis.

Die fokussierte Prüfung des Renderjob-Vertrags besteht: `7 passed` mit
`python -m pytest scripts/tests/test_render_job.py -q`. Ein zuerst irrtümlich
verwendeter unittest-Aufruf hatte keine Tests gefunden und wird nicht als
Testnachweis gezählt. Es gab keinen vollständigen Release-Check.

## Nutzerfreigabe des gezeigten Kandidaten

Am 14. September 2026 hat der Nutzer C ausdrücklich visuell akzeptiert:

> Sieht wirklich gut aus. Nur noch leichte Abweichungen, zb im Auge fehlt der schwarz Strich/Punkt/Pupille. Aber das halte ich für vertretbar!

Diese Freigabe gilt für den oben hashgebundenen Druckmaster, einschließlich
der kleinen Augen-/Pupillendetail-Abweichung und der sonstigen leichten
Abweichungen im gezeigten Bild. Welches Pokémon mit dem Augenhinweis gemeint
ist, wurde nicht benannt. Daraus folgt keine pauschale Ausnahme für fehlende
Pupillen oder Anatomiefehler in anderen Panoramen. Die Betrachtung sämtlicher
neun Einzelkarten bleibt eine Agentenprüfung; eine zusätzliche vollständige
Einzelkartenprüfung durch den Nutzer wird nicht behauptet.

Der Freigabevorbehalt für das erste Vergleichsbild ist damit erfüllt.
One-Shot bleibt der bevorzugte Weg. Noch ausstehend sind die kanonische
Integration des experimentellen Prompts, die technische Promotion des
freigegebenen Bilds sowie der erneute PDF-/Release-Check.

Status: A verworfen, B durch C überholt, C visuell vom Nutzer akzeptiert.
Kein weiterer Render läuft. Keine Promotion, keine neuen Sets, keine
Änderung an Produktionsbildern, Generierungsmanifesten, PDFs oder Archiven.
Der mehrstufige Ansatz bleibt unbenutzte Reserve; seine Tiefenanalyse wird
nicht implementiert. Der experimentelle Prompt ist noch nicht als neuer
gemeinsamer Produktionsvertrag integriert.
