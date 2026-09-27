# Freigegebene historische Panoramen in deutsche PDFs übernehmen

Stand: 27.09.2026. Entwurf zur schriftlichen Freigabe. Dieser Text ist keine
Bild-, PDF- oder Release-Freigabe.

## Ziel und Geltungsbereich

Die vom Nutzer am 14.09.2026 visuell akzeptierten textfreien Master für
`Base1` (Kandidat B) und `ExGen3/sections/mega` (Kandidat C) sollen mit
unveränderten Bildpixeln über den regulären Poster- und PDF-Pfad nutzbar
werden. Anschließend werden die jeweils betroffenen deutschen PDFs neu
erzeugt und vollständig geprüft. Die ursprüngliche Bildentscheidung gilt nur
für die exakt gezeigten Master, nicht für Logo, alle Einleger oder eine
pauschale Release-Freigabe.

Die beiden freigegebenen Dateien liegen unter `assets/reviewed-candidates`:

| Scope | Master-SHA-256 | Noch offen |
| --- | --- | --- |
| `Base1` | `d06f69eb6e010b2670987a2209d3aec50848ac694aaefec64dc70d342ce0d9b4` | Historischer Import, deutsches Logo, PDF-Prüfung |
| `ExGen3/sections/mega` | `eb61f272fd22bd400b2c2555cb2a490fad47c85b3947087a88b96b2e9dce3ebd` | Historischer Import, vollständige ExGen3-PDF-Prüfung |

Die bereits aktive normale ExGen3-Sektion bleibt unverändert. Keine anderen
Master, nicht akzeptierten Kandidaten oder bestehenden Release-PDFs werden
stillschweigend ersetzt.

## Ausgangslage und gewählter Weg

Beide archivierten Versuche sind als `canonical_promotion_eligible: false`
und `experimental_prompt_override: true` gekennzeichnet. Ihre tatsächlichen
Läufe verwendeten `spatial_identity_joint`, 2,0 Generierungs-Megapixel,
eigene Prompts und unveränderliche Remote-Jobs. Die derzeitigen Manifeste
beschreiben dagegen `individual_spatial_joint` mit 1,0 Megapixel. Ein bloßes
Kopieren der PNGs oder eine Umbenennung zu einem aktuellen v11-Lauf würde
einen falschen Herkunftsnachweis erzeugen.

Gewählt ist ein enger, versionierter **historischer Import** der tatsächlichen
Verträge. Alternativen wären erneutes Generieren (verliert die exakten
Nutzerfreigaben) oder das Umgehen der Promotionsprüfung (verliert die
technische Nachvollziehbarkeit); beides wird ausgeschlossen. Der Import wird
nur für diese zwei dokumentierten Kandidaten gebaut, nicht als allgemeiner
„beliebige alte PNG akzeptieren“-Schalter.

## Komponenten und Datenfluss

1. Ein lesender Import-Vorcheck verknüpft Archiv-Master und Review-Provenienz
   mit dem ursprünglichen `experiment.json`, versiegeltem `job.json`, Workflow,
   Prompt, `run.json`, Rohbild und den drei Quellbildern. Er prüft Dateihashes,
   Scope, Seed, Modell-/Encoder-/VAE-Hashes, Referenzmodus und die tatsächliche
   2,0-MP-/300-dpi-Verarbeitung. Fehlende oder widersprüchliche Belege
   führen zu einem begründeten Stopp, nicht zu geratenen Ersatzwerten.
2. Ein eigener historischer Vertragsdatensatz benennt Schema und
   Implementierungs-/Promptversion des Versuchs. Er bindet alle genannten
   Eingaben sowie den akzeptierten Master und hält die frühere
   `experimental_prompt_override`-Kennzeichnung sichtbar. Er behauptet
   weder einen neuen GPU-Lauf noch die aktuelle v11-Prompt-Topologie.
3. Eine eng begrenzte Promotionsschnittstelle prüft diesen historischen
   Datensatz zusätzlich zu den bestehenden Pixel-, Quellen-, Layout- und
   Overlay-Gattern. Der produktive Scope hat danach genau **einen** aktiven
   Generierungsvertrag. Es gibt keinen parallelen Alt-/Neu-Routingpfad.
   Archiv und gesicherte Vorgänger bleiben für den Vergleich erhalten.
