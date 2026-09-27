# Regionsgebundener One-shot als gezielter Panorama-Fallback

Stand: 23.09.2026. Entwurf zur Freigabe; **keine Implementierung und keine Bildfreigabe**.

## Ziel und Entscheidung

Der bestehende `joint_scene`-Flow bleibt für neue und bereits erfolgreiche
Panoramen unverändert der Standard. Ein zusätzlicher Modus
`region_constrained_joint` darf nur für ein ausdrücklich ausgewähltes Motiv
verwendet werden, dessen bisheriger One-shot nach dokumentierten, materiell
unterschiedlichen Versuchen weiter an Quelltreue oder physischen
Einlegergrenzen scheitert. Es gibt keine automatische Umschaltung und keine
Massenregenerierung. Erster und einziger Pilot ist P16
(`ExGen2/sections/primal`); P37 folgt nur nach einem technisch und visuell
bestandenen sowie vom Nutzer am exakten P16-Artefakt akzeptierten Pilot.

Erfolg bedeutet: ein zusammenhängendes Panorama mit natürlich integrierten
Pokémon, aber beide P16-Figuren vollständig innerhalb ihrer eigenen
750 × 1050 px / 300-dpi-Einleger. Die Anatomie und prägenden Markierungen
müssen gegen die beiden hashgebundenen Originalquellen bestehen. Vordergrund
darf Figuren plausibel überdecken, jedoch weder Gliedmaßen verstecken noch
Kartenränder kaschieren. Ein technisch gelungener GPU-Lauf ist keine Freigabe.

## Ausgangsbefund und Alternativen

