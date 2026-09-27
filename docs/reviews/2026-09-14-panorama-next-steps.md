# Panorama-Neubewertung und nächster Arbeitsplan

Stand: 14.09.2026. **Prüf- und Planungsergebnis, keine neue Generierung und keine Veröffentlichung.**

## Ergebnis der erneuten Sichtung

Alle 40 noch offenen Panorama-Ziele und ihre 119 Figuren wurden erneut gegen die tatsächlichen Quellbilder und physischen Kartenausschnitte betrachtet, aufgeteilt auf vier Agenten. Bei Dschungel wurde Fassung E betrachtet; die acht nicht zu Pikachu gehörenden Karten sind weiterhin unverändert. Dies ist eine vollständige Ziel-/Figurentriage, keine vollständige Rohbild-, Neun-Karten-, Logo- oder PDF-Druckfreigabe.

| Empfehlung | Anzahl | Bedeutung |
| --- | ---: | --- |
| Neuer gemeinsamer One-Shot | 36 | Mindestens ein klarer Figuren-/Identitätsbefund; darunter Dschungel mit gesondertem Teilfreigabe-Vorbehalt |
| Direkt zur Nutzerbewertung | 3 | P03 Dunkelnacht, P10 Pokédex Generation VII, P27 Stürmische Funken; kleine Unterschiede offenlegen |
| Erst genauer beurteilen | 1 | P06 Pokédex Generation III; kein sicherer reiner Halmfehler |
| Sicher nur lokale Tiefenreparatur | 0 | In dieser Gegenprüfung kein weiterer eindeutig belegter Fall |

Die zwei freigegebenen vollständigen Versuchsmotive **ExGen3 Mega C** und **Basis-Set B** bleiben separat erhalten. Die Freigabe für **Pikachu in Dschungel E** bleibt eine Teilfreigabe. Keine davon wurde auf andere Figuren übertragen oder technisch in die Produktion übernommen.

[Erste überschaubare Freigaberunde mit Quellenpaaren](2026-09-14-panorama-shortlist.md) · [Hashgebundene Neubewertung aller 40 Ziele](2026-09-14-panorama-retriage.json)

## Was der neue Flow wirklich bewiesen hat

**One-Shot:** Die akzeptierten ExGen3-C-/Basis-Set-B-Versuche geben eine gemeinsame Positionsvorlage und je ein individuelles Original-Detailbild in einen gemeinsamen Szenenlauf. Anzahl und Kartenpositionen haben Vorrang, die kleinen Figuren bekommen konkrete Quellmerkmale und 2 MP tatsächliche Generierungsauflösung. Landschaft und Pokémon entstehen gemeinsam; keine nachträglich eingeklebten Figuren. Anschließend nur deterministische Druckaufbereitung.

**Optionale Nacharbeit:** Dschungel E belegt, dass zwei eng geführte Landschaftskonturen mit einer maskierten generativen Angleichung plausibel vor Pikachu weiterlaufen können. Das war agentengeführte Konturanalyse, kein allgemeiner automatisch funktionierender Tiefendetektor. Diese Nacharbeit behebt keine fehlenden Zähne, falschen Formen oder umgezeichneten Gesichter. Sie darf bestehende Anatomiefehler auch nicht unter Vegetation verstecken.

Bei P06 wurde die anfängliche Annahme eines stumpf abgeschnittenen Blatts ausdrücklich gegengeprüft: Hydropis Blatt kann ebenso eine natürliche verjüngte Spitze mit ungünstiger Tangente besitzen. Der Erstprüfer hat den Befund deshalb auf **unklar** korrigiert. Hier wird nicht vorsorglich darübergezeichnet.

## Empfohlene Reihenfolge

