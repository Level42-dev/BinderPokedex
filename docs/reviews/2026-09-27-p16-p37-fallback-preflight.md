# P16/P37: quellgebundene Fallback-Vorprüfung

Stand: 27.09.2026. Dies ist eine technische Vorprüfung, keine Bild- oder PDF-Freigabe.

Beide Scopes behalten ihre produktiven Manifeste, Master und PDFs. Der bestehende Workspace-Marker ist vollständig, nur für den lokalen Benutzer lesbar und verweist auf einen erreichbaren privaten Apple-MPS-Worker. Es wurde kein Ziel aus der Unterhaltung oder einem beliebigen laufenden Prozess abgeleitet. Verbindungswerte und Maschinenpfade stehen ausschließlich im ignorierten Marker, nicht in diesem Bericht oder den Jobs.

| Kandidat | Motiv / kritische Druckkarte | Quellbild-SHA-256 | unveränderlicher Szenenjob-SHA-256 |
| --- | --- | --- | --- |
| `p16-il-20260927-a` | Proto-Kyogre, r3c1 | `226507487da40a44b8df44c4fd04ecc6398b8873e792dd2ce31ecfa7a8e3777b` | `697ac4de929aec2f013df72619417a9a44727441ad40b821ef4157870031a384` |
| derselbe | Proto-Groudon, r3c3 | `fd0a131143a3289cde178438f5ea0249ff62cacb6dbb6742c95544c7c42aad5a` | derselbe |
| `p37-il-20260927-a` | Serpifeu, r3c1 | `e7ff61a0daed598a7676b262c56af766e88bcf91764658eeeae615f6f9937549` | `00b76b9cf727c031340376ced80caba0f89347968af8de7b2d2870627b5dc0f6` |
| derselbe | Bauz, r3c2 | `5456dc8d55b3fd305bb7ddd4b1f94f07b51e3691414abaf4d60c7a7745f09c36` | derselbe |
| derselbe | Mega-Zygarde, r3c3: linkes Emblem vollständig innerhalb der Karte | `33261872ff2adb38b60f19d6f18a34681555e4243ff4c2ca5f367e9ddd976b55` | derselbe |

P16 verwendet explizit Official-Artwork-IDs 10077/10078, P37 für Mega-Zygarde 10301; die Alpha-/Form-Prüfung des reproduzierbaren Quellenabrufs meldete alle fünf Dateien gültig. Die konkreten Mängel der abgelehnten Vorgänger sind [für P16](2026-09-23-p16-stronger-oneshot.md) und [für P37](2026-09-22-panorama-batch-review-notes.md) dokumentiert. Kandidat A je Scope verwendet die bestehenden Seeds 647668836648946 bzw. 260791529, `identity_lock/two_pass_source_pixels`, FLUX.2 Klein 4B und Qwen 3 4B; kein stiller Modell- oder Seed-Wechsel.

Der Szenenjob je Scope enthält genau drei referenzierte Eingabebilder und drei hashgebundene Modelle. Der 300-dpi-Modell-Upscale mit dem vorhandenen Real-ESRGAN-Anime-Modell wurde zusätzlich als eigener zweiter Job vorbereitet. Beide P16-Stufen und der separate P37-Szenenjob wurden vor einem GPU-Lauf übertragen und auf dem Worker erfolgreich gegen Workflow-, Eingabe- und Modellhashes validiert. Für den Upscale-Trockentest diente ausdrücklich ein altes, abgelehntes P16-Rohbild nur als Transport-/Pfadprobe; es ist kein neuer Kandidat. Der echte zweite Job wird erst aus dem neuen Szenenergebnis erstellt.

Ausgangshashes der produktiven P16-/P37-Master sind `74c828b35bbf41bd745c80b088179ac41aba9e560a2cfff824504f0c2c85b836` und `f168f308c04d3cfd617d49378ae74ebc3bb5ad9ccb6fb6fbc8e1f01dcd1a065f`; die bestehenden lokalen deutschen PDFs haben `c714da38608b7c414fd4f5301181cddc8f8f5cd627b72c0ec6d629dcb9522ebf` bzw. `7adc6723a3b8862c515208fbc8cade0559f2cd19e9dc93c28cba525b3d10ad95`. Der fokussierte Testlauf meldete 208 bestandene Tests.
