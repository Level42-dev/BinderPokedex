# P02 – Dschungel: gezielte Vordergrund-Nacharbeit

Stand: 14.09.2026. Isolierter Versuch auf ausdrücklichen Nutzerwunsch. Keine Übernahme in Original-Artwork, Produktionsrenderer, PDF oder Release.

Nachfolgende Fortsetzung auf erneuten Nutzerwunsch: [Konturgeführte Kandidaten D/E](2026-09-14-base2-contour-repair.md). E liegt jetzt zur Nutzerbewertung vor; dieser Bericht bewahrt die vorherige, erfolglose Versuchsreihe A–C.

## Prüfauftrag

Pikachus Darstellung wurde vom Nutzer akzeptiert. Zwei bereits vorhandene, von unten links kommende Grashalme sollen vor dem ausgestreckten Arm und der linken Bauchseite weiterlaufen. Die orangefarbenen Markierungen im Nutzerbild sind eine Richtungs- und Positionshilfe, keine gewünschten Bildelemente.

## Vorgehen und Grenzen

1. Die zwei widersprüchlichen Überdeckungen wurden visuell lokalisiert und mit der Nutzerannotation abgeglichen. Das ist agentengeführte Analyse, **noch kein implementierter autonomer Tiefenfehler-Detektor**.
2. Der unveränderte physische Kartenausschnitt (750 × 1050 Pixel) wird ohne Skalierung auf 768 × 1056 Pixel aufgefüllt. Zwei eng begrenzte Masken erlauben das Ergänzen der vorhandenen Halme.
3. Der bereits konfigurierte Worker führt einen maskierten FLUX.2-Klein-4B-Lauf aus. Gesicht, Pose und restliche Szene sind nicht zur Neubearbeitung vorgesehen.
4. Eine deterministische Maskenkomposition übernimmt nur Pixel in den beiden Reparaturregionen. Rohbild und begrenztes Ergebnis bleiben separat erhalten. Ein vollständiger Pixelvergleich muss außerhalb der erlaubten Regionen exakt null Änderungen ergeben.

Die Nacharbeit ist ein optionaler Reparaturschritt **nach** einem One-Shot, kein Ersatz für den vereinbarten primären One-Shot-Ansatz. Es werden keine Pokémon-Quellbilder nachträglich eingeklebt. Die Masken können unerwünschte Änderungen außerhalb ihres Bereichs verhindern, aber keine gute Zeichnung innerhalb der Maske garantieren.

## Versuche

### A – Textgeführte Reparatur

Ein neuer grüner Halmabschnitt liegt vor dem Bauch. Der Halm am Arm bleibt jedoch dahinter; außerdem bleibt ein Stück der überdeckten Körperkontur im grünen Bauchhalm sichtbar. **Nicht als vollständige Korrektur akzeptiert.**

- Laufzeit laut zurückgeholtem Laufprotokoll: 34,31 Sekunden.
- 13.792 geänderte Pixel innerhalb von 13.866 erlaubten Pixeln; **0 Änderungen außerhalb** – sowohl im Ausschnitt als auch im vollständigen Panorama.
- Rohbild, begrenzter Pikachu-Ausschnitt und vollständiger textfreier Master wurden visuell geprüft. Keine vollständige Neufreigabe aller neun Karten für diesen verworfenen Versuch.
- [A: Kartenausschnitt](../../tmp/foreground-repair-trials/base2-foreground-20260914-a/review/pikachu-card.png) · [technische Evidenz](../../tmp/foreground-repair-trials/base2-foreground-20260914-a/review/evidence.json)

### B – Nutzerannotation als zusätzliche Bildreferenz

Gegenüber A bleiben Original, Masken, Modelle, Seed, Raster und Sampler unverändert. Hinzu kommen die unveränderte Nutzerannotation als zweite Bildreferenz und die zugehörige Rollenbeschreibung im Prompt. Sie fordert beide grünen Überdeckungen und das Entfernen der jeweils verdeckten schwarzen Körperkontur.

Die Bildreferenz genügt nicht: Der Arm bleibt unverdeckt; am Bauch entsteht nur eine sehr kurze, nicht überzeugende Spitze. **Verworfen.** Rohbild, Pikachu-Karte und vollständiger textfreier Master wurden betrachtet.

- Laufzeit: 66,39 Sekunden.
- 13.788 geänderte Pixel innerhalb der unveränderten Maske, **0 außerhalb**.
- [B: Kartenausschnitt](../../tmp/foreground-repair-trials/base2-foreground-20260914-b/review/pikachu-card.png) · [technische Evidenz](../../tmp/foreground-repair-trials/base2-foreground-20260914-b/review/evidence.json)

### C – Freie Synthese, weiterhin ausschließlich maskierte Übernahme

Hypothese: Die auf die beiden Regionen beschränkte latente Inpainting-Bearbeitung hält an den alten verdeckten Konturen fest. C ersetzt deshalb ausschließlich das maskierte Ausgangslatent durch ein leeres Zielbild. Prompt, beide Bildreferenzen, Modelle, Seed, Sampler und finale Übernahmemaske bleiben wie bei B. Der Generator darf ein vollständiges Rohbild erzeugen; der endgültige Ausschnitt übernimmt weiterhin nur die zwei erlaubten Regionen.

Im freien Rohbild entsteht ein viel zu langer, nahezu waagerechter Halm über dem Bauch; zwei orangefarbene Annotationsreste erscheinen rechts. Die engen Übernahmemasken verhindern diese großflächige Veränderung, schneiden die abweichende neue Geometrie aber sichtbar ab. Im begrenzten Ergebnis bleiben helle Farbkeile und nicht passende Übergänge an Arm und Bauch. **Verworfen.** Rohbild, Pikachu-Karte und vollständiger textfreier Master wurden betrachtet.

