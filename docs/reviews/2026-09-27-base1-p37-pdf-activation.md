# Base1 und ME03: ausdrücklich freigegebene deutsche Panoramen in lokalen PDFs

Stand: 27.09.2026. Dieser Bericht belegt die beiden nachträglichen Einzelentscheidungen und den lokalen PDF-Austausch; er ist **keine Freigabe des gesamten v10-Releases**.

## Entscheidungen und unveränderte Bildquellen

- `Base1`: Der bereits historisch freigegebene und technisch übernommene B-Master bleibt bytegleich (`d06f69eb6e010b2670987a2209d3aec50848ac694aaefec64dc70d342ce0d9b4`). Der Nutzer akzeptierte das echte deutsche Pokémon-Sammelkartenspiel-Logo mit seiner bekannten 250-px-Quellenbreite ausdrücklich für dieses historische Set. Die Auflösungsgrenze wird nicht als neues scharfes Logo ausgegeben und nicht auf andere Sets übertragen.
- `ME03`/P37: Der Nutzer gab Kandidat A nach Gesamtbild und allen drei Einleger-Quellbild-Paaren ausdrücklich frei. Der übernommene Master hat unverändert SHA-256 `fc1df7acd8359153d53eabbaf23c22a189dbc8d694e58ed5cd8a7c3b683e7b76`; die deutsche Vorschau ist bytegleich zum geprüften Kandidaten. Serpifeu, Bauz und Mega-Zygarde bleiben vollständig auf ihren Karten. Der separate [Run- und Pixelnachweis](2026-09-27-p37-identity-lock-review.md) bindet Originaljob, Upscale und 54.082 unveränderte Quellpixel. `identity_lock/two_pass_source_pixels` gilt nur für diesen bislang gescheiterten Scope; der übrige One-shot-Standard bleibt unangetastet.

## PDF-Prüfung vor dem Austausch

Für beide Sets wurden mit den konfigurierten Logoquellen zuerst **separate** deutsche Prüffassungen mit neun Einlegern und mit Vollseitenpanorama gebaut. Alle Seiten beider Einlegervarianten wurden gerastert und als Kontaktbogen geprüft; die Panoramaseiten zusätzlich einzeln bei 200 dpi. Die neun physischen Motivausschnitte pro Panorama sind in der PDF als 750 × 1050 px bei 300 dpi eingebettet. Die Vollseiten-PDFs enthalten jeweils ein 2368 × 3268-px-Panorama bei 300 dpi. Zwischen Einleger- und Vollseitenmodus ist nur Seite 1 verschieden; jede andere Seite ist bei 72 dpi pixelgleich. Logos, Schnittlinien, Kartenreihenfolge, Seitenwechsel und Infokarten zeigten in dieser Prüfung keine neue Überschneidung oder Abschneidung.

| Scope | Nummerierte Karten | A4-Seiten | Infokarte | alter lokaler PDF-SHA-256 | neuer lokaler PDF-SHA-256 |
| --- | ---: | ---: | ---: | --- | --- |
| `Base1` | 102 | 14 | 14 | `6e9de2598de286444838b3b66647cc7c793a72128fb68fe935d8b8f2f1b3aecc` | `f7e6b72b8414be424d0f827ec26a75273943e164ed3409268e831bbd3c7ba8ec` |
| `ME03` | 124 | 16 | 16 | `7adc6723a3b8862c515208fbc8cade0559f2cd19e9dc93c28cba525b3d10ad95` | `e0ecd710a72cc8c340035fe7264c011af2c02f26a55b0a0aa740bcdd4201bfbc` |

Erst nach dem visuellen Prüfbau wurden die regulären Dateien `output/de/Base1_DE.pdf` und `output/de/ME03_DE.pdf` neu erzeugt. Das 72-dpi-Raster **jeder** regulären Seite ist pixelgleich zu ihrer vorab geprüften Einleger-PDF. Die alten Dateien sind nur in ignorierten lokalen Prüfverzeichnissen gesichert; weder diese Sicherungen noch Quellcaches/Renderjobs werden versioniert. Die generierten PDF-Dateien bleiben nach der bestehenden Projektregel ignorierte lokale Artefakte. Weitere v10-Daten-, Artwork- und Release-Gates bleiben unabhängig offen.

Nach Anpassung der Release-Routen bestanden die beiden gezielten Testdateien mit 131 Tests; nach Ergänzung des Dschungel-Logo-Regressionstests meldete die vollständige Projektsuite **972 bestanden, 1 übersprungen**. Alle 40 aktivierten Master wurden zusätzlich mit `validate_promoted_poster.py` bestätigt.

## Release-Build: Dschungel-Logo ohne Bildänderung absichern

Der bereits vor diesem Austausch laufende PR-Release-Build meldete bei `Base2` einen Dateihash-Unterschied der heruntergeladenen, freigegebenen Logoquelle. Der lokale Neudownload ergab nach der projektüblichen PNG-Normalisierung erneut den freigegebenen Dateihash. Da PNG-Dateibytes je nach Auslieferung und Codierung variieren können, prüft die dauerhafte Freigabe nun zusätzlich den Hash der **dekodierten RGBA-Pixel einschließlich Bildabmessungen**. Eine nur anders codierte, visuell gleiche Quelle ist zulässig; jede Pixelabweichung bleibt ein Fehler. Der akzeptierte Dateihash und die Vorschau-Freigabe bleiben unverändert. Ein Test deckt beide Fälle ab. Die Aussage, dass der Remote-Build damit wieder grün ist, setzt dessen erneuten Lauf voraus.