1. **Erfolgreichen One-Shot sauber zum gemeinsamen, versionierten Renderer-Vertrag machen.** Aktuell stehen die drei geplanten Pilotmanifeste noch auf 1 MP und der Standardprompt vermeidet weiterhin Vordergrundüberschneidungen. Deshalb nicht einfach die alte Batch-Funktion erneut starten. Die akzeptierte Positions-/Detailreferenzierung, 2-MP-Auflösung, exakte Figurenanzahl und erlaubte natürliche Überdeckung müssen zentral nachvollziehbar abgebildet werden. Historische Jobs bleiben reproduzierbar; alte Prüfsiegel werden nicht passend umetikettiert.
2. **Als erstes neues Beispiel P01 – Stellarkrone erzeugen.** Schwerpunkt Hopplos Auge, Zahn und zwei Halsflecken sowie Bisasams Pfotenzeichnung. Vor weiteren Motiven das neue Gesamtbild und alle drei Karten-/Quellpaare prüfen und vorlegen.
3. **Danach zwei anspruchsvollere Übertragungsproben:** P15 – Mega-Pokémon EX (exakte Sonderformen, Kopf-/Flügelzeichnung) und P40 – Pokémon ex (Koraidon/Miraidon, komplexe Anhänge und Körperzeichnung). Diese drei Piloten decken unterschiedliche Fehlerklassen ab; ein Erfolg allein belegt noch keine Verlässlichkeit für alle übrigen Sets.
4. **Erst anschließend die übrigen klaren Fehlerfälle in kleinen Prüfgruppen bearbeiten.** Jeweils die aus dem Quellenvergleich bekannten Merkmale im Brief hervorheben, pro Versuch nur einen belegten Einfluss ändern. Nach höchstens drei materiell unterschiedlichen Versuchen für dieselbe weiterhin gescheiterte Bedingung neu entscheiden, nicht endlos Seeds tauschen oder automatisch auf Identity-Lock wechseln.
5. **Jeden neuen Kandidaten getrennt abnehmen.** Exakte Quellen und Rohbild, vollständiger Master, alle neun physischen Karten, anatomische Merkmale, Bodenkontakt und Vordergrundkontinuität kontrollieren. Nur wenn die Figuren stimmen und ein enger Landschaftsfehler übrig bleibt, kommt die optionale Kontur-Nacharbeit infrage. Vorher/Nachher und außerhalb der Maske unveränderte Pixel nachweisen. Dann erst deine dateigebundene Bildfreigabe, technische Übernahme, lokalisierte Logos, PDF- und Archivprüfung.

**Parallel ohne neue Bilder:** P03, P10 und P27 jetzt zur bewussten Nutzerentscheidung vorlegen. P02 separat mit Relaxo/Evoli abschließen; wegen der akzeptierten Pikachu-Fassung E keine automatische komplette Neugenerierung. P06 erst weiter beurteilen.

## Aufwand und Risiken

- Die One-Shot-Übertragung bewahrt natürliche Szene und Figureneinbindung und adressiert die tatsächlich sichtbaren Identitätsfehler. Sie garantiert aber keine perfekte Kopie; neue Anatomiefehler oder zusätzliche Figuren sind weiterhin möglich.
- 2 MP statt des bisherigen 1-MP-Standards gibt kleinen Figuren mehr tatsächliche Bildinformation, kostet aber Rechenzeit und Speicher. Für 36 Motive ist vor den drei Übertragungsproben noch keine belastbare Gesamtlaufzeit ableitbar.
- Eng begrenzte Landschaftsreparatur kann bereits akzeptierte Bildteile bewahren. Falsch gewählte Konturen oder Masken erzeugen aber neue Fehler. Deshalb kein pauschaler Nacharbeitslauf über jedes Panorama.
- Bestehende Bildfreigaben und kleine bewusst akzeptierte Abweichungen bleiben exakt dateigebunden. Diese Triage erteilt keine neue menschliche Freigabe.

## Sichtbare Gründe für die ersten drei Piloten

Die folgenden Paare zeigen **unveränderte Bestandsbilder**, keine neuen Ergebnisse und keine Freigabevorlagen. Sie belegen, weshalb hier One-Shot statt reiner Halmnacharbeit sinnvoll ist.

