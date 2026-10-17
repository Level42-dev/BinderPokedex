# Panorama-Nachprüfung für Version 10

Stand: 12. September 2026. Prüfung abgeschlossen; bestehende Korrekturverfahren
getestet. Der gezielte Renderer-Umbau ist vom Nutzer freigegeben und wird
zunächst als ExGen3-Prototyp umgesetzt; noch kein Ersatz ist freigegeben.

Alle **42 Panoramen mit 125 Figurenpositionen und 378 Kartenfeldern** wurden
gegen ihre tatsächlichen Originalreferenzen geprüft. Die Prüfsummen aller
42 Master und 125 verwendeten Referenzdateien wurden zusätzlich abgeglichen.
Die Quellen passen; die gefundenen Abweichungen entstehen beim generativen
Neuzeichnen oder bei der Einbettung der Figuren in die Landschaft.

## Ergebnis

| Umfang | Bestanden | Abgelehnt | Unsicher, nicht freigegeben |
| --- | ---: | ---: | ---: |
| Panoramen | 1 | 41 | 0 |
| Einzelne Figurenpositionen | 22 | 86 | 17 |

Nur **ME05** besteht als vollständiges Panorama, bestätigt durch eine zweite
unabhängige Prüfung. Ein einzelnes bestandenes Pokémon reicht nicht zur
Freigabe eines Panoramas, wenn andere Figuren darin durchfallen.

Konkrete Beispiele sind fehlende Bruststacheln bei ExGen3 Mega-Lucario,
veränderte Kopf-/Brustformen bei Koraidon und Miraidon, zusätzliche Krallen
bei mehreren Bisasam-Motiven, fehlende Zähne bei Startern und ein fehlendes
Augendetail bei SV08 Ho-Oh. SV07 Hopplo hat zwar zwei Ohren, verliert aber
weiterhin andere typische Merkmale. Alle Befunde sind pro Figur dokumentiert;
unsichere Details werden ausdrücklich nicht als bewiesene Anatomiefehler
ausgegeben und auch nicht freigegeben.

Die bisherigen Freigabevermerke der 41 abgelehnten Master wurden mit einem
hashgebundenen Agenten-Prüfvermerk zurückgenommen. Historische Angaben bleiben
erhalten. Die bestehende Release-Prüfung lehnt diese Freigaben dadurch ab.
Bilddateien, vorhandene PDFs und ZIPs sind bisher unverändert und dürfen nicht
als fertige verkäufliche Version 10 betrachtet werden.

## Korrektur und erneute Freigabe

- [x] Alle Originalquellen, Master und physischen Kartenfelder prüfen.
- [x] Befunde und zurückgenommene Freigaben an konkrete Dateihashes binden.
- [x] ME05 und den unsicheren SV08-Befund unabhängig gegenprüfen.
- [x] ExGen3 Mega mit neuem Seed sowie anderer dokumentierter Referenzführung testen; beide Versuche abgelehnt.
- [x] Den dokumentierten Identity-Lock-Ansatz mit unveränderten Quellfiguren an ExGen3 prüfen: Anatomie besteht, Szeneneinbindung nicht.
- [x] Übergangszone separat vergleichen: Geisterkonturen werden reduziert, Bodenkontakt bleibt unverändert. Die nur für den Versuch geänderte Konfiguration ist zurückgesetzt.
- [x] Design für einen begrenzten, quellenpixelgeschützten Schattenpass freigeben.
- [ ] Renderer-Vertrag, Tests und einen ExGen3-Prototyp gemäß [Umsetzungsplan](../superpowers/plans/2026-09-12-source-locked-grounding.md) erweitern und prüfen.
- [ ] Für jedes abgelehnte Panorama einen bestandenen Ersatz erzeugen und Rohbild, Druckmaster sowie alle neun Kartenfelder prüfen.
- [ ] Ausschließlich bestandene Ersatzmaster samt vollständiger Provenienz übernehmen.
- [ ] Betroffene PDFs und Archive konsistent neu bauen und erneut prüfen.
- [ ] Abschließende menschliche Motiv-/Druckfreigabe; kein automatisches Veröffentlichen.

## Detailnachweise

- [Gesamtübersicht mit allen 42 Zielmotiven](2026-09-12-panorama-audit-summary.json)
- [Pokédex und ExGen1/2](2026-09-12-panorama-audit-aggregate.json)
- [Base1 bis SV07](2026-09-12-panorama-audit-early-tcg.json)
- [SV08 bis MEP](2026-09-12-panorama-audit-late-tcg.json)
- [ExGen3 einschließlich PDF-Seiten 1 und 27](2026-09-12-panorama-audit-exgen3.json)
- [Unabhängige Zweitprüfung ME05/SV08](2026-09-12-panorama-audit-me05-sv08-second-review.json)
- [Erster Identity-Lock-Test: Anatomie bestanden, Szene abgelehnt](2026-09-12-exgen3-mega-identity-lock-trial-1.json)

## Grenze des bestehenden Renderers

Beide Identity-Lock-Versuche erhalten alle 40.345 vollständig deckenden
Quellpixel. Die unabhängige Prüfung des ersten Versuchs bestätigt auch nach
dem Modell-Upscale die korrekte Anatomie aller drei Figuren. Trotzdem fehlen
Lucario ein überzeugender Bodenkontakt und passende Körperschatten. Latias
und Diancie wirken ohne zuordenbare Bodenschatten aufgelegt.

Das ist kein Seed-Problem: Der erste Durchlauf erzeugt die Landschaft ohne
Figuren. Der zweite sieht die Figuren, darf aber ausschließlich oberhalb von
ihnen ändern. Die Figuren liegen bei Rohbild-y 875–1092; der editierbare
Bereich endet im ersten Versuch bei y817, im zweiten schon bei y525. Alle
Pixel von y818 bis zum unteren Rand sind in beiden Rohbildern identisch.

Empfohlene Erweiterung: ein eng begrenzter, separat prüfbarer Schattenpass,
der nur freigegebenen Boden unter/neben den Figuren verändert. Alle
Figurenpixel und alle Pixel außerhalb der erlaubten Maske bleiben gesperrt.
Masken, Stütz-/Projektionspunkte und der geänderte Render-Vertrag müssen
versioniert und geprüft werden. Zunächst muss ein ExGen3-Prototyp technisch
und visuell bestehen; erst danach wäre die Anwendung auf andere Motive
sinnvoll. Die Umsetzung ist freigegeben; ein bestandener Prototyp liegt noch
nicht vor. Der neue Durchlauf behält die erste Landschaft bei und ersetzt
die problematische obere Überblendung durch den gezielten Boden-Edit.

Die Originalberichte beschreiben den Zustand zum Prüfzeitpunkt. Darin
enthaltene Provenienz-Dateihashes liegen deshalb zeitlich vor dem ergänzten
Rücknahmevermerk; die Master- und Quellenhashes bleiben unverändert. Eine
Agentenprüfung wird nicht als menschliche Freigabe ausgewiesen.
