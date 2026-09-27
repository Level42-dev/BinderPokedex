# ExGen3: quellengetreuer Schattenpass

Stand: 13. September 2026. Design, Implementierung und unabhängige Codeprüfung
sind abgeschlossen. Der erste Pilot ist vollständig zurückgeholt und besteht
die Pixelprüfungen, wurde aber wegen seiner Schatten verworfen. Auch die zweite,
rein textlich veränderte Variante erreicht noch keine visuelle Freigabe.

## Lösungsansatz

Zunächst entsteht eine zusammenhängende Landschaft. Darin werden die exakt
ausgewählten Originalfiguren an ihren vorgesehenen Positionen eingesetzt.
Dieser Zustand wird zusätzlich als unverändertes Vergleichsbild gespeichert.

Ein zweiter Durchlauf sieht Landschaft und Figuren, darf im Ergebnis aber nur
kleine, vorher geprüfte Bodenflächen verändern. Bei Lucario sind das die
Kontaktbereiche unter beiden Füßen und der anschließende Körperschatten.
Bei Latias und Diancie sind es getrennte Schattenprojektionen, die ihre
schwebende Position verständlich machen. Die Beleuchtung kommt wie in der
bisherigen Landschaft von links oben.

Alle Figurenpixel einschließlich teiltransparenter Randpixel sind von der
Maske ausgeschlossen. Außerhalb der Maske wird das Vergleichsbild exakt
wiederhergestellt. Die bisherige großflächige obere Überblendung entfällt in
diesem neuen Verfahren; sie war für die doppelten Landschaftskonturen
verantwortlich und kann ohnehin keine Schatten unter den Figuren ergänzen.

## Vorteile und Grenzen

| Vorteil | Grenze beziehungsweise Aufwand |
| --- | --- |
| Die KI zeichnet die Figuren im Rohbild nicht neu; Stacheln, Ohren, Augen und Formen bleiben überprüfbar erhalten. | Posen, Blickrichtung und Beleuchtung der Originalfiguren sind damit weitgehend festgelegt. |
| Veränderungen bleiben auf freigegebene Bodenflächen beschränkt und sind pixelgenau messbar. | Gute Schatten sind nicht allein durch einen bestandenen Pixeltest bewiesen; Richtung, Bodenkontakt und Übergänge brauchen eine Sichtprüfung. |
| Ein gutes Landschaftsbild muss nicht wegen einer misslungenen Figur komplett neu erzeugt werden. | Das Zusammensetzen kann weiterhin aufgelegt wirken, etwa bei stark abweichendem Licht oder Stil. Der Pilot muss zeigen, ob die Einbindung genügt. |
| Quellen, Masken, Parameter und Bilder bleiben über Prüfsummen nachvollziehbar. | Jedes Motiv benötigt sinnvolle Kontakt-/Projektionspunkte. Eine pauschale Schattenellipse unter jeder Figur reicht nicht. |
| Der frühere obere Mischbereich entfällt. | Der zusätzliche lokale Edit gegenüber einer reinen Einsetzung benötigt Rechenzeit; die Druckvergrößerung kann neue Details verändern und wird erneut geprüft. |

Die Pixelgarantien beziehen sich auf das Rohbild vor der vorhandenen
modellbasierten Druckvergrößerung. Deshalb müssen auch der 300-dpi-Master und
alle neun physischen Kartenfelder gegen die Originalquellen bestehen.

## Bisher geprüft

- Die genaue Auswahl ist Mega-Latias, Mega-Diancie und Mega-Lucario; alle drei
  Originaldateien wurden erneut betrachtet.
- Auf dem Rohbild mit 848 × 1168 Pixeln liegen die Figuren vollständig im
  unteren Kartenband. Lucarios zwei Sohlenkontakte wurden anhand der
  tatsächlichen Alpha-Pixel bestimmt, nicht aus der Mitte seiner Bilddatei.
- Der vorhandene Render-Worker und die vier benötigten Modellartefakte sind
  erreichbar; ihre Prüfsummen entsprechen den festgelegten Versionen.
- Die bestehende fokussierte Identity-Lock-Testsuite besteht vor der Änderung:
  7 Tests erfolgreich.
