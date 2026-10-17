# P16 und P37: begrenzter quelltreuer Fallback-Versuch

Stand: 27.09.2026. Entwurf zur schriftlichen Freigabe. Keine neue
Bildfreigabe, Promotion oder PDF-Aktivierung durch diesen Text.

## Ziel und Anlass

Für `ExGen2/sections/primal` (P16) und `ME03` (P37) soll je ein neues,
druckkartensicheres Panorama als **unveröffentlichter Kandidat** entstehen.
Beide Scopes bleiben derzeit offen: P16-One-shots A/B/E/F schneiden Kyogre
oder Groudon an, einschließlich des 9B-Versuchs; bei P37 schneiden die
Versuche B/C/D Mega-Zygardes linkes Kanonen-Emblem an der r3c3-Grenze ab.
Der regionsgebundene P16-Pilot C brach vor der Bildausgabe wegen nichtendlicher
globaler Modellvorhersage ab. Ein bloßer weiterer Seed-, Größen- oder
Modellwechsel ist damit keine belegte Lösung.

Der Nutzer hat den alternativen Weg ausdrücklich nur für diese zwei erfolglos
gebliebenen Fälle gewählt. `joint_scene` bleibt Standard für alle anderen
Motive. Das ersetzt die frühere Bedingung, P37 erst nach einem erfolgreichen
Regions-P16-Pilot zu starten, **nur** für die hier gewählten, voneinander
isolierten Fallback-Versuche.

## Gewählter Weg und Trade-off

Wir testen den vorhandenen `identity_lock`-Pfad mit FLUX.2 Klein 4B und den
hashgebundenen Official-Artwork-Quellen. Er generiert eine passende Szene,
setzt die exakten Quellfiguren kontrolliert ein, prüft die vollständig
opaken Quellpixel und skaliert modellgestützt auf 300 dpi. Die druckrelevante
Silhouette lässt sich so wesentlich besser innerhalb des jeweiligen
Einlegers halten. Der Nachteil ist ein möglicher „aufgeklebter“ Eindruck bei
Licht, Bodenkontakt und Überdeckung.

Eine Reparatur des experimentellen Regions-Guiders könnte natürlicher
integrieren, braucht aber zuerst numerische Diagnose und einen neuen
Laufzeitvertrag; sie ist für diese konkrete Bildrunde nicht der gewählte
Weg. Ein direkter harter Ausschnitt aus den abgelehnten One-shots würde die
fehlenden Körperteile nicht beheben und ist ausgeschlossen.

## Kandidatenfluss

1. Für jeden Scope werden die dokumentierten One-shot-Fehler und die genauen
   Originalquellen mit Hashes festgehalten. Vor GPU-Arbeit wird der aktive
   ignorierte Poster-Workspace samt `renderer.local.yaml` geprüft. Die dort
   vollständige und erreichbare Zielkonfiguration wird wiederverwendet;
   private Verbindungswerte gelangen weder in Jobs noch in Git oder Berichte.
2. Pro Scope entsteht ein unveränderlicher, getrennt benannter Renderjob mit
   eigener Provenienz. Die produktiven Manifeste, Master, PDFs und die
   übrigen Panoramen bleiben dabei unverändert. Der erste Versuch pro Scope
   verwendet die bestehenden `identity_lock`-Parameter und die bisher
   festgelegten Quellfiguren; keine automatische Seed- oder Modellschleife.
3. Nach dem Lauf werden `run.json`, `comfyui.log`, Rohbild, 300-dpi-Master
   und jedes Ausgabebild zurückgeholt. Fehlt etwas, gilt der Lauf als
   unvollständig. Quellen- und Modellhashes, Pixelgleichheitsprüfung der
   unbedeckten opaken Quellflächen und die tatsächlichen neun physischen
   750 × 1050-px-Karten werden geprüft.
4. Der visuelle Review erfasst Panorama und jede Karte, insbesondere
   Kyogres/Groudons Außenkanten bei P16 und Mega-Zygardes linkes Emblem bei
   P37. Für jedes Pokémon wird der exakte Einleger neben seine exakte Quelle
   gestellt. Zusätzlich gelten Licht, Schatten, Bodenkontakt, Perspektive,
   Vordergrundüberdeckung, Kantenübergänge und eine durchgehende Landschaft
   als Freigabekriterien. Ein hart sichtbarer Ausschnitt, eine Schwebekante,
   eine falsche Anatomie oder eine verdeckte Schnittverletzung führt zur
   Ablehnung.
5. Nur ein konkret belegter Defekt erlaubt eine gezielte, erneut getrennt
   benannte Nacharbeit. Diese darf Vegetation/Schatten/Umgebung passend
   einbetten, aber keine Quellfigur unbemerkt ummalen oder abgeschnittene
   Merkmale kaschieren. Danach werden alle neun Karten und Quellpaare erneut
   geprüft. Es gibt keine unbegrenzte automatische Variantenserie.
6. Nur visuell bestandene Kandidaten werden dem Nutzer mit Gesamtbild und
   beschrifteten Karte-Quelle-Paaren zur exakten Bildentscheidung vorgelegt.
   Erst dessen ausdrückliche Freigabe des jeweiligen Kandidaten erlaubt eine
   getrennte Promotion. Dafür wird der einzelne aktive Manifestvertrag auf
   den tatsächlich verwendeten Fallback umgestellt und die normale
   Promotionsprüfung durchlaufen. Vorher bleiben beide `pdf.enabled`-Zustände
   und alle Original-PDFs unverändert.

## Grenzen und Fehlerverhalten

- Die Fallback-Nutzung ist auf P16 und P37 beschränkt; sie ist kein neuer
  globaler Default. 9B mit nichtkommerzieller Lizenz ist kein
  Produktionskandidat.
- Technische Pixelprüfungen belegen keine natürliche Integration. Umgekehrt
  ist eine schöne Gesamtansicht kein Nachweis für alle neun Schnittkarten.
- Wenn eine Quelle fehlt, ein Hash abweicht, ein Job scheitert, eine Figur
  abgeschnitten oder der Klebeeffekt nicht vertretbar ist, bleibt der Scope
  offen. Der andere Scope kann unabhängig weiter geprüft werden.
- Frühere Freigaben anderer Kandidaten werden nicht übertragen. Auch ein
  bestandener Agentenreview wird nicht als menschliche Bildabnahme etikettiert.

## Tests und Nachweise

Die bestehenden Unit-/Integrationsprüfungen für `identity_lock`,
Quellpixel-Audit, Modell-Upcaling, Planner und Promotion werden vor einem
Produktionswechsel ausgeführt. Pro Kandidat werden Eingabemanifest,
unveränderlicher Job, vollständige Rückgaben, Quell-/Ausgabehashes,
Kartenmaße und der visuelle Befund dokumentiert. Die unveränderten
Produktionsmaster und PDFs werden gegen den Ausgangsstand geprüft.

Diese Runde ist abgeschlossen, wenn für beide Scopes entweder ein exakt
bezeichneter, vollständig geprüfter Kandidat zur Nutzerabnahme vorliegt oder
ein konkreter, belegter Ablehnungs-/Blockiergrund. Sie ist **nicht** schon
mit zwei erfolgreichen GPU-Jobs abgeschlossen.