4. Die deutsche Überlagerung wird deterministisch aus dem unveränderten
   textfreien Master erstellt. Für `Base1` ist das bisherige englische
   `TRADING CARD GAME` im Logo keine mitfreigegebene deutsche Fassung. Vor
   Aktivierung wird eine authentische deutsche Logoquelle mit Herkunft,
   Dateihash und visueller Kontrolle beschafft. Eine unbelegte englische oder
   künstlich umbeschriftete Grafik zählt nicht als Lösung. Lässt sich keine
   tragfähige deutsche Quelle belegen, bleibt nur `Base1` gesperrt; ExGen3
   wird unabhängig weiterbearbeitet.
5. Nach bestandener Scope-Validierung wird `pdf.enabled` nur für den jeweils
   geprüften Poster aktiviert. `Base1` und das ExGen3-Aggregat werden als
   deutsche Ziel-PDFs gebaut; bei ExGen3 muss die aktive normale Sektion
   erhalten bleiben und die Mega-Sektion an ihrer vorgesehenen Stelle
   erscheinen. Ziel-PDFs entstehen zunächst als neue Prüfdateien. Bestehende
   Original- oder Release-Dateien werden erst nach vollständiger Prüfung
   durch klar benannte neue Ausgaben abgelöst.

## Fehler- und Freigabeverhalten

- Ein Archiv-Master darf nur übernommen werden, wenn sein Hash bytegenau
  stimmt und die erzeugten Produktionspixel mit den akzeptierten Pixeln
  identisch sind. Eine neue PNG-Kompression darf keine Pixeländerung
  verbergen.
- Alte `run.json`-/Log-/Job-Belege bleiben unverändert und werden nicht als
  „jetzt neu gerendert“ ausgegeben. Private Worker-Konfigurationen, Hosts,
  Aliase, Pfade und heruntergeladene Quellen bleiben außerhalb von Git und
  Berichten.
- Ein Fehler an einem Scope blockiert nur dessen neue PDF; der andere Scope
  kann separat bestehen. Kein Prüfskript deaktiviert Qualitätsgatter, um die
  Promotion zu erzwingen.
- Ein technisch gültiger Import erweitert die damalige Nutzerfreigabe nicht.
  Der fehlende schwarze Augendetailpunkt bei ExGen3 C bleibt ausdrücklich
  eine für **dieses** Bild akzeptierte Abweichung.

## Prüfplan und Definition von fertig

- Negativtests lehnen manipulierte Master, fehlende Jobs/Quellen,
  Scope-/Seed-/Prompt-/Modellhash-Mismatch und falsche historische
  Vertragsversion ab. Bestehende moderne Promotions- und Planner-Tests
  bleiben grün; alle übrigen Poster bleiben byte- beziehungsweise
  pixelgleich zum Ausgangsstand.
- Die beiden textfreien Master, Rohbilder, deutsch überlagerten Panoramen,
  neun tatsächlichen 750 × 1050-px-Einleger je Motiv und alle verwendeten
  Quellbilder werden erneut visuell geprüft. Besonders Kartenränder,
  Anatomie, Augen, Bodenkontakt, Schrift und Logos werden protokolliert.
- Die neu gebauten deutschen PDFs werden seitenweise gerastert. Posterposition,
  vollständige neun Schnittkarten, Panorama-Seite, Seitenfolge,
  Schnittlinien, Sprache und Logo werden geprüft. Eine komplette
  ExGen3-Ausgabe darf nicht durch ein künstliches Deckblatt oder Auslassen
  der normalen Sektion ersetzt werden.
- Das Ergebnis nennt konkrete PDF-Dateien, Prüfsummen, Umfang und bekannte
  Einschränkungen. Erst dann gilt die technische PDF-Aktualisierung für den
  jeweiligen Scope als fertig; Veröffentlichung oder Gesamt-v10-Freigabe ist
  ein getrenntes Gatter.

## Nichtziele

Keine neue Bildgenerierung für diese zwei akzeptierten Master, keine Änderung
des Standard-One-shot-Modus, keine Reparatur anderer Panoramen und kein
ungeprüfter Gesamt-Release. Der getrennte P16/P37-Fallback steht in einer
eigenen Spezifikation.
