# Base1-B und ExGen3-Mega-C: historische Freigaben in v10

Stand: 27.09.2026. Dieser Bericht unterscheidet übernommene Motive, technische Promotion, PDF-Prüfung und weiterhin offene Freigaben.

## Exakt übernommene Motive

| Scope | Historisch vom Nutzer akzeptierter Kandidat | SHA-256 des akzeptierten und des produktiven textfreien Masters | Zustand |
| --- | --- | --- | --- |
| `Base1` | B | `d06f69eb6e010b2670987a2209d3aec50848ac694aaefec64dc70d342ce0d9b4` | Technisch promoviert; PDF nach späterer ausdrücklicher Logofreigabe aktiviert |
| `ExGen3/sections/mega` | C | `eb61f272fd22bd400b2c2555cb2a490fad47c85b3947087a88b96b2e9dce3ebd` | Technisch promoviert, PDF aktiviert |

Für beide Kandidaten wurden der archivierte Originaljob, Workflow, Prompt, die drei exakten Pokémon-Quellen, Rohbild, Reviewbeleg und Master vor Promotion erneut gehasht. Die Masterpixel sind unverändert. Die Provenienz nennt ausdrücklich den historischen `spatial_identity_joint`-Vertrag v8 und behält die damaligen Flags `experimental_prompt_override: true` und `canonical_promotion_eligible: false`; sie gibt keinen neuen Render vor. Alle neun physischen Einleger pro Motiv und die drei Quellen wurden visuell kontrolliert. Base1 zeigt Mewtu, Bisasam und Glumanda; ExGen3 zeigt Mega-Latias, Mega-Diancie und Mega-Lucario. Die vom Nutzer für C tolerierte kleine Augen-/Detailabweichung wird nicht auf andere Motive übertragen.

Die Abschlussprüfung hat den Herkunftsvertrag zusätzlich geschärft: Die Allowlist bindet nun den vollständigen historischen Generierungsdatensatz einschließlich Schritte, Referenzmodus, Auflösung und Ausgabeparametern. Selbst gemeinsam veränderte Experiment-, Manifest- und Run-Angaben werden abgelehnt. Beide bereits übernommenen Motive wurden danach erneut erfolgreich gegen ihre produktive Provenienz validiert.

## Base1: Logo-Blocker

Das authentische deutsche Pokémon-Sammelkartenspiel-Logo stammt aus der dokumentierten [Originalquelle](2026-09-27-base1-de-logo-source.md). Der Cache wurde nach einem verworfenen, unvollständigen Regelbuch-Extrakt auf die echte PNG-Datei mit SHA-256 `666c69257f7d444d943bcc12098e97d48714bab742955d0efc7454bfb3948b1f` zurückgesetzt. Die Quelle ist 250 × 128 px und auf dem 750 × 1050-px-Einleger bei Druckgröße sichtbar weich. Deshalb keine Base1-PDF-Aktivierung, kein Austausch der bestehenden Base1-PDF und keine Aussage, dass diese Ausgabe bereits eine verkäufliche Druckvorlage sei. Offen bleibt eine belegte, scharfe deutsche Logoquelle plus erneute Druckprüfung.

Nachtrag vom 27.09.2026: Der Nutzer akzeptierte ausdrücklich genau dieses historische deutsche Logo und seine sichtbare Auflösungsgrenze. Die spätere Base1-Aktivierung und PDF-Prüfung sind im [nachfolgenden Aktivierungsbericht](2026-09-27-base1-p37-pdf-activation.md) dokumentiert; der obige Absatz bleibt als ursprünglicher, vor der Nutzerentscheidung geltender Befund erhalten.

## ExGen3: deutsche PDF-Prüfung

- Normales und Mega-Panorama erscheinen in dieser Reihenfolge auf den Seiten 1 und 27. Der Normalmaster und alle anderen Sektionen bleiben unverändert; nur Mega-C wurde neu geroutet.
- Die getrennten Prüffassungen `cards` und `full-page` enthalten je 33 A4-Seiten und 261 nummerierte Einträge; Infokarte auf Seite 33. Seiten 1 und 27 wurden im Einzelbild, alle 33 Seiten beider Varianten als Raster-Kontaktbogen geprüft. Außer den beiden Panoramaseiten sind die 90-dpi-Raster beider Varianten pixelgleich.
- Der Mega-Einlegerbogen enthält neun eingebettete 750 × 1050-px-Bilder mit 300 dpi; die Vollseitenvariante enthält den 2368 × 3268-px-Master mit 300 dpi. Auf den geprüften Seiten 27/28 sind Schnittlinien, Abschnittsübergang und die erste Mega-Kartenseite vollständig und ohne sichtbare Überschneidung.
- Die reguläre deutsche Datei `output/de/ExGen3_DE.pdf` wurde erst nach dieser Kandidatenprüfung neu gebaut. Ihr alter Zustand wurde ignoriert lokal gesichert (SHA-256 `3f2511dfebfd2c52df134a24eb797aa8f16d142ac1e6272529d10d112ab330d4`). Die neue Datei hat SHA-256 `a4e6fc55f46f6799eedb8e08d42ed289162dceef57d82eb8922258785c52b9cd`; ihr 33-seitiges 90-dpi-Raster ist auf jeder Seite pixelgleich zum geprüften Karten-Kandidaten (dessen PDF-Bytehash wegen Metadaten abweicht: `a6b70871988bd69252d6fe53014a837d4d6fd23fb74b1b73a11f557dd604fdfb`).

Die PDF-Dateien sind bestehend release-konform ignorierte lokale Bauartefakte und noch kein publiziertes v10-Release. Datenstand, Rechts-/Markennutzung und die anderen offenen Poster gehören zu eigenen Release-Gates; die optische ExGen3-Prüfung ersetzt sie nicht.
