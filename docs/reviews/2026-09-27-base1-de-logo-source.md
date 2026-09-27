# Base1: deutsche Titel-Logoquelle

Stand: 27.09.2026. Dieser Quellenbefund ist **keine PDF- oder Release-Freigabe**.

- Quelle für `de`: `https://tcg.pokemon.com/assets/img/global/logos/de-de/tcg-logo-2x.png` (offizielle Pokémon-TCG-Domain; HTTP 200, `image/png`).
- Nach Abruf über `fetch_poster_sources.py --scope Base1 --kind logos`: ignorierter Cache `tmp/poster-workspaces/Base1/sources/logo-de.png`, RGBA, 250 × 128 px, SHA-256 `666c69257f7d444d943bcc12098e97d48714bab742955d0efc7454bfb3948b1f`.
- Sichtbefund am Original: gelb-blauer Pokémon-Schriftzug über rotem Balken mit weißem **SAMMELKARTENSPIEL**; keine englische Unterzeile. Das Erscheinungsbild ist zusätzlich auf dem offiziellen deutschen Regelbuch `https://assets.pokemon.com/assets/cms2-de-de/pdf/trading-card-game/rulebook/swsh11_rulebook_de.pdf`, Seite 1, nachvollziehbar.
- Alle bisher anderen Sprachfassungen bleiben auf der bisherigen `en/base/base1/logo.png`-Quelle und `logo.png`; das ist eine bewusste Nichtänderung, keine Behauptung lokalisierter Logos für jene Sprachen.
- Druckgrenze: Die veröffentlichte Webgrafik ist nur 250 px breit. Im tatsächlichen 750 × 1050-px-Einleger `r1c2` ist die hochskalierte Beschriftung sichtbar weich. Ein Prüfversuch mit dem offiziellen Regelbuch lieferte nur die blaue Vektorkontur: Gelbfüllung und roter Balken sind Bestandteil eines Seitenbilds. Auch die [offizielle deutsche Detective-Pikachu-Kartenliste](https://assets.pokemon.com/assets/cms2-de-de/pdf/trading-card-game/checklist/det_web_cardlist_de.pdf) zeigt das richtige Logo nur klein im Seitenkopf; die extrahierten Bildobjekte enthalten keinen vollständigen hochaufgelösten Logo-Master. Diese unvollständigen Extrakte wurden verworfen und der offizielle PNG-Cache mit dem oben genannten Hash wiederhergestellt. Base1 bleibt für die PDF deaktiviert, bis eine authentische, ausreichend hoch aufgelöste deutsche Quelle vorliegt.
- Rechte: Pokémon-Logo und Wort-/Bildmarke gehören ihren Rechteinhabern. Die öffentliche Abrufbarkeit ist keine Nutzungs- oder Verkaufsfreigabe; diese Quelle dient hier nur der quellentreuen Lokalisierung des bestehenden Projekts.

Weder die heruntergeladene Bilddatei noch das Regelbuch werden ins Repository aufgenommen.
