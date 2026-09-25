# P02 – Dschungel: Konturgeführte Nacharbeit, Kandidat E

Stand: 14.09.2026. Fortsetzung nach dem Nutzerauftrag „mach bitte weiter“. **Pikachu samt Vordergrundüberdeckung in Fassung E vom Nutzer visuell akzeptiert; nicht übernommen und nicht veröffentlicht.**

## Ergebnis

Beide vorhandenen Vordergrundhalme laufen jetzt vor Pikachu weiter: über dem ausgestreckten Arm und über der linken Bauchseite. Die zuvor quer durch die grünen Flächen laufenden Körperkonturen werden dort verdeckt. Gesicht, Augen, Ohren, Fingerspitzen, Pose und Schwanz bleiben außerhalb der schmalen Überdeckungen pixelgleich mit der bereits akzeptierten Bestandsdarstellung.

Der lokale Tiefenfehler besteht den Agenten-Sichtcheck in E. In der Vergrößerung ist am rechten Rand des Bauchhalms weiterhin eine kleine Unregelmäßigkeit der Kontur zu sehen; sie ist kein durch den Halm verlaufender Körperstrich. Dieser Hinweis sowie die Bitte, die Anschlüsse zu beurteilen, wurden vor der anschließenden Nutzerfreigabe mitgeteilt. Es wird keine pauschal makellose Druck- oder Gesamtpanorama-Freigabe behauptet.

## Nutzerfreigabe

Am 14.09.2026 wurde die gezeigte Fassung mit „das sieht prima aus!“ akzeptiert. Die Freigabe gilt für **Pikachu und die zwei korrigierten Vordergrundhalme in E**, nicht für Relaxo, Evoli, das gesamte Panorama, Beschriftung, PDFs oder Veröffentlichung. Die Bestandsfassung und die versiegelten Versuchsnachweise bleiben unverändert.

Die Freigabe ist im [Ergebnisbericht](2026-09-14-base2-contour-repair.json) an den gezeigten Kartenausschnitt `d92ab3abb30aaeaffed2d128891ef69cdff7b329ef82252b0c36c753117002b4`, den Master `70766e8307e73b36e0d5ff6be18f24c0df0efaae35cc7fb9355eb6948ee291aa` und die daneben gezeigte Originalquelle gebunden.

## Pikachu – unten links, physische Karte r3c1

Rechts steht die Identitätsquelle der Bestandsfassung. Sie wurde im Reparaturlauf nicht erneut als Figur eingefügt.

| Neuer Kartenausschnitt E | Tatsächlich verwendetes Quell-Pokémon |
| --- | --- |
| ![Pikachu – Nacharbeit E](../../tmp/foreground-repair-trials/base2-contour-20260914-e/review/pikachu-card.png) | ![Pikachu – unveränderte Quelle](../../tmp/poster-workspaces/Base2/sources/cutouts/pokemon_025_pikachu.png) |

[Vorher](../../tmp/poster-workspaces/Base2/comfyui_poster/promotion/poster-flux2-cards/card_r3_c1.png) · [Überdeckungen vierfach vergrößert](../../tmp/foreground-repair-trials/base2-contour-20260914-e/review/pikachu-intersections-4x.png) · [vollständiger textfreier Master E](../../tmp/foreground-repair-trials/base2-contour-20260914-e/review/artwork-300dpi.png)

## Andere Steuerung statt weiterer Prompt-Wiederholungen

Die [vorherigen Versuche A–C](2026-09-14-base2-foreground-repair.md) konnten die zwei Verläufe nicht zuverlässig herstellen. In dieser Fortsetzung wurden die sichtbaren Blattkanten visuell nachverfolgt und als kurze Kurven bis zu den vom Nutzer markierten Spitzen verlängert. Die geometrische Vorlage verwendet Grün- und Texturinformationen aus den gleichen bereits vorhandenen Halmen. Es wurden keine Pokémon-Bildchen nachträglich eingesetzt.

