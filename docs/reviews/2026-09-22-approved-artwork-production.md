# Übernahme freigegebener Panoramen – 22.09.2026

## Auftrag und Reihenfolge

Fortsetzung nach der Nutzerfreigabe von P15-D. Freigegebene Bildpixel bleiben
unverändert; keine neue Generierung, Veröffentlichung oder pauschale Freigabe.

1. P15-D und P40-B gegen ihre exakten Prüfnachweise und aktuellen Manifeste prüfen.
2. Rohbilder, vollständige Master, deutsche Vorschauen, alle neun Karten pro
   Motiv und alle sechs Originalquellen erneut visuell prüfen.
3. Bisherige Produktionsdateien sichern, beide Kandidaten über die reguläre
   Übernahmefunktion installieren und anschließend validieren.
4. Druckausgaben nur für vollständig gültige Zielumfänge erstellen. Ungeprüfte
   Nachbarabschnitte nicht durch Ersatzdeckblätter oder falsche Freigaben umgehen.
5. Die älteren akzeptierten Versuche Basis-Set B und ExGen3 Mega C auf eine
   wahrheitsgetreue technische Übernahme prüfen; übrige offene Motive getrennt halten.

## Frische Vorprüfung

Beide Laufbeschreibungen stimmen mit der aktuellen Generierungskonfiguration und
deren Eingabefingerabdruck überein. Die Quelldateien sind vorhanden. Vollständige
Rohbilder/Master, deutsche Vorschauen, alle 18 physischen Kartenausschnitte und die
sechs tatsächlich verwendeten Original-Pokémon wurden in diesem Durchlauf angesehen.

| Ziel | Exakt geprüfter Master (SHA-256) | Bildentscheidung |
| --- | --- | --- |
| P15 / ExGen2 Mega / D | `ae8d7afad5051c47117650ae03c1b4cbc30c7da8b7083a10f9e7da3d801b55bb` | Rayquazas gezeigter Abstand vom Nutzer akzeptiert; erneute Agentenprüfung aller Figuren und Karten ohne neuen harten Befund. |
| P40 / ExGen3 normal / B | `0ec6eb54e7e0797021497ade7a624b025b797fe03217117322199413770befa4` | Nutzer akzeptiert Identitäten und größere Komposition; keine Änderung der Figuren. |

Die Figuren einschließlich leuchtender Fortsätze bleiben in ihren tatsächlichen
Karten. P15-Latios hat weiterhin wenig Abstand an der linken Nasenspitze; dies
ist keine Behauptung eines großzügigen Sicherheitsrands. Rayquazas rechter Rand
bleibt enger als der linke, wie vor der Nutzerentscheidung offengelegt.
Beschriftungen und Infokarten sind vollständig enthalten. Keine zusätzlichen
Figuren, eindeutig falschen Körperteile oder neuen Vordergrund-Konturabbrüche
bei dieser erneuten Sichtung festgestellt. Kleine Linien-/Zeichenunterschiede
bleiben Bestandteil der gezeigten Fassungen.

**Abgrenzung:** Die historischen `layout_contract_pass: false`-Befunde zu den
kleineren numerischen Prompt-Zielgrößen werden nicht geändert. Die Freigabe der
tatsächlich gezeigten größeren Komposition und die Prüfung realer Schnittkanten
sind davon getrennt. Die technische Übernahme wird als Agentenprüfung erfasst;
die ursprünglichen, engeren Nutzerfreigaben werden nicht erweitert.

SV07-B bleibt wegen des vorbehaltenen Hopplo-Schattens offen. Dschungel E besitzt
nur eine Teilfreigabe für Pikachu und zwei Halme. Andere alte, zurückgezogene
Panorama-Freigaben bleiben zurückgezogen. Eine Gesamtfreigabe für v10 folgt aus
diesem Dokument nicht.

## Ausführung und Prüfung

- Beide Kandidaten sind über die reguläre Übernahmefunktion installiert,
  einschließlich aktueller Herkunftsnachweise. Die bisherigen beiden Master
  und Nachweise bleiben im ignorierten Sicherungsordner erhalten.
- Beide Produktionsvalidatoren bestehen. Master, Vorschauen und alle 18 Karten
  sind pixelidentisch mit den überprüften Kandidaten. Die 40 übrigen Master
  sind gegenüber dem eingefrorenen Produktionsstand unverändert.
- Die unabhängige Prüfung fand in den zwei übernommenen Bildpaketen keine
  kritischen oder wichtigen Mängel. Der enge Latios-Rand bleibt als kleine
  Drucktoleranz-Einschränkung dokumentiert; ein realer Druck-/Schneidtest wurde
  nicht behauptet.
