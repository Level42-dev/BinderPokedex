# Entwicklungsstand: Git-Sicherung und Testgrenzen

Stand: 22.09.2026. Kein Release und keine Merge-Freigabe.

Die sieben bereits vorhandenen lokalen Commits bis `4abae76` wurden auf den
bestehenden Remote-Branch `codex/v10-refresh` übertragen. GitHub bestätigte
den Repository-Umzug; `origin` verweist nun auf `Level42-dev/BinderPokedex`.

## Prüfung des bisher uncommitteten Stands und nach P04-B-Übernahme

- Vollständiges Testverzeichnis: `python -m pytest scripts/tests -q`:
  **828 bestanden, 3 fehlgeschlagen, 1 übersprungen**; 174,59 Sekunden.
- Wiederholung nach P04-B-Übernahme: gleiches Ergebnis und dieselben drei
  Testnamen; 107,29 Sekunden. Keine neue Testregression durch die Übernahme.
- Separater unabhängiger Review: 93 fokussierte Tests bestanden; kein konkreter
  Fehler in den geprüften Source-Detail-/Skalierungsänderungen gefunden.
- Maschinengebundene Markdown-Verweise wurden in relative Projektverweise
  umgewandelt; lokale Skill-Verweise bleiben als reine Bezeichnungen erhalten.
- Quellen-Caches, Renderer-Einstellungen, temporäre Versuche, PDFs, ZIPs und
  lokale Release-Metadaten sind ausdrücklich nicht Teil des Staging-Umfangs.

Die drei bereits vor der P04-Übernahme bestehenden Fehler:

1. `test_promoted_production_posters_match_provenance_and_print_geometry`
2. `test_validation_rejects_pdf_artwork_not_named_by_provenance`
3. `test_every_checked_in_enabled_poster_remains_generation_current`

Die Prüfungen treffen auf absichtlich widerrufene historische Bildfreigaben
(zuerst Basis-Set). Deshalb schlagen die globale Bestandsfreigabe und die
Erwartung eines durchgehend aktuellen Bestands fehl; beim Negativtest greift
die Freigabeprüfung vor der erwarteten Routing-Fehlermeldung. Diese Grenzen
werden nicht durch wieder eingeschaltete Altfreigaben oder abgeschwächte Tests
verdeckt. P04 wird separat auf seine exakte neue Version geprüft.

## Sicherungsgrenze

Checkpoint `82b23a9` schützt Code, Konfiguration, Prüfberichte und regulär
übernommene textfreie Master samt Herkunftsnachweisen und wurde gepusht.
Commit `6b1513a` sichert zusätzlich den regulär übernommenen P04-B-Master.
Außerdem enthält er die exakten Master von Basis-Set B, ExGen3 Mega C, Dschungel E
und Stellarkrone B samt unverändert abgegrenzten Review-Entscheidungen im
[Review-Archiv](../../assets/reviewed-candidates/README.md). Das Archiv
aktiviert keine Produktionsroute und macht insbesondere Teilfreigaben nicht zu
Gesamtfreigaben. Die reguläre technische Übernahme dieser Kandidaten bleibt offen.
Auch `6b1513a` wurde gepusht; eine unabhängige Remote-Abfrage bestätigte exakt
`6b1513a7acc11df3d22fec28e5e229d26da64674`. Alle fünf Master entsprechen
bytegenau den gespeicherten Git-Blobs. Der abschließende Dokumentations-Commit
ändert keine Bildpixel, Produktionsdaten oder Renderer-Funktionen.

Dies ist keine vollständige Sicherung sämtlicher ignorierter Render-Versuche.
Deren Rohbilder, Protokolle, Versuchshilfen und reproduzierbare Quellen bleiben
lokal. Die bestehenden PDF-/ZIP-Release-Kandidaten wurden nicht verändert,
veröffentlicht oder in Git aufgenommen.

## Review-Abgrenzung

Der unabhängige Review bewertete die angesammelten Renderer-Änderungen und
die sichere Staging-Grenze, nicht die neue P04-Übernahme oder den vollständigen
Release. Die konkrete P04-Prüfung wird separat festgehalten. Kein erneuter
Worker-Zugriff war erforderlich; dessen Erreichbarkeit ist hier nicht geprüft.