Der bestehende, konfigurierte ComfyUI-Worker erhält diese Vorlage als Ausgangsbild und Bildreferenz. Ein tatsächlicher maskierter FLUX.2-Klein-4B-Lauf gleicht die Blattflächen und Kanten an. Erst danach wird außerhalb der beiden engen Schutzmasken das unveränderte Original beibehalten. Die gezeigte Fassung E ist das geprüfte Generatorergebnis mit dieser Schutzkomposition, nicht bloß die geometrische Eingabevorlage.

| Versuch | Einzige weitere Änderung | Ergebnis |
| --- | --- | --- |
| D | Kontur- und Texturvorlage ersetzt die rein beschreibende Steuerung | Beide Überdeckungen vorhanden; periodische Querbänder aus der gekachelten Spendertextur. Durch E ersetzt |
| E | Nur die Spendertextur läuft durchgehend statt periodisch; gleicher Workflow, gleiche Masken, Geometrie, Modelle und Seed | Beide Überdeckungen bleiben erhalten; die periodischen Querbänder entfallen. Lokal vom Nutzer visuell akzeptiert |

Ein neuer Startfehler trat bei beiden Varianten vor der Jobanlage auf. Vor jeweils einem kontrollierten erneuten Start wurde lesend nachgewiesen, dass der konkrete Job nicht existierte. Danach wurde pro Variante genau ein vollständiger Renderlauf zurückgeholt. Die genaue Ursache des ersten Reservierungsfehlers ist nicht belegt; es gab keine blinde Wiederholung einer möglicherweise laufenden Generierung.

## Prüfung und Grenzen

- 17 fokussierte Tests bestanden: Kontur-/Texturführung, Schutzmasken und vorhandene Render-Job-Prüfungen. Kein vollständiger Release-Testlauf.
- Beide vollständigen Jobpakete mit Laufprotokoll, ComfyUI-Log und sämtlichen Roh-/begrenzten Ausgaben sind zurückgeholt und gebunden geprüft.
- Für E: 10.783 geänderte Pixel innerhalb von 10.787 erlaubten Pixeln; **0 geänderte Pixel außerhalb der Masken** im vollständigen Panorama.
- Alle neun physischen Ausschnitte je Variante stimmen mit dem jeweiligen 300-dpi-Raster überein. Die acht anderen Karten sind je Variante pixelidentisch mit der Bestandsfassung.
- Visuell betrachtet: beide Eingabevorlagen und Rohbilder, beide nativen Pikachu-Karten, die vergrößerten Überdeckungen, beide vollständigen textfreien Master, die E-Vorschau mit Bestandsbeschriftung und das genaue Quell-Pokémon. Keine visuelle Vollfreigabe aller neun Karten oder der anderen Pokémon.
- Die übernommene Vorschau namens `poster-de.png` enthält weiterhin die vorhandene **englische** Beschriftung „Jungle / 64 cards / Released“. Sie ist nicht neu lokalisiert und kein freigegebenes deutsches Druckprodukt. Der hier beurteilte Master ist textfrei.
- Kein Originalbild, Produktionsrenderer, PDF oder Release-Archiv wurde ersetzt. Relaxo und Evoli sowie Gesamtpanorama-, Lokalisierungs-, PDF- und Release-Freigabe bleiben getrennt offen.

Dies bleibt ein gezielt geführter Machbarkeitstest: **Kein allgemeiner automatischer Tiefenfehler-Detektor wurde implementiert.** Die räumliche Vorgabe kommt bisher aus der agentengeführten Bildanalyse. One-Shot bleibt der primäre Weg; diese begrenzte Nacharbeit ist eine optionale Reparatur.

## Reproduzierbarkeit

[Hashgebundener Ergebnisbericht](2026-09-14-base2-contour-repair.json) · [Versuchsskript](../../tmp/v10_contour_repair_trial.py) · [Tests](../../tmp/test_v10_contour_repair_trial.py)

Die vollständigen Prompts, Kurven und Eingaben sind in den Versuchsdaten [D](../../tmp/foreground-repair-trials/base2-contour-20260914-d/experiment.json) und [E](../../tmp/foreground-repair-trials/base2-contour-20260914-e/experiment.json) sowie den unveränderten Jobpaketen dokumentiert. Kein anderer Bilddienst und keine neuen Modelle wurden eingesetzt. Die Probe liegt im ignorierten Versuchsbereich, nicht im Produktionsrenderer.
