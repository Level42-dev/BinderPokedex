# P02: belegbare Fallback-Promotion und deutsches Erscheinungsdatum

Stand: 25.09.2026. Der Nutzer hat die Richtung des Entwurfs bestätigt. Dieses
Dokument ist die zu prüfende Spezifikation; es ist weder eine Implementierung
noch eine Freigabe der lokalisierten PDF.

## Ziel und Grenzen

Das bereits angenommene textfreie P02-H-Panorama wird ohne erneute Generierung
und ohne Pixeländerung in den bestehenden Freigabeweg übernommen. Die
Freigabe soll wahrheitsgemäß zeigen, dass es aus einem FLUX.2-One-shot und
zwei begrenzten, maskierten Vordergrund-Korrekturen besteht. Der normale
`joint_scene`-One-shot bleibt der Standard. Ein maskierter Fallback wird nie
automatisch gewählt und darf nicht als reiner One-shot ausgegeben werden.

Die deutsche P02-Infokarte soll `Juni 2000` statt `16. Juni 1999` zeigen.
Ein bestimmter deutscher Erscheinungstag wird ohne belastbaren Nachweis nicht
erfunden. Die globale TCGdex-Angabe `1999-06-16` bleibt als Datum der
ursprünglichen Setdaten erhalten; nur die deutsche Poster-Einblendung wird
lokalisiert. P02 bleibt bis zur Prüfung der neuen Einblendung und der
Druckausgabe aus der PDF-Route ausgeschlossen.

Die bestehende Zustimmung zu H gilt für den textfreien Master mit SHA-256
`26d6a468e59b7dd1ea21931d85ae016ed220324d23eee1fd8aacb642001a07f6`.
Die Zustimmung zum historischen `JUNGLE`-Logo gilt für die in
`assets/review-pending/p02-h/review-provenance.json` gebundenen Logo- und
Vorschau-Hashes. Keine dieser Zustimmungen wird auf einen neuen Bildinhalt,
ein anderes Logo oder eine geänderte Infokarte übertragen.

## Befund und Entscheidung

Der bestehende Promoter erwartet ein Kandidaten-`run.json`, dessen
Generierungsvertrag genau dem Manifest entspricht, sowie einen visuellen
Vergleich zum rohen One-shot. P02-H ist kein solches Einzelresultat. Das
aktuelle P02-Manifest beschreibt zudem einen älteren 1-MP-Lauf; die
One-shot-Basis von H wurde mit 2 MP und anderer Referenzführung erzeugt.
Ein bloßes Kopieren von H in den produktiven Pfad würde die bisherigen
Provenienzprüfungen umgehen oder falsche Metadaten erfordern.

Zwei Alternativen werden verworfen: Ein statischer Sonderfall nur für P02
wäre leicht zu veröffentlichen, ließe sich aber nicht mit demselben
Freigabeprüfer auditieren. Ein weiterer One-shot würde das bereits
angenommene Motiv ersetzen und neue Bildfehler riskieren. Stattdessen
bekommt der vorhandene Promoter einen ausdrücklich gekennzeichneten,
allgemein prüfbaren **maskierten Fallback-Vertrag**. Dieser Vertrag wird
zunächst ausschließlich an P02-H eingesetzt.

## Eingaben und Herkunftskette

Die Promotion verlangt die vorhandenen, ignorierten Originalartefakte:
One-shot-A-Run und textfreien Basis-Master, beide lokalen Reparatur-Jobs samt
`run.json`, `comfyui.log`, Ausgabebildern und Masken, den zusammengesetzten
H-Master sowie die hashgebundene menschliche Bildfreigabe. Ein fehlendes oder
abweichendes Artefakt beendet die Promotion vor jeder Dateiersetzung.
Remote-Rechnernamen, private Pfade und Zugangsdaten gehören weder in den
Job-Nachweis noch in die Git-Provenienz.

