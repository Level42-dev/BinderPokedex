# P16: stärkerer One-shot, Druckzuschnitt weiter nicht sicher

Stand: 23.09.2026. **Abgelehnter Versuch, keine Nutzerfreigabe und keine Übernahme.**

## Abgegrenzter Test

Nach dem gescheiterten regional maskierten Versuch E wurde dessen experimenteller
Pfad aus dem aktiven Renderer entfernt. Für Versuch F wurden gegenüber dem
unmaskierten P16-Versuch B nur FLUX.2 Klein 4B und Qwen 3 4B gegen das bereits
vorhandene FLUX.2 Klein 9B FP8 und Qwen 3 8B getauscht. Die vier geänderten
Manifestfelder sind Modellname und -Hash sowie Encodername und -Hash. Seed
`653315091`, beide Quellbilder, Merkmalsbeschreibungen, Landschaft,
Positionsreferenz-Skalen `0.55`, 2-MP-Leinwand und vier Sampling-Schritte sind
gleich geblieben. Der generierte Prompt ist bytegleich
(`2a684e7b8860f31ac5df8d088d294b8786f8c220a043691d57b0da5bb2bb41b4`).
Der Workflow unterscheidet sich nur in den zwei Modell-Ladeknoten; er enthält
einen Sampler und keine Masken, Composites oder Nachbearbeitung.

Die vollständigen, ignorierten Versuchsdateien liegen unter
`tmp/oneshot-trials/p16-batch-20260923-f/`. Der überprüfte deutsche Gesamtbogen
`review/poster-de.png` hat SHA-256
`53f0269bb9a5d713bd3cd5975eac1772bd241f198a611e0bff638932aa5c61e9`.
Die versiegelte technische Prüfevidenz hat SHA-256
`55e449738ea2f90daaea8a2b1673b575eac81226e4ded333226c997fc9ade881`.
`run.json`, `comfyui.log`, das Ausgabebild und sämtliche neun exakten
750 × 1050 px / 300-dpi-Kartenausschnitte wurden zurückgeholt und geprüft.
Die Produktionsmaster blieben unverändert.

## Sichtprüfung aller neun Karten

Die sechs oberen Karten sind vollständig; Titel und Infokarte bleiben innerhalb
ihrer jeweiligen Flächen. Auf der unteren Reihe verletzt F jedoch die
entscheidende Bedingung: Kyogres hintere Flossen laufen von r3c1 nach r3c2,
Groudons Schwanz von r3c3 ebenfalls nach r3c2. Der mittlere Einleger enthält
abgeschnittene Teile beider Pokémon, während beiden Figuren auf ihrer eigenen
Karte diese Teile fehlen. Die Quellmotive sind zwar besser erkennbar als im
maskierten Versuch E, aber F ist keine saubere einzeln schneidbare Vorlage.

| Ausschnitt | SHA-256 | Ergebnis |
| --- | --- | --- |
| r3c1 Kyogre | `95c1bae373b3a37c99a454cffcdbd1a30967eeb23376ceb98baab3bd0f853d4a` | Rechte Flossen abgeschnitten |
| r3c2 Mitte | `65252e18502ea2c5283bcaed7f5c52107c5f9d09c6eabcfdcfc31d983b6bc033` | Flossen und Schwanz ragen hinein |
| r3c3 Groudon | `35fed3685dcba431bd5f107df22ad3c9e5de74d7c066573611e535cdab48386b` | Linker Schwanz abgeschnitten |

Der maskierte Versuch E hatte bereits stärkere Figurenverlagerung und wurde
ebenfalls abgelehnt. Er ist kein Fallback für F. Die vorangegangenen
unmaskierten A/B-Versuche erfüllten die Kombination aus Quellenidentität und
Einlegergrenzen auch nicht zuverlässig. Deshalb **kein P37-Folgerender und
keine Promotion**. P16 und P37 bleiben offen. Ein weiterer bloßer Seed- oder
Skalenwechsel ist nach diesen materiell unterschiedlichen Fehlversuchen keine
belastbare Freigabestrategie. Vor einem neuen Render sollte gezielt geklärt
werden, ob ein tatsächlich hart begrenzender One-shot-Mechanismus verfügbar ist;
erst falls nicht, ist der bereits vorgesehene mehrstufige Fallback zu bewerten.

## Nachprüfung der One-shot-Schnittliniensteuerung

Der am 23.09.2026 gepinnte ComfyUI-Stand ist `87d23b8`. Sein
[`ConditioningSetMask`](https://github.com/Comfy-Org/ComfyUI/blob/87d23b81765161624889febfb3b81f19f3c8435b/nodes.py)
hängt eine Maske an die Konditionierung; der
[`Sampler`](https://github.com/Comfy-Org/ComfyUI/blob/87d23b81765161624889febfb3b81f19f3c8435b/comfy/samplers.py)
gewichtet damit Vorhersagen, beschneidet aber keine Figurenpixel. Beim Versuch
E blieb außerdem die gemeinsame Positionsreferenz mit beiden Figuren im
globalen, unmaskierten Zweig. Seine zusätzlichen Kartenmasken konnten deren
Einfluss deshalb nicht exklusiv auf r3c1 und r3c3 begrenzen. Der reine
Konditionierungs-Maskenansatz ist für eine harte Zuschnittgarantie widerlegt.

Die bereits vorhandene Variante `regional_identity_joint` nimmt die globale
Figurenreferenz heraus, erzeugte jedoch bei den früher geprüften Motiven
getrennt wirkende Horizonte und Kartenhintergründe. Sie ist ebenfalls keine
freigabefähige Standardlösung. Eine lesende Prüfung des konfigurierten Workers
fand keinen installierten regionalen Attention-/Control-Knoten. Es wurde
nichts installiert oder gerendert. Ein weiterer Seed-, Modell- oder
Maskenstärke-Versuch würde keine neue Schnittliniengarantie prüfen.

Ein möglicher **neuer** One-shot-Ansatz wäre ein eigener regionsgebundener
Sampling-Eingriff: ein gemeinsamer latenter Bildzustand und ein finaler Decode,
aber pro Denoising-Schritt ein globaler Landschaftsbeitrag und auf die
Einleger-Innenflächen begrenzte Figurenbeiträge. Dabei müssten
Referenz-/Figureninformationen auch in der Attention außerhalb ihrer Regionen
gesperrt und Dekodier-Randwirkungen durch Abstand zur Schnittlinie plus
automatische sowie visuelle Crop-Prüfung abgefangen werden. Das ist eine
Architekturänderung, **noch kein implementierter oder bewiesener Mechanismus**;
seine Nahtfreiheit, Quelltreue und Laufzeit sind offen. Vor Umsetzung sind
Designfreigabe und ein isolierter P16-Prototyp nötig.

Zusätzlich ist das 9B-Modell laut
[`FLUX.2`-Modellübersicht des Herstellers](https://github.com/black-forest-labs/flux2)
non-commercial lizenziert, während 4B unter Apache 2.0 steht. Der 9B-Versuch
bleibt deshalb eine Diagnose; für einen verkäuflichen Release ist zunächst der
4B-Pfad oder eine gesondert geklärte Lizenz maßgeblich.