- Ein weiterer Prompt-, Seed-, Skalen- oder 9B-Modellwechsel bleibt ein weicher
  Hinweis. P16 A/B/E/F haben gezeigt, dass das nicht zuverlässig schneidbare
  Figuren ergibt. Die globale Figurenreferenz in E blieb trotz zusätzlicher
  `ConditioningSetMask`-Knoten unmaskiert. Der gepinnte
  [ComfyUI-Knoten](https://github.com/Comfy-Org/ComfyUI/blob/87d23b81765161624889febfb3b81f19f3c8435b/nodes.py)
  versieht Konditionierung mit einer Maske; sein
  [Sampler](https://github.com/Comfy-Org/ComfyUI/blob/87d23b81765161624889febfb3b81f19f3c8435b/comfy/samplers.py)
  beschneidet dadurch nicht die fertige Figur. Diese Variante wird nicht erneut
  als angeblich harter Fallback verwendet.
- Das vorhandene, cast-freie `regional_identity_joint` bleibt reproduzierbar,
  erzeugte aber bereits sichtbare Karten-/Horizontnähte. Auch bloßes
  Wiederverwenden dieser Variante ist kein neuer Lösungsweg.
- Empfohlen ist ein **einziger gemeinsamer latenter Bildzustand mit einem
  Sampling-Verlauf**, dessen Figurenbeiträge in jedem Schritt auf die
  jeweiligen Karten-Innenflächen begrenzt werden. Das ist aufwendiger und kann
  Nähte erzeugen, fügt aber keine fertigen Figuren nachträglich ein.
- Ein mehrstufiges Einsetzen oder Überzeichnen von Pokémon bleibt nur der
  gesondert zu entscheidende letzte Fallback, falls auch dieser neue One-shot
  P16 nicht sauber löst.

## Ablauf des experimentellen Modus

1. Ein `Fallback-Eignungsnachweis` nennt Motiv, Original-Flow,
   fehlgeschlagene Kandidaten mit Bildhashes, konkrete Fehler und die
   Entscheidung, **nur dieses Motiv** für den Modus vorzubereiten. Ohne diesen
   Nachweis lehnt die Vorbereitung den Modus ab. Der Nachweis ist keine
   Freigabe des neuen Bildes.
2. Die tatsächliche Abbildung vom 1200 × 1664 px Generierungsbild auf die
   neun physischen 3×3-Druckeinleger definiert die Regionen; bloß gleichmäßig
   aufgeteilte Bilddrittel sind dafür unzulässig. Der Innenabstand an jeder
   Kartenkante beträgt `ceil(0.08 × Kartenbreite / 16) × 16`
   Generierungspixel; für P16 ergibt dies 32 px Abstand zur senkrechten
   Schnittlinie. Regionen dürfen einander nicht überlappen.
   Quellen, Positionen und Prüfsummen bleiben in der Laufmetadatei gebunden.
3. Ein globaler Zweig beschreibt ausschließlich die durchgehende Landschaft
   und erhält **keine** Pokémon- oder Sammelreferenz. Je Figur gibt es einen
   lokalen Zweig mit nur ihrem eigenen Positionierungsbild, ihrem unveränderten
   Detailbild und ihren Quellmerkmalen. Globale und lokale Zweige sehen in
   jedem Schritt denselben aktuellen latenten Gesamtzustand.
4. Ein projektspezifischer, versionierter Guider berechnet pro Schritt die
   globale Vorhersage und je eine lokale Vorhersage. Er addiert pro Figur nur
   die Differenz `lokal − global` innerhalb ihrer eingerückten Region zur
   globalen Vorhersage; am inneren Rand wird diese Differenz weich auf null
   geführt. Für P16 sind das höchstens drei Modellvorhersagen pro Schritt,
   aber weiterhin **ein** Bildzustand, **ein** Sampler und **ein** finaler
   VAE-Decode. `ImageCompositeMasked`, spätes Einsetzen, Inpainting und ein
   zweiter generativer Durchlauf sind im Pilotgraph verboten.
5. Die Modell-Attention muss verhindern, dass Figurenreferenzen die
   Vorhersage **außerhalb** ihrer Karte beeinflussen. Im globalen Zweig dürfen
   Abfragen außerhalb der Figurenzonen nicht auf Bildtokens innerhalb dieser
   Zonen zugreifen; im lokalen Zweig dürfen Referenztokens nur Abfragen der
   zugehörigen Karte bedienen. Der Guider verwendet dafür eine am gepinnten
   ComfyUI-/FLUX.2-Klein-4B-Stand geprüfte Query/Key-Regionssperre.
   Ist diese Sperre nicht sicher an die
   gepinnte API anschließbar, endet der Pilot **vor** einem GPU-Render; eine
   bloße `ConditioningSetMask` wird nicht als Ersatz ausgegeben.
6. Das Ergebnis wird wie bisher deterministisch auf 300 dpi gebracht,
   lokalisiert und in neun physische Karten zerlegt. Die geometrische Sperre
   begrenzt den **Figureneinfluss während des Samplings**, beweist aber allein
   noch keine semantisch perfekte Endsilhouette: VAE-Randwirkungen und
   ungewollte Bildmuster bleiben möglich. Deshalb ist der vollständige
   visuelle Karten- und Quellenvergleich zwingend.

## Isolation, Datenfluss und Fehlerverhalten

Der Pilot verwendet zunächst eine ignorierte P16-Manifestvariante und einen
unveränderlichen Renderjob. Der produktive P16-Master, die übrigen 39 Motive,
alle PDFs und der Standard-Graph bleiben unverändert. Der neue Modus darf
später nur über eine explizite per-Motiv-Konfiguration aktiviert werden; ein
globaler Default-Wechsel ist ausgeschlossen. Fingerprint und Provenienz
enthalten Modus-/Guider-Vertragsversion, Regionengeometrie, Quellhashes,
Modellhash und den exakten Workflow. Historische Freigaben werden nicht auf
neue Artefakte übertragen.

Der projektspezifische Guider soll als hashgebundene Job-Erweiterung geladen
werden, ohne die bestehende `custom_nodes`-Installation des Workers zu
verändern. Ob die gepinnte ComfyUI-Laufzeit einen solchen isolierten Ladeweg
und die benötigten Attention-Hooks überhaupt unterstützt, ist ein eigener
Machbarkeitsnachweis im Implementierungsplan. Gelingt dieser Nachweis nicht,
endet der Pilot vor einem GPU-Lauf; es gibt keine stille Runtime-Änderung.
Vor GPU-Arbeit wird wie üblich der private Workspace-Marker geprüft und dessen
bestehendes Ziel wiederverwendet.
Job, `run.json`, `comfyui.log` und alle Bilder kommen zurück. Fehlende
Quellen, unpassende Hashes, überlappende Masken, inkompatible Hook-Signaturen,
Speicherfehler und unvollständige Rückgaben brechen ohne Promotion ab.

Für einen möglichen verkäuflichen Release ist der Pilot auf das vorhandene
FLUX.2-Klein-4B-Modell mit Apache-2.0-Lizenz begrenzt. Das bereits getestete
9B-Modell ist laut
[Herstellerübersicht](https://github.com/black-forest-labs/flux2)
non-commercial lizenziert und wird hier nicht zum Produktionskandidaten.
Unabhängige Rechte an Pokémon-Quellmotiven bleiben eine eigene Releasefrage.

## Test- und Freigabegatter

- Red/Green-Tests belegen, dass der Standard-Workflow bytegleich bleibt und
  der neue Modus ohne Eignungsnachweis nicht vorbereitet werden kann.
- Geometrietests prüfen die exakten neun Karten, nicht überlappende
  Innenregionen und Null-Figurenbeitrag an/außerhalb der Schnittlinien.
- Hook-/Guider-Tests mit kleinen künstlichen Tensoren prüfen getrennte
  Referenzen, nur einen latenten Zustand und einen Decode. Ein nicht
  funktionsfähiger Attention-Hook stoppt den Versuch vor dem Render.
- Ein einziger P16-4B-Job verwendet zunächst dieselben P16-B-Quellen, dieselbe
  Landschaftsvorgabe und Seed `653315091`; nur der Steuerungsmodus ändert sich.
  Vor einer Wiederholung wird der konkrete Fehler analysiert; keine
  automatische Seed-Schleife.
- Nach dem Lauf werden voller Rohbogen, textfreier Master, deutsches Panorama,
  alle neun exakten Druckeinleger und beide Originalquellen geprüft. Besonders
  r3c1, r3c2 und r3c3 dürfen keine abgeschnittenen oder in die Mitte ragenden
  Gliedmaßen enthalten. Nahtfreiheit, Bodenkontakt und Quellmerkmale zählen
  ebenso wie der Zuschnitt.
- Nur ein bestandener Kandidat wird dem Nutzer als Gesamtbild plus
  Karte/Quelle-Paare vorgelegt. Erst dessen ausdrückliche, dateigebundene
  Freigabe erlaubt Promotion und danach einen getrennten P37-Pilot.
- Scheitert die Hook-Machbarkeit oder P16 an Nähten, Quellenidentität oder
  Kartengrenzen, bleibt der neue Modus experimentell. Ein mehrstufiger
  Fallback wird dann **nicht automatisch** aktiviert, sondern gesondert
  besprochen.

## Kosten und Grenzen

Die zwei lokalen Figurenzweige können P16 gegenüber dem bestehenden 4B-Lauf
ungefähr um den Faktor drei bei den Modellvorhersagen verteuern; tatsächliche
Zeit und MPS-Speicherbedarf sind vor dem Pilot unbekannt. Die Methode kann
Figureneinfluss geometrisch begrenzen, aber weder eine schöne Komposition noch
korrekte Anatomie erzwingen. Die Freigabe bleibt deshalb bild- und
druckkartenbezogen, nicht graphbezogen.