- Zwei getrennte deutsche Druckproben wurden mit dem bestehenden
  Produktionsrenderer erstellt: Schnittkarten und durchgehende Panoramen.
  Jede enthält P15, P40 und die reguläre Herkunfts-/Hinweisseite, also drei
  A4-Seiten. Keine vollständige ExGen2-/ExGen3-Ausgabe und kein Release.
- Alle finalen Seiten wurden gerastert. Vier Bildseiten und beide
  Hinweisseiten wurden visuell geprüft; die Bildseiten sind nach Ergänzung
  der Hinweisseite pixelidentisch. Die eingebetteten Originalpixel und die
  PDF-Platzierung sind zusätzlich geprüft: neun Karten von 63,5 × 88,9 mm
  beziehungsweise ein Panorama pro Bildseite. Für den Probedruck 100 %
  verwenden, keine Seitenanpassung.
- Die fokussierte Renderer-/Quellen-/Fingerprint-/Transport-Suite besteht
  mit **119 Tests**. Dies ist kein vollständiger Projekttestlauf.
- Alte Release-PDFs und ZIPs wurden nicht neu gebaut oder ersetzt. Keine
  Generierung, kein Commit, Push, Tag oder Veröffentlichung.

Die PDF-Kontrollbilder wurden schließlich mit der vorhandenen lokalen
Poppler-Installation erzeugt. Das gebündelte Werkzeug verursachte massive
Schriftkonfigurations-/Cachewarnungen; diese wurden nicht als Bildfehler oder
als erfolgreicher stiller Kontrolllauf ausgegeben. Die finalen lokalen
Renderläufe endeten erfolgreich, mit verbleibenden nichtfatalen Cachewarnungen.

## Zusätzlich gefundener Arbeitsplan-Widerspruch

P15 wird korrekt als aktuell geführt. Bei P40 sind Generierung und Überlagerung
laut Validator aktuell; der Arbeitsplan meldet trotzdem `scene_catalog_drift`.
Ursache: Die geprüfte Szenenvorgabenliste enthält die unveränderte Katalogliste
plus einen zusätzlichen Platzierungshinweis. Der Arbeitsplan erlaubt zusätzliche
Wörterbuchfelder, vergleicht Listen aber auf vollständige Gleichheit.

Vorgeschlagene eng begrenzte Korrektur: Unveränderte Katalogvorgaben als
Listenanfang und danach zusätzliche Hinweise zulassen. Änderungen, fehlende
Vorgaben oder eine andere Reihenfolge bleiben gesperrt. Die bestehenden
Fingerabdrücke prüfen weiterhin jeden zusätzlichen Hinweis. Keine Änderung an
Prompt, Bildern oder historischen Nachweisen. Diese neue kleine Codeänderung
wartet gemäß Design-Skill auf die gesondert gestellte Freigabe; sie ist noch
nicht implementiert. Der P40-Widerspruch wurde nicht als bestanden umetikettiert.

## Noch offene Übernahmen und nächste Bildrunde

Die älteren akzeptierten ExGen3-Mega-C-/Basis-Set-B-Dateien sind unverändert
vorhanden. Ihre ursprünglichen Versuchsprotokolle besitzen jedoch ausdrücklich
einen experimentellen Prompt und keine kanonische Übernahmefähigkeit. Beide
verwenden außerdem andere Referenzierungs-/Auflösungsparameter als die aktiven
Manifeste. Sie dürfen nicht nachträglich als aktuelle Version 11 etikettiert
werden. Nötig ist ein enger, versionierter Import des tatsächlichen historischen
Vertrags mit unveränderten Job-, Prompt-, Quellen- und Bildprüfsummen. Das ist
eine noch offene Implementierung, kein Grund, die akzeptierten Bilder ungefragt
neu zu generieren.

Für die nächste Bildentscheidung sind **P03 Dunkelnacht, P10 Pokédex Generation
VII und P27 Stürmische Funken** erneut bereitgestellt. Alle 21 Gesamtbild-,
Karten- und Quellenprüfsummen stimmen mit der bisherigen Sichtprüfung überein.
Die [neun direkten Karten-/Quellenpaare](2026-09-14-panorama-shortlist.md)
enthalten ihre konkreten kleinen Abweichungen. Es wurde keine neue menschliche
Freigabe ergänzt.

Exakte Dateien, Prüfsummen, Prüfgrenzen und offene Punkte:
[maschinenlesbarer Prüfstand](2026-09-22-approved-artwork-production.json).
