# P16: Identity-Lock-Kandidat A abgelehnt

Stand: 27.09.2026. **Keine Nutzerfreigabe, keine Promotion, keine PDF-Aktivierung.** Kandidat `p16-il-20260927-a` ist ein isolierter Test des ausdrücklich für diesen gescheiterten One-shot-Fall reservierten Fallbacks.

## Reproduzierbare Eingaben und Rückgaben

- Unveränderlicher Szenenjob SHA-256 `697ac4de929aec2f013df72619417a9a44727441ad40b821ef4157870031a384`; tatsächlicher 300-dpi-Upscale-Job SHA-256 `3838430b9189395a730e4d6fa73f189b89894e436f9509d455d7a0cebf4d72a4`.
- Beide Jobs wurden vor Ausführung auf dem gespeicherten privaten Worker hashvalidiert. Für beide liegen `run.json`, `comfyui.log` und genau ein Ausgabebild vollständig im ignorierten Scope-Workspace vor. Die Szenen- und Upscale-`run.json`-Hashes lauten `f867a6a4477e9aa36fc051f9a3e0b9d49585985b036dcce8cb1f0576e8114769` und `18f6ec7bebd35ac348bdf563a189c367d6c597c1c496a494c6c134fe1a1d063a`; Gerät MPS und Ausgabedateihashes sind bestätigt.
- Das Rohbild SHA-256 `348e800dab28ed02a376c2b01998ac38ba4eed8036b7bbbcc5138902e49af366` bewahrt 24.992 vollständig opake Quellpixel, davon 0 verändert. Der fertige textfreie 2368 × 3268-px-Master hat SHA-256 `bae8c22729c089b4dc971e8a662c23010fd2c367e68ef2ed7c829857c7295524`; die deutsche Vorschau `db5a55da5afe43b35343f22af36937dceecae51655bec65add0a3d13e35ac7c2` und alle neun 750 × 1050-px-Karten sind vorhanden und einzeln geprüft.

## Visueller Befund

Die früher abgeschnittenen Außenkanten von Proto-Kyogre auf r3c1 und Proto-Groudon auf r3c3 liegen diesmal vollständig innerhalb ihrer jeweiligen physischen Karte. r3c2 enthält keine fremden Flossen oder Schwanzteile. Die beiden Figuren erhalten ihre definierenden Quellmerkmale.

Der Szenenaufbau besteht jedoch aus einer deutlich geraden, dunkel konturierten Grenze quer durch **alle drei unteren Karten**. Unterhalb davon liegt eine andere Steinfläche. Kyogre liegt auf Stein statt nachvollziehbar im Meer; beide Figuren haben keinen plausiblen Bodenkontakt oder Richtungsschatten und wirken eingesetzt. Der harte horizontale Übergang ist auf Gesamtbild und Einlegern sofort sichtbar. Zudem liest der Titel der deutschen Vorschau `Primal Pokémon EX`, also nicht vollständig deutsch. Diese Punkte verletzen die vereinbarte Szenen-/Druckfreigabe trotz bestandener Pixelprüfung.

Der Fehler folgt nicht aus einem knapp falschen Seed oder fehlenden Upscale-Pixeln: Der aktuelle Identity-Lock-Vertrag verlangt ausdrücklich eine glatte geschützte untere Zone ohne hohe Vordergrundelemente und erzeugt hier eine harte Grenzlinie. Ein weiterer blinder Seed-Lauf oder bloßes Austauschen eines Schattenworts ist daher nicht begründet. Nächster sinnvoller Versuch wäre eine **eigene**, quellpixelgeschützte, subjektbezogene Untergrund-/Wasserkontakt- und Schattenkomposition, die die Dreikarten-Grenze nicht sichtbar macht; sie benötigt vor einem GPU-Lauf einen konkreten Masken- und Kontinuitätsentwurf. Dieser Kandidat wird dem Nutzer nicht als freigabefähig vorgelegt.

Der aktive P16-Master und die bestehende deutsche PDF behalten ihre Ausgangshashes `74c828b35bbf41bd745c80b088179ac41aba9e560a2cfff824504f0c2c85b836` und `c714da38608b7c414fd4f5301181cddc8f8f5cd627b72c0ec6d629dcb9522ebf`.