- Die neue Masken- und Pixelprüflogik besteht 34 fokussierte Tests und eine
  unabhängige Prüfung. Dabei wurden ein harter Maskenrand, ein Rundungsfall bei
  Ankerpunkten und zu schmale Schattenbereiche gezielt abgesichert.
- Die endgültig vorbereitete ExGen3-Maske erlaubt Änderungen an 18.400 Pixeln
  (rund 1,86 Prozent des Rohbildes) und schützt alle 54.119 sichtbaren
  Figurenpixel.
- Die Renderer-/Metadatenintegration einschließlich Druckmaster-Austauschtest
  ist unabhängig geprüft. Ein frischer fokussierter Lauf umfasst 112
  erfolgreiche Tests.
- Beim Abgleich mit echten zurückgeholten Worker-PNGs wurde zusätzlich die
  ComfyUI-Cache-Anmerkung `is_changed` erkannt und bis zu ihrem Ursprung im
  installierten Renderer verfolgt. Sie enthält die jeweilige Eingabe-Prüfsumme;
  der eigentliche Renderplan ist unverändert. Die eng begrenzte gemeinsame
  Vergleichskorrektur und der sichere Pilot-Jobhelfer haben die unabhängige
  Codeprüfung ohne offene Befunde bestanden.
- Der vollständige lokale Testlauf am stabilen Code-Stand `2f918b0` ergab 814
  erfolgreiche, drei fehlgeschlagene und einen übersprungenen Test sowie vier
  erfolgreiche Untertests. Die drei
  Fehler hängen an den zurückgenommenen Bestandsfreigaben; zusätzlich meldet
  ReportLab eine bestehende Veraltungswarnung. Das ist ausdrücklich kein
  grüner Release-Nachweis.
- Der erste unveränderlich vorbereitete Versuch heißt
  `audit-exgen3-mega-grounded-v4-260751036`. Vor dem Start wurden beide
  gespeicherten Ausgaberollen, die normale VAE-Kodierung mit lokaler
  Rauschmaske, das Fehlen der alten oberen Überblendung und die exakten
  Quell-/Masken-Prüfsummen geprüft. Der Job wurde einmalig ausgeführt und samt
  aller Bilder und Protokolle zurückgeholt. Das gibt das Bild noch nicht frei.

## Erstes tatsächliches Ergebnis

Rohbild: 848 × 1168 Pixel. Geändert wurden 18.153 erlaubte Bodenpixel, **kein**
sichtbarer Figurenpixel und **kein** Pixel außerhalb der erlaubten Maske.
Die unveränderte Vergleichsausgabe wurde separat gespeichert. Der Renderlauf
benötigte rund 93 Sekunden; die anschließende Modellvergrößerung rund 6 Sekunden.

Der Druckmaster besitzt 2368 × 3268 Pixel; die neun Kartenfelder jeweils
750 × 1050 Pixel. Alle Ausschnitte stimmen pixelgenau mit den vorgesehenen
Vorschau-Rechtecken und den gespeicherten Prüfsummen überein. Die Kandidaten-PNGs
haben noch keinen DPI-Metadatenwert; die normale Übernahme in den Produktionspfad
ist nicht erfolgt. Es handelt sich um Druckgröße in Pixeln, nicht um eine bereits
freigegebene Druckdatei.

Die Hauptprüfung hat alle drei Originalfiguren, beide Rohbilder, den gesamten
Master und die lokalisierte Vorschau sowie alle neun einzelnen Kartenfelder
tatsächlich betrachtet. Der vollständige Master wurde in der Anzeige verkleinert,
die Kartenfelder dagegen mit nativen 750 × 1050 Pixeln geprüft. Die Originaldetails
der Figuren sind erhalten. Die unabhängige Beurteilung bestätigt Anatomie und
Kartencontainment, verwirft aber Diancies kantige Schattenprojektion und
Lucarios abgesetzt wirkenden Sohlenkontakt über einer verschmierten dunklen
Fläche. Latias' Einbindung bleibt unklar. Der vollständige Bericht steht in
[`2026-09-12-exgen3-grounded-pilot-1.json`](2026-09-12-exgen3-grounded-pilot-1.json).