### P01 – Hopplo · r3c3

Zwei lange Ohren sind vorhanden. Das linke Auge ist jedoch zu einem winzigen, mit dem Nasenbereich verschmolzenen Fleck reduziert; der sichtbare Zahn fehlt und aus den zwei orangefarbenen Halsflecken wird ein rotes Halsband. Keine Vegetation verdeckt diese Stellen.

| Bestehender Kartenausschnitt | Tatsächlich verwendete Quelle |
| --- | --- |
| ![Hopplo – P01 – Karte](../../tmp/poster-workspaces/SV07/comfyui_poster/promotion/poster-flux2-cards/card_r3_c3.png) | ![Hopplo – P01 – Quelle](../../tmp/poster-workspaces/SV07/sources/cutouts/pokemon_813_scorbunny.png) |

[Karte in Originalauflösung](../../tmp/poster-workspaces/SV07/comfyui_poster/promotion/poster-flux2-cards/card_r3_c3.png) · [Quelle in Originalauflösung](../../tmp/poster-workspaces/SV07/sources/cutouts/pokemon_813_scorbunny.png)

### P15 – Mega-Latios · r3c3

Die helle dreieckige Flügelmarkierung ist zu einem gelb-schwarzen Auge geworden, sodass der Flügel wie ein zusätzlicher Kopf wirkt. Die Kopfspitzen sind ebenfalls geglättet.

| Bestehender Kartenausschnitt | Tatsächlich verwendete Quelle |
| --- | --- |
| ![Mega-Latios – P15 – Karte](../../tmp/panorama-audit-aggregate/ExGen2/sections/mega/card_r3_c3.png) | ![Mega-Latios – P15 – Quelle](../../tmp/poster-workspaces/ExGen2/sections/mega/sources/cutouts/pokemon_381_artwork_10063_mega_latios.png) |

[Karte in Originalauflösung](../../tmp/panorama-audit-aggregate/ExGen2/sections/mega/card_r3_c3.png) · [Quelle in Originalauflösung](../../tmp/poster-workspaces/ExGen2/sections/mega/sources/cutouts/pokemon_381_artwork_10063_mega_latios.png)

### P40 – Miraidon · r3c3

Die blitzartig verzweigten Antennen sind zu federartigen Blättern geworden. Die gezackte leuchtende Brustzeichnung wird zur glatten ovalen Scheibe mit diagonalen Linien; Auge und Kopf gehen in eine dunkle schmale Fläche über.

| Bestehender Kartenausschnitt | Tatsächlich verwendete Quelle |
| --- | --- |
| ![Miraidon – P40 – Karte](../../tmp/poster-workspaces/ExGen3/sections/normal/comfyui_poster/promotion/poster-flux2-cards/card_r3_c3.png) | ![Miraidon – P40 – Quelle](../../tmp/poster-workspaces/ExGen3/sections/normal/sources/cutouts/pokemon_1008_miraidon.png) |

[Karte in Originalauflösung](../../tmp/poster-workspaces/ExGen3/sections/normal/comfyui_poster/promotion/poster-flux2-cards/card_r3_c3.png) · [Quelle in Originalauflösung](../../tmp/poster-workspaces/ExGen3/sections/normal/sources/cutouts/pokemon_1008_miraidon.png)

## Vollständige Arbeitsliste

Historische Agentenurteile und menschliche Entscheidungen bleiben im bisherigen Register erhalten. Die folgende Spalte beschreibt die **neue Empfehlung**, nicht eine ausgeführte Maßnahme.

