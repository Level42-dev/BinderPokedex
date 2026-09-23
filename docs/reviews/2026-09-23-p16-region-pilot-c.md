# P16: korrigierter FLUX.2-Regionspilot C

Stand 23.09.2026: **vorbereitet, nicht gerendert, nicht freigegeben**. Der konfigurierte Remote-Worker war vor dem Jobtransfer nicht mehr erreichbar (SSH-Timeout). Ein lokales Renderziel wurde nicht stillschweigend gewählt. Es gibt für C weder `run.json` noch `comfyui.log` noch ein Ausgabebild. P16- und P37-Produktionsmaster, Provenienz und PDFs sind unverändert.

## Abgrenzung der Versuche

- `p16-region-20260923-a`: erster GPU-Lauf, vor Bildausgabe an falscher Latentgeometrie gescheitert; Log-SHA-256 `d7376db5eb5f9d70d6da16e49f0e67c86856a6f13ed5cc3b33648b3dc9180054`. Siehe `2026-09-23-p16-region-pilot.md`.
- `p16-region-20260923-b`: nach der ersten Korrektur versiegelter, aber **nicht gestarteter** Job. Die unabhängige Prüfung erkannte vor dem Transfer, dass versehentlich die Tokengeometrie des Qwen-Bildmodells auf FLUX.2 Klein übertragen worden war. Job-Manifest-SHA-256 `f8958e149312cf20187c382c7b44cea5c2075945fe504a0ff3c72a0b2fa2b6f0`.
- `p16-region-20260923-c`: einziger derzeit für einen weiteren GPU-Test vorgesehener Job. Er bindet A und B in seiner ignorierten Laufprovenienz, verwendet unverändert Seed `653315091`, dieselben beiden Quellen, FLUX.2 Klein 4B, Qwen3 4B und vier Schritte. Er bleibt strikt außerhalb der Produktion.

## Technischer Vertrag für C

Das tatsächliche Bildmodell ist FLUX.2, nicht Qwen Image. Für 1200 × 1664 Bildpixel beträgt das Latent 104 × 75 Zellen. FLUX.2 verwendet hier `patch_size=1`, also ebenfalls 104 × 75 Hauptbild-Tokens. Die beiden Referenzen liefern 1976 und 1024 Tokens. Beide FLUX-Blockarten (`double` und `single`) müssen den regionsgebundenen Attention-Override aufrufen. Der Regionsvertrag ist Version 3 mit SHA-256 `c5a508657aac24dda6b007d052f3e93e464bc7d658cdb87f19913832da173956`.

Die gezielte Suite besteht mit 48 Tests. Die vollständige Suite meldet 905 bestanden, einen übersprungenen und drei bereits bestehende Base1-Freigabe-Sperren; diese wurden nicht abgeschwächt. Eine kleine lokale Metal/BF16-Probe der Maske besteht in beiden Blockarten. Die noch fehlende Prüfung ist ein minimaler Hook-Test im **gepinnten** Worker mit dessen subquadratischem Attention-Backend, gefolgt von genau einem C-Renderlauf, Rückholung aller Ausgaben und Sichtprüfung von Gesamtpanorama, neun physischen Einlegern und beiden Quellenvergleichen. Erst danach kann der exakte Kandidat dem Nutzer vorgelegt werden; keine automatische Promotion und kein P37-Folgelauf.
