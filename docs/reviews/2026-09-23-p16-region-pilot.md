# P16 regionsgebundener One-shot — technischer Pilotbefund

**Historischer Zwischenstand:** Die unten vermutete 2×2-Tokenpackung wurde vor
Pilot C am gepinnten FLUX.2-Modell widerlegt. Der [spätere Pilot-C-Bericht](2026-09-23-p16-region-pilot-c.md)
dokumentiert `patch_size=1`, 104×75 Hauptbild-Tokens und den danach erreichten
numerischen Fehler. Dieser Bericht bleibt als Fehlerchronik erhalten.

Stand: 2026-09-23. Variante: `p16-region-20260923-a`. **Nicht freigegeben; kein Bild entstanden.** `joint_scene` bleibt der produktive Standard. P16 und P37 wurden nicht promotiert oder für neue PDFs verwendet.

Der isolierte Job wurde mit vier hashgebundenen Referenzen, der lokalen Guider-Erweiterung und den gepinnten FLUX.2-4B-Modellen vorbereitet. Lokale Tests (75 fokussierte Prüfungen), Modell-/Jobhash-Validierung auf dem konfigurierten Worker und eine kleine MPS-Aufmerksamkeitsprobe bestanden. Die Modellgewichte sind BF16. Der erste Startversuch blieb noch vor ComfyUI an einem durch die eigene MPS-Probe erzeugten Python-Bytecode-Cache im Job hängen. Genau diese vier Cache-Dateien wurden nach Dateilistenprüfung lokal und auf dem Worker entfernt; der Job bestand danach erneut die vollständige Hashprüfung.

Beim einzigen tatsächlichen Bildlauf lud ComfyUI Textencoder und FLUX.2-Modell und erreichte den ersten Sampling-Schritt. Dort brach der Pilot mit `P16 latent canvas does not match region contract` ab. Das gepinnte `EmptyFlux2LatentImage` erzeugt bei 1200 × 1664 Pixeln ein Latent von 75 × 104 (`width // 16`, `height // 16`); der Pilotvertrag erwartete irrtümlich 150 × 208 (`// 8`). Die gepinnte FLUX.2-Implementierung packt außerdem jeweils 2 × 2 Latent-Zellen pro Bildtoken. Daher muss der regionsgebundene Vertrag für einen neuen Versuch auch die Token-Geometrie auf 38 × 52 und die tatsächliche Semantik von `img_slice` für Doppel- und Einzelblöcke abgleichen. Diese weiteren Unterschiede wurden nur lesend am gepinnten Quellcode festgestellt, nicht per erneutem Render getestet.

Das gesamte Jobverzeichnis samt `comfyui.log` wurde in den ignorierten Pilotordner zurückgeholt. `run.json` fehlt, weil kein Bildlauf erfolgreich abgeschlossen wurde; es gibt null Ausgabebilder. Der zurückgeholte Job und seine Modell-Dateien bestanden die Hashprüfung weiterhin. Workflow-SHA-256: `66b1977f74fad8f2bcf706543dfb35be5cadeb86c83dccbbcf4489bcfc6de52b`; Log-SHA-256: `d7376db5eb5f9d70d6da16e49f0e67c86856a6f13ed5cc3b33648b3dc9180054`. Die produktiven P16- und P37-Master samt Provenienz haben dieselben Hashes wie vor dem Versuch.

Für einen Folgelauf braucht es einen korrigierten, versions- und hashgebundenen FLUX.2-Geometrievertrag, neue Tests gegen den gepinnten Worker-Quellcode und einen **neuen** unveränderlichen Variantnamen. Den fehlgeschlagenen Job nicht überschreiben oder als Artwork-Abnahme ausgeben. Kein automatischer Seed-, Modell- oder Mehrstufen-Fallback.