| ID | Motiv | Nächster Weg | Begründung |
| --- | --- | --- | --- |
| P01 | Stellarkrone | Neuer One-Shot | Neuer One-Shot empfohlen: Hopplos frei sichtbare Gesichts-/Halsmerkmale und Bisasams Pfotendetails sind verändert. Eine reine Landschaftsmaske kann diese Identitätsfehler nicht beheben. |
| P02 | Dschungel | Neuer One-Shot – Teilfreigabe beachten | Offene Figurenfehler bei Relaxo und Evoli sind nicht mit dem Halm-Reparaturtest lösbar. Wegen der bereits akzeptierten Pikachu-Fassung E keine automatische Voll-Neugenerierung: erst die zwei übrigen Paare dem Nutzer zur eigenen Entscheidung zeigen. |
| P03 | Dunkelnacht | Nutzerprüfung | Zur menschlichen Bewertung vorlegen und derzeit nicht neu generieren: alle drei Figuren sind quellnah; nur begrenzte Konturunterschiede ohne klaren harten Identitäts- oder Tiefenfehler festgestellt. |
| P04 | Pokédex – Generation I | Neuer One-Shot | Glumanders helle Schwanzunterseite fehlt auf einer frei sichtbaren, ausreichend großen Fläche. Dieser Identitätsfehler lässt sich nicht durch eine reine Landschaftsmaske beheben. Bisasams kleine Flecken-/Krallenvereinfachungen gesondert dem Menschen zeigen. |
| P05 | Pokédex – Generation II | Neuer One-Shot | Karnimanis frei sichtbarer Standfuß hat eine andere Zehen-/Fußsilhouette als die breite zweigeteilte Quellform. Zusätzlich endet ein Blatt bei Endivie am Halsknopf. Eine reine Tiefenreparatur würde die Fußanatomie nicht lösen. |
| P06 | Pokédex – Generation III | Detailprüfung | Gegenprüfung am 14. September mit erneuter Originalansicht aller drei Crop/Quellpaare: Die zunächst behauptete stumpfe Blattkappung bei Hydropi ist nicht belastbar; eine natürliche verjüngte Spitze an der Kinnkontur ist ebenfalls plausibel. Kein eindeutiger Tiefensprung belegt. Geckarbors deutlich verdickte, weniger getrennte Finger und Flemlis eng überlagerte Fußlinien brauchen zudem genauere anatomische Prüfung. Daher keine Einstufung als erwiesener reiner Landschaftsfehler und kein Reparaturlauf. |
| P07 | Pokédex – Generation IV | Neuer One-Shot | Panflams frei sichtbare aufgestützte Hand verliert einen in der Quelle getrennten langen Finger; zusätzlich wird die Bauchspirale unklar. Das betrifft Anatomie und ist kein Landschaftsproblem. |
| P08 | Pokédex – Generation V | Neuer One-Shot | Ottaros charakteristische Wangenpunkte fehlen weitgehend auf frei sichtbaren Flächen. Ein weiterer Lauf mit individuellen Gesichtsdetails ist angemessen; eine Grasmaske behebt das nicht. |
| P09 | Pokédex – Generation VI | Neuer One-Shot | Igamaros sichtbare Wangenzeichnung und der weiße obere Zahn gehen verloren. Das sind Gesichtsmerkmale; die Szene sollte mit stärkeren individuellen Referenzdetails gemeinsam neu entstehen. |
| P10 | Pokédex – Generation VII | Nutzerprüfung | Nach direkter Paaransicht kein klarer definierender Form- oder Anatomiefehler. Reduzierte kleine Augen-/Pfotenlinien bei Flamiau und die Fußüberdeckung bei Bauz müssen offen gezeigt werden. Präsentation ist ausdrücklich keine Freigabe. |
| P11 | Pokédex – Generation VIII | Neuer One-Shot | Hopplos Hals- und Sohlenzeichnungen sowie Memmeons Augen und sitzende Bein-/Armstruktur weichen klar ab. Mehrere individuelle Identitätsdetails erfordern einen neuen gemeinsamen Szenenlauf. |
| P12 | Pokédex – Generation IX | Neuer One-Shot | Feloris sichtbare Fangzähne fehlen, und bei Kwaks sitzt unter dem bildrechten Flügel ein nicht quellgetreuer fingerartiger Fortsatz. Kleine Linien allein tragen die Ablehnung nicht. |
| P13 | Pokémon ex - Generation 1 | Neuer One-Shot | Bisaflors Gesicht und Lugias Kopf weichen klar von den Quellen ab; keine reine Überdeckungsreparatur. |
| P14 | Pokémon EX | Neuer One-Shot | Lugias Augen-/Schnabelbereich und Mewtus Handstruktur sind definierend verändert. |
| P15 | Mega-Pokémon EX | Neuer One-Shot | Mega-Latios besitzt ein erfundenes Auge auf dem Flügel, Mega-Rayquazas Kopfzeichnung und Arme sind strukturell verändert; höchste Priorität. |
| P16 | Primal Pokémon EX | Neuer One-Shot | Beide Proto-Formen verlieren klar sichtbare definierende Zeichnung bzw. Gliederung; Szene und äußere Platzierung sind brauchbar. |
| P17 | Fossil | Neuer One-Shot | Lapras verliert die charakteristischen dunklen Körperflecken, Kabutops zeigt eine veränderte sichtbare Fußstruktur. |
| P18 | Karmesin & Purpur | Neuer One-Shot | Feloris Fangzähne und Krokels sichtbar gezackte Handkonturen sind nicht erhalten. Diese Zielbilder werden unabhängig von akzeptierten anderen Kandidaten beurteilt. |
| P19 | Entwicklungen in Paldea | Neuer One-Shot | Feloris Fangzähne fehlen; bei Krokel fehlt ein in der Quelle frei sichtbarer unterer Zahn. Zusätzlich zeigt Kwaks einen ungeklärten hellen Fortsatz zwischen den Beinen. Bereits die klaren Gesichtsdefekte begründen den neuen gemeinsamen Szenenlauf. |
| P20 | Obsidian Flammen | Neuer One-Shot | Glumandas Mund und Arm-/Handkonturen weichen deutlich ab; die sinnvolle Grasüberdeckung bei Bauz ist kein Identitätsfehler. |
| P21 | 151 | Neuer One-Shot | Bisasams sichtbare Fleckenzeichnung ist verändert; eine reine Landschaftskorrektur würde diesen Figurenfehler nicht beheben. |
| P22 | Paradoxrift | Neuer One-Shot | Mewtus ausgestreckte Hand verliert einen klar getrennten Finger, Palkias Handkrallen werden umgebaut; keine lokale Tiefenkorrektur. |
| P23 | Paldeas Schicksale | Neuer One-Shot | Lapras verliert mehrere klar sichtbare blaue Hals-/Körperflecken; die kleine Grasüberdeckung bei Glumanda ist dagegen plausibel. |
| P24 | Gewalten der Zeit | Neuer One-Shot | Flamiaus rote Augenzeichnung und die Flanke wurden verändert; dafür den gemeinsamen One-shot mit individuellen Detailquellen verwenden. |
| P25 | Maskerade im Zwielicht | Neuer One-Shot | Panflams Gesichtsform und Augenzeichnung wurden deutlich umgestaltet; ein enger Landschafts-Pass wäre keine passende Reparatur. |
| P26 | Nebel der Sagen | Neuer One-Shot | Genesects Augenstruktur und Yveltals frei sichtbare Fuß-/Kopfdetails sind klar umgestaltet. |
| P27 | Stürmische Funken | Nutzerprüfung | Kein eindeutiger grober Form-/Anatomiedefekt im direkten Vergleich. Ho-Ohs sehr vereinfachtes Auge und kleinere Linienabweichungen ausdrücklich im Quellenpaar vorlegen; keine automatische Freigabe. |
| P28 | Prismatische Entwicklungen | Neuer One-Shot | Lugias Gesicht ist erneut strukturell verändert; Groudons Maul und seitliche Panzerstacheln weichen deutlich ab. |
| P29 | Reisegefährten | Neuer One-Shot | Reshirams Kopf-/Halsprofil und Federkonturen sind sichtbar umgestaltet. Neu gemeinsam erzeugen; die Grasüberdeckung am Fuß ist nicht der entscheidende Mangel. |
| P30 | Ewige Rivalen | Neuer One-Shot | Ho-Ohs charakteristische gelappte Haube wird zu einem flachen Fächer, zusätzlich weicht die Federzeichnung ab. |
| P31 | Schwarze Blitze | Neuer One-Shot | Kyurems eisiger Flügel und Zekroms erhobene Hand verlieren definierende Details; mehrere Identitätsfehler. |
| P32 | Weiße Flammen | Neuer One-Shot | Reshirams Kopf und Flügel-/Halsdetails weichen strukturell ab; die kleinen Begleitmotive benötigen eher Detailurteil. |
| P33 | SVP Black Star Promos | Neuer One-Shot | Feloris Mund verliert Zähne und Zungenabgrenzung; Krokel verliert einen sichtbaren unteren Zahn. Kwaks besitzt zusätzlich einen klaren weißen Fortsatz zwischen den Beinen. Dies sind Figurenfehler, keine reine Landschaftsreparatur. |
| P34 | Mega-Entwicklung | Neuer One-Shot | Endivies Körper-/Beinaufbau und Knospenkragen weichen deutlich ab; im Crop erscheint zusätzlich ein langer seitlicher Schweif. |
| P35 | Fatale Flammen | Neuer One-Shot | Reshiram und Genesect zeigen deutliche Gesichtsänderungen; Glumandas frei sichtbare Zähne fehlen teilweise. |
| P36 | Erhabene Helden | Neuer One-Shot | Ho-Ohs Haube und Hals-/Schwanzzeichnung sind gegenüber der exakten Quelle verändert; übrige Figuren haben kleinere Detailabweichungen. |
| P37 | Optimale Ordnung | Neuer One-Shot | Mega-Zygardes Körperzeichnung und Kanonenmarkierungen brechen im Vergleich zur Quelle deutlich zusammen. |
| P38 | Wachsendes Chaos | Neuer One-Shot | Mehrere klare Figurenfehler: Igamaro-Mund/Fußspitzen, Ho-Oh-Haube und Fynx-Nase/Beinpose. Hohe Priorität für einen neuen Detailquellen-One-shot. |
| P39 | MEP Black Star Promos | Neuer One-Shot | Zacians Flechtmähne und Bisasams frei sichtbare Fleckenzeichnung sind verändert. Gras vor den Füßen ist erwünscht und kein Grund für einen Anatomievorwurf. |
| P40 | Pokémon ex | Neuer One-Shot | Koraidons Gesicht/Brustrad und Miraidons elektrische Antennen/Brustzeichnung sind stark umgebaut; höchste Priorität. |

## Technische Nachweise und Grenzen

- 309 eindeutige Eingabedateien vor der Neubewertung geprüft; keine Hashabweichung. Dazu gehören vorhandene Master, Figurenquellen und Karten sowie die bereits akzeptierten Kandidaten.
- Vier getrennte Bildprüfberichte, insgesamt 40 eindeutige Zielkennungen und 119 Figuren. Zusätzliche Gegenprüfungen durch den Hauptagenten bei P06, P10, P15, P27 und P40.
- P02: Die bereits akzeptierte Figur samt Reparatur wurde nicht verändert; Relaxo/Evoli werden über ihre unveränderten physischen Karten und Originalquellen beurteilt.
- Keine Generierung, Promotion, Änderung von Produktionsbildern/-code, PDFs oder Archiven. Kein neuer vollständiger Release-Testlauf.

Aktuell geprüfte Implementierungsstellen: [gemeinsamer Szenenprompt](../../scripts/poster_assets/poster_config.py:354), [bisheriges Standardprofil](../../scripts/poster_assets/poster_config.py:1326), [1-MP-Initialisierung](../../scripts/poster_assets/init_poster_scope.py:103), [2-MP-Versuch und Graphschutz](../../tmp/v10_base1_oneshot_trial.py:43).