Der zweite Versuch veränderte ausschließlich den Wortlaut der Schattenanweisung:
diffuse, kontrastarme Projektionen für die schwebenden Figuren und enge
Kontaktschatten unmittelbar unter den Sohlen. Seed, Originalfiguren, Positionen,
Masken, Übergangsbreite und Modelle bleiben identisch. So lässt sich der Effekt
dieser einen Änderung beurteilen; der erste Versuch bleibt unverändert erhalten.
Beide Vergleichsbilder vor dem Schattenpass sind tatsächlich pixelgleich.
Die zweite Ausgabe verändert 18.272 erlaubte Bodenpixel und wiederum keinen
Figurenpixel oder Pixel außerhalb der Maske. Ihr Master hat die Prüfsumme
`a556ea3da2349b00f5973e3900fa23f125b200b261b1bf89fd31df2b4d857a6d`.

Die vollständige unabhängige Prüfung bestätigt weichere Schatten, aber die
gleichen wesentlichen Fehler: Diancies Spitzen/Kerbe, Lucarios abgesetzte
Sohlenränder und einen weiterhin unklaren Latias-Schatten. Anatomie und
Kartencontainment bestehen. Siehe
[`Prüfbericht zum zweiten Versuch`](2026-09-13-exgen3-grounded-pilot-2.json).

Als dritte und letzte kontrollierte Variante dieses Mechanismus wird ein
breiterer, nach innen weich auslaufender Maskenrand geprüft. Eine Änderung der
Maskengeometrie, des Seeds oder des Quellschutzes ist damit nicht verbunden.

Die geometrische Vorprüfung mit `feather_ratio: 0.012` besteht: Alle Figuren
bleiben geschützt und jede Region behält einen voll wirksamen Kern. Allerdings
würde der linke Sohlen-Anker schwächer gewichtet (209 statt 255). Das wurde nur
in isolierten Diagnosemasken untersucht; die Produktionskonfiguration bleibt
bei 0.004. Es existiert kein dritter Render.

### Neue Freigabegrenze des Nutzers

Am 13. September hat der Nutzer ausdrücklich verlangt, zuerst ein finales
Einzelbeispiel zu sehen, bevor weitere Bilder erzeugt werden, und den weiterhin
möglichen Eindruck hart eingesetzter Figuren angesprochen. Deshalb werden
vorerst keine neuen Render gestartet. Der zweite Versuch wird offen als
**verworfener Teststand** gezeigt, nicht als fertiges Produkt. Ein visuell
freigegebenes ExGen3-Beispiel liegt weiterhin nicht vor. Seriengenerierung,
Übernahme und neue PDFs/Archive bleiben ausgesetzt.

| Datei | SHA-256 |
| --- | --- |
| Vergleich vor Schattenpass | `3b4047623aed57ded1ec674b86e0b0fdf3bc09f87c4af67328ac137a17760355` |
| Rohbild nach Schattenpass | `c4286bae6c7ab9a2fe109fbba105340a83de35f70ab13f8ea38b2db25950f765` |
| Druckgroßer Master | `0461fb5d646b0fab5cd07e58f87be643be608f48035141a66e2fa19eb3023533` |
| Deutsche Vorschau | `f42cc15c4cc6005c85c0016ce463d6cef521a330b10562429ca56ec9107a1100` |

## Freigabefolge

1. Maskenlogik, Quellschutz, Metadaten und Fehlerfälle automatisiert prüfen.
2. Die tatsächlich erzeugten Masken vor dem Rendern visuell abgleichen.
3. Rohbild und Vergleichsbild vollständig zurückholen; Quellpixel und
   Änderungen außerhalb der Maske prüfen.
4. Schatten, Anatomie, Druckmaster und jedes der neun Kartenfelder prüfen;
   zusätzlich unabhängige Gegenprüfung.
5. Erst nach einem bestandenen ExGen3-Prototyp weitere Figurenkonstellationen
   testen. Ein bestandener Prototyp gibt die anderen Panoramen nicht frei.

Die alten 41 beanstandeten Freigaben bleiben zurückgenommen. Vorhandene
Produktbilder, PDFs und Archive werden durch diesen Versuch nicht ersetzt.