Der Manifest-Generierungsblock muss den **wirklichen** One-shot A (2 MP,
Seed, Referenzmodus und Modell-/Encoder-/VAE-Hashes) beschreiben. Der
Quellenfingerprint bleibt in den A-Laufmetadaten und wird dagegen geprüft.
Der Block darf nicht durch Umbenennung von H in ein One-shot-Resultat
scheinbar passend gemacht werden. Wenn die eingefrorenen A-Eingaben heute
nicht gegen das aktuelle Manifest und die reproduzierbaren Quellassets
validiert werden können, bleibt P02 deaktiviert; der Unterschied wird
dokumentiert, nicht durch eine erfundene Fingerprint-Gleichheit übergangen.

Ein neuer Provenienzabschnitt `composition` beschreibt:

- `kind: masked_fallback` und den Hash des Basis-Masters samt A-Run und
  Generation-Fingerprint;
- pro Reparatur den Grund, getrennte Hashes für `run.json`, `comfyui.log`,
  Jobbeschreibung, rohes Ergebnis und Editiermaske, die Maskenlage im
  Gesamtpanorama sowie die Zahl der innerhalb und außerhalb geänderten Pixel;
- den Hash des zusammengesetzten Masters, die Vereinigungsmaske und den
  nachgewiesenen unveränderten Bereich;
- die konkrete menschliche Annahme von H und die getrennte Logo-Annahme.

Die beiden P02-Reparaturen beginnen unabhängig von A und liegen in
verschiedenen Karten. Deshalb prüft die Promotion ihre Masken auf
Nichtüberlappung und setzt nur Pixel aus der jeweiligen Maske zusammen.
Die vollständige 300-dpi-H-Bildfläche wird gegen A verglichen. Für P02-H
müssen 10.548 veränderte Pixel innerhalb von 11.121 editierbaren Pixeln
liegen; außerhalb der Vereinigungsmaske müssen es **null** sein. Die sieben
anderen physischen Einleger bleiben pixelgleich zu A. Diese Zahlen sind
Erwartungen an genau H, keine pauschalen Grenzwerte für spätere Projekte.

Für spätere Prüfung ohne die ignorierten Renderdateien enthält die
Git-Provenienz eine kompakte, deterministische Kodierung der beiden Masken
in 300-dpi-Gesamtbildkoordinaten und einen Pixel-Digest des unveränderten
Außenbereichs von A. Der Promoter berechnet diesen Digest aus dem echten
A-Master und vergleicht ihn mit H. Der spätere Validator dekodiert dieselbe
Maske und berechnet den Außenbereichs-Digest des beförderten Masters erneut.
Damit kann er Drift am beförderten Bild erkennen; eine unabhängige
Neuberechnung des historischen A-Digests ohne A-Datei ist nicht vorgetäuscht.
Die Artefakt-Hashes und der bei der Promotion geprüfte Auditbefund bleiben
die nachvollziehbare Herkunft von A und den beiden Reparaturen. Ins Repo
kommen wie bisher nur der geprüfte textfreie Master und seine Provenienz,
nicht die heruntergeladenen Cutouts, Logos oder temporären Renderdateien.

## Validator, Fehlerverhalten und Rückwärtskompatibilität

Der Promoter prüft den neuen Abschnitt **vor** der transaktionalen
Ersetzung von Master und Provenienz. Die normale One-shot-Promotion und
bestehende Provenienzversionen bleiben unverändert gültig. Nur ein explizit
als `masked_fallback` gekennzeichneter Kandidat benutzt den zusätzlichen
Pfad; ein stiller Fallback bei gescheiterter One-shot-Prüfung ist verboten.