- Laufzeit: 69,35 Sekunden.
- 13.789 geänderte Pixel innerhalb der unveränderten Maske, **0 außerhalb**.
- [C: Rohbild](../../tmp/foreground-repair-trials/base2-foreground-20260914-c/retrieved/repair-85jfe072/output/base2_depth_raw_00001_.png) · [begrenzter Kartenausschnitt](../../tmp/foreground-repair-trials/base2-foreground-20260914-c/review/pikachu-card.png) · [technische Evidenz](../../tmp/foreground-repair-trials/base2-foreground-20260914-c/review/evidence.json)

## Ergebnis: Teilerfolg, keine saubere Korrektur

Die Versuchsreihe endet nach drei unterscheidbaren Steuerungen. Kein Versuch erfüllt beide gewünschten Halmüberdeckungen mit sauberen Anschlüssen. Der deutlichste örtlich passende Teilerfolg ist A am Bauch; auch A bleibt wegen des Armhalms und der sichtbaren alten Körperkontur **nicht freigabetauglich**.

C zeigt, dass freie Synthese Überdeckungen erzeugen kann. Sie kontrolliert deren Verlauf aber nicht genau genug für diese Reparatur. Die Annahme, allein das Öffnen der Inpainting-Maske löse den Fehler, hat sich damit nicht bestätigt. Für einen weiteren Versuch wäre eine andere, präzisere Kontursteuerung zu prüfen; bloße Wiederholungen oder weitere Betonungen desselben Prompts werden hier nicht gestartet. Eine allgemeine automatische Nacharbeitsstufe ist nicht implementiert.

### Pikachu – physischer Ausschnitt und exakte Quelle

Das Bild in der Mitte ist ausdrücklich ein **nicht akzeptierter Test**, keine neue Originalfassung.

| Vorher: akzeptierte Pikachu-Darstellung, falsche Tiefe | Versuch A: Teilkorrektur am Bauch | Tatsächlich verwendetes Quell-Pokémon |
| --- | --- | --- |
| ![P02 Pikachu – unveränderter Kartenausschnitt](../../tmp/poster-workspaces/Base2/comfyui_poster/promotion/poster-flux2-cards/card_r3_c1.png) | ![P02 Pikachu – Test A, noch fehlerhaft](../../tmp/foreground-repair-trials/base2-foreground-20260914-a/review/pikachu-card.png) | ![Pikachu – exakte verwendete Quelle](../../tmp/poster-workspaces/Base2/sources/cutouts/pokemon_025_pikachu.png) |

[A im vollständigen Panorama](../../tmp/foreground-repair-trials/base2-foreground-20260914-a/review/artwork-300dpi.png) · [alle Prüfnachweise und Urteile](2026-09-14-base2-foreground-repair.json)

## Abschlussprüfung

- Zwölf fokussierte Tests bestanden: fünf Schutz-/Variantenprüfungen und sieben vorhandene Render-Job-Tests. Das ist kein vollständiger Release-Testlauf.
- Bei allen drei Jobs wurden Paketbindung, Eingaben, Modelle, `run.json`, `comfyui.log` und sämtliche Ausgabebilder geprüft.
- Alle 27 erzeugten physischen Karten stimmen mit ihren neun jeweiligen Ausschnitten im 300-dpi-Raster überein. Je Versuch sind die acht anderen Karten pixelidentisch mit dem Original.
- Die sechs gebundenen Ausgangsdateien jedes Versuchs blieben unverändert. Keine visuelle Vollfreigabe aller neun Karten, keine Nutzerfreigabe der Nacharbeit und keine Promotion.

## Reproduzierbarkeit

- [Versuchsskript](../../tmp/v10_foreground_repair_trial.py) und [Sicherheitstests](../../tmp/test_v10_foreground_repair_trial.py) liegen im ignorierten Versuchsbereich; keine Änderung am Produktionsrenderer.
- Jeder Versuch besitzt ein eigenes unveränderliches Jobpaket mit Workflow, Eingabebildern und Modell-Hashes. `run.json`, `comfyui.log` und alle Ausgabebilder werden zurückgeholt und geprüft.
- Die vollständigen tatsächlich verwendeten Prompts stehen in den Versuchsdaten [A](../../tmp/foreground-repair-trials/base2-foreground-20260914-a/experiment.json), [B](../../tmp/foreground-repair-trials/base2-foreground-20260914-b/experiment.json) und [C](../../tmp/foreground-repair-trials/base2-foreground-20260914-c/experiment.json) sowie in den versiegelten Workflows. Backend: bestehender ComfyUI-Worker mit gepinnten FLUX.2-Modellen, kein Wechsel zu einem anderen Bilddienst.
- Ausgangsmaster: `9c0c166cc6bda2f8a8e07ba9affd486c19d9c017b54ed15b9bedba4568d5c45f`.
- Exakter Pikachu-Quellausschnitt: `bd2163009d392e192c134a5f1c4ccceafd5d7c57a704373c6b6be4be0091cc5f`.
- Nutzerannotation: `725015f63b68624ad7dd0847fa3f8d86fc33fc63b763dfa8d3af88441eb0d03f`.

Relaxo, Evoli, das vollständige Panorama sowie Druck- und Release-Freigabe bleiben davon getrennte, offene Prüfpunkte.