Der Release-Validator akzeptiert eine neue Provenienzversion nur mit
vollständigem Kompositionsnachweis. Er prüft Format und Dimensionen der
Maskenkodierung, zulässige Gesamtbildkoordinaten, nicht überlappende
Reparaturflächen, die Hashes des beförderten Masters, seinen unveränderten
Außenbereich, den an das Manifest gebundenen A-Fingerprint und die getrennten
Freigaben. Fehlende Hashes, fremde Maske, ein Pixel außerhalb der Maske,
Quell- oder Manifestdrift und ein nicht freigegebenes Overlay sind harte
Fehler. Eine bloße JSON-Behauptung `changed_outside_mask_pixels: 0` reicht
nicht aus.

## Deutsche Datumsanzeige

Die Poster-Konfiguration kann für `set_summary` unter
`text_content.release_date_overrides.<sprache>` einen sprachgebundenen
Erscheinungszeitpunkt mit `value` und `precision` (`month` oder `day`)
angeben. Für `Base2/de` stehen dort `value: 2000-06` und
`precision: month`; die Infokarte rendert exakt
`Juni 2000`. Andere Sprachen behalten zunächst das bisherige globale Datum.
Ungültige Formate oder eine Monatsangabe, die heimlich als konkreter Tag
formatiert wird, werden abgelehnt. Der lokalisierte sichtbare Text und die
Konfiguration gehen in den bestehenden Overlay-Fingerprint ein. Diese
posterbezogene Korrektur schreibt den importierten globalen Datensatz nicht
um; dessen irreführende deutsche Beschreibung bleibt eine gesonderte
Datenpflegefrage und darf nicht als korrigiert gemeldet werden. Die
Monatsangabe für die deutsche Ausgabe stützen unabhängig voneinander
[Bisafans](https://www.bisafans.de/sammelkarten/sets/klassisch/dschungel.php)
und [PokéPrinz](https://pokeprinz.de/en/blogs/set-guides/pokemon-dschungel).

## Prüfung und Freigabe

1. Red/Green-Tests prüfen den neuen Provenienzpfad mit echten P02-H-Hashes
   sowie künstlichen Fällen: Maske verschoben, ein Außenpixel verändert,
   reparierte Bereiche überlappen, Job-/Basis-Hash fehlt, falscher Seed und
   unerlaubter stiller Fallback. Bestehende One-shot-Tests bleiben grün.
2. Datumstests prüfen `Base2/de` als `Juni 2000`, unverändertes Englisch,
   präzise Tagesdaten anderer Sets und Ablehnung fehlerhafter Overrides.
   Ein geänderter deutscher Text muss den Overlay-Fingerprint ändern.
3. Die technische Master-Promotion kann vor der noch ausstehenden
   Overlay-Freigabe stattfinden, aber nicht die PDF-Route aktivieren. Aus dem
   unveränderten H-Master und dem freigegebenen Logo entsteht eine neue
   deutsche Vorschau. Der volle Bogen und alle neun physischen
   750 × 1050-px-Einleger werden visuell auf Logo, Datum, Schnittkanten,
   Text und Pokémon geprüft. Besonders die Info-Karte r2c2 wird dem Nutzer
   für die noch ausstehende Overlay-Freigabe gezeigt.
4. Erst nach dieser Freigabe und bestandener Validierung wird `pdf.enabled`
   aktiviert. Weil diese Route alle betroffenen Sprachen betrifft, werden
   auch deren Titel- und Info-Einleger vor dem Umschalten geprüft. Der
   tatsächliche PDF-Build wird gerendert und seitenweise bzw. an allen neun
   Panoramaflächen kontrolliert; ein erfolgreicher Befehl allein genügt
   nicht. Fehler lassen den bisherigen deaktivierten P02-Zustand stehen.

Für diese Arbeit ist **kein neuer GPU-Lauf** vorgesehen. Sollte ein
erforderliches historisches Job-Artefakt fehlen oder der A-Fingerprint
nicht ehrlich reproduzierbar sein, endet der Versuch vor der Promotion mit
einem konkreten Befund. Die bestehende PDF und alle anderen Panoramen bleiben
unverändert.
