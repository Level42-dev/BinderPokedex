# P16/P37 Identity-Lock Candidates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Für P16 und P37 je einen quelltreuen, vollständig prüfbaren Fallback-Kandidaten erzeugen oder einen konkreten Ablehnungsgrund belegen, ohne produktive Poster oder PDFs zu verändern.

**Architecture:** Die vorhandene `identity_lock`-Pipeline wird nur per Scope-Override in ignorierten, unveränderlichen Renderjobs genutzt. Quellpixel-Audit, 300-dpi-Modell-Upscale und physische Kartenausschnitte liefern die technische Basis; ein separater visueller Gesamtbild-/Quellvergleich entscheidet, ob überhaupt etwas zur Nutzerabnahme gezeigt wird.

**Tech Stack:** Python 3, Pytest, Pillow, ComfyUI/FLUX.2 Klein 4B, bestehender isolierter Remote-Job-Transport.

**Spec:** `docs/superpowers/specs/2026-09-27-p16-p37-identity-lock-fallback-design.md`

## Global Constraints

- Nur `ExGen2/sections/primal` (P16) und `ME03` (P37); `joint_scene` bleibt überall sonst Standard. FLUX.2 Klein 4B statt nichtkommerziellem 9B.
- Bestehende aktive Master, Manifeste, `pdf.enabled` und PDFs bis zu einer getrennten Nutzerfreigabe unverändert lassen; kein stiller Promotion-Schritt.
- Bestehenden vollständigen, erreichbaren `renderer.local.yaml` des aktiven Workspaces wiederverwenden; private Zielwerte nicht in Git, Jobs, Provenienz oder Berichte kopieren.
- Jeden Job unveränderlich benennen, `run.json`, `comfyui.log` und **alle** Bilder zurückholen; Rohbild, 300-dpi-Master, neun 750 × 1050-px-Einleger und exakte Quellbilder prüfen.
- Keine automatische Seed-/Modellschleife; eine Nacharbeit erfordert einen dokumentierten konkreten Fehler und einen neuen Kandidatennamen. Vollständige Bildabnahme bleibt beim Nutzer.

## Review Focus

1. Fehlender/unvollständiger oder unerreichbarer Workspace-Marker muss vor GPU-Arbeit stoppen (`preflight_marker_complete_and_reachable`, Task 1).
2. Eine falsch zugeordnete Form oder Quelle muss vor dem Job scheitern (`preflight_exact_subject_hashes`, Task 1).
3. Fehlendes `run.json`, Log oder Output darf nicht als Erfolg gelten (`audit_returned_job_complete`, Tasks 2/3).
4. Ein technisch pixelgenauer, aber sichtbar aufgeklebter Charakter ist kein Freigabekandidat (`audit_grounding_and_occlusion`, Tasks 2/3).
5. Eine abgeschnittene Figur oder ein fremder Scope im Review-Paket muss die Übergabe blockieren (`audit_nine_cards_and_pairs`, Task 4).

---

### Task 1: Gemeinsame sichere Vorprüfung

**Files:**
- Read: `docs/reviews/2026-09-23-p16-stronger-oneshot.md`, `docs/reviews/2026-09-22-panorama-batch-review-notes.md`, beide Scope-Manifeste und Originalquellen.
- Create: `docs/reviews/2026-09-27-p16-p37-fallback-preflight.md` — nur nichtprivate Motive, Quellhashes, Einlegerpositionen und Fehlertypen.
- Test: `scripts/tests/test_poster_assets.py`, `scripts/tests/test_poster_agent_guidance.py`.

**Interfaces:**
- Produces: zwei getrennte unveränderliche Kandidaten-IDs mit geprüften Quell-/Modellhashes und Druckkarten-Zielpositionen; keine Produktionsänderung.

- [ ] **Step 1: Run baseline tests** `python -m pytest scripts/tests/test_poster_assets.py scripts/tests/test_poster_agent_guidance.py -q`; erwarteter Befund: die vorhandenen Fallback-/Agenten-Gatter bestehen. Fehler zuerst diagnostizieren, nicht durch Rendern übergehen.
- [ ] **Step 2: Check `preflight_marker_complete_and_reachable`** aktiven Workspace und ignorierten Marker auf vollständige lokale/remote Werte prüfen; konfigurierte Worker-Verbindung nur privat testen. Bei Fehlen/Unvollständigkeit/Unerreichbarkeit Operatorwahl anfordern und hier pausieren.
- [ ] **Step 3: Check `preflight_exact_subject_hashes`** für beide Scopes `fetch_poster_sources.py --kind cutouts`, Quellformen und Hashes gegen die dokumentierten Ziel-Pokémon prüfen. Keine Basisform stillschweigend als Mega-/Primal-Form verwenden.
- [ ] **Step 4: Record evidence and commit** nur den nichtprivaten Vorprüfbericht; Cache, Marker und Renderjob bleiben ignoriert.

### Task 2: P16-Fallback als isolierter Kandidat

**Files:**
- Read: `config/posters/ExGen2/sections/primal/poster.yaml`, `docs/POSTER_WORKFLOW.md`, `docs/POSTER_RENDER_WORKER.md`.
- Create ignored: `tmp/poster-workspaces/ExGen2/sections/primal/` und ein eigener unveränderlicher P16-Job samt Rückgaben.
- Create: `docs/reviews/2026-09-27-p16-identity-lock-review.md` — Hashes und konkrete Sichtbefunde; keine Freigabebehauptung.

**Interfaces:**
- Consumes: Vorprüfung aus Task 1.
- Produces: P16-Gesamtbild, neun echte Karten, zwei Quellpaare und vollständige lokale Run-/Log-Nachweise oder einen benannten Fehler.

- [ ] **Step 1: Prepare** mit dem aktuellen Manifest als Quelle, `--mode identity_lock` und bestehendem 4B-Modell/Seed; Scene- und Upscale-Stufe mit dem dokumentierten Worker-Verfahren auf demselben Host ausführen und deren Inputs/Outputs in einem scope-gebundenen, nicht überschreibbaren Jobnachweis versiegeln. Vor GPU-Arbeit einen trockenen Transport-/Pfadtest beider Stufen ausführen; kann der vorhandene Transport dies nicht, ohne Daten zu verlieren oder den aktiven Workspace zu ändern, hier mit Befund stoppen und einen gesonderten Transportplan vorlegen statt einen ungeprüften Teiljob auszuführen.
- [ ] **Step 2: Verify before GPU** Workflow-/Modell-/Quellhashes und `pdf.enabled`/Produktionsmaster-Hashes erneut lesen; erwarteter Befund: unverändert, Job vollständig und nur P16 betreffend.
- [ ] **Step 3: Execute and retrieve** ausschließlich auf dem konfigurierten Worker mit Loopback-ComfyUI; `audit_returned_job_complete` verlangt `run.json`, `comfyui.log`, Rohbild, 300-dpi-Master und alle Ausgaben. Bei Fehler kein automatischer Wiederholungslauf.
- [ ] **Step 4: Audit** `audit_grounding_and_occlusion`: Quellpixelprüfung, P16-Karten r3c1/r3c3 besonders auf vollständige Kyogre-/Groudon-Silhouetten, zusätzlich alle neun Karten, Schatten, Wasserkante/Lava, Kantenübergänge und durchgehende Szene. Defekte mit Hash und Ausschnitt notieren; nur eine gezielte neue Variante je belegtem Defekt.
- [ ] **Step 5: Commit** nur den Reviewbericht und etwaige geprüfte Transporttests/-code; keine Kandidatenbilder, Marker oder Logs.

### Task 3: P37-Fallback unabhängig prüfen

**Files:**
- Read: `config/posters/ME03/poster.yaml` und dokumentierte P37-B/C/D-Ablehnungen.
- Create ignored: `tmp/poster-workspaces/ME03/` und separater unveränderlicher P37-Job samt Rückgaben.
- Create: `docs/reviews/2026-09-27-p37-identity-lock-review.md` — Hashes und Sichtbefunde.

**Interfaces:**
- Consumes: geprüfter Transport aus Task 2 und eigene Scope-Quellen aus Task 1; P16-Bildfreigabe ist **keine** Vorbedingung.
- Produces: P37-Gesamtbild, neun Karten, jedes Quellpaar und vollständige Nachweise oder einen benannten Fehler.

- [ ] **Step 1: Prepare** eigenen `identity_lock`-Job mit ME03-Quellen/4B/Seed und vorab geprüften Zielkarten; nicht den P16-Job überschreiben oder dessen Quellen übernehmen.
- [ ] **Step 2: Execute/retrieve** auf dem im Marker konfigurierten Worker; `audit_returned_job_complete` verlangt sämtliche Logs, Metadaten und Ausgaben.
- [ ] **Step 3: Audit** `audit_nine_cards_and_pairs`: alle Karten, vor allem Mega-Zygardes linkes Emblem an r3c3, jedes exakte Pokémon-Quellpaar, Bodenkontakt, Schatten, Vordergrund und natürliche Landschaft prüfen. Ein intakter Pixel-Audit allein genügt nicht.
- [ ] **Step 4: Commit** nur den Reviewbericht, keine Kandidatenbilder oder privaten Laufdaten.

### Task 4: Entscheidungsmappe ohne Promotion

**Files:**
- Create ignored: `tmp/poster-workspaces/review-p16-p37/` mit Gesamtbildern und beschrifteten Karte-Quelle-Paaren.
- Modify: `docs/reviews/2026-09-27-p16-identity-lock-review.md`, `docs/reviews/2026-09-27-p37-identity-lock-review.md` nur für finale Hash-/Statusnachträge.

**Interfaces:**
- Consumes: beide Kandidatenberichte; produces einen genauen Vorschlag „zeigen“, „gezielt nacharbeiten“ oder „offen lassen“ pro Scope.

- [ ] **Step 1: Check `audit_nine_cards_and_pairs`** Kandidaten-ID und Quellhash auf jedem Paar, volle Karte links, exakte Quelle rechts, keine abgeschnittene Figur und keine fremden Scope-Dateien.
- [ ] **Step 2: Present only viable candidates** mit Panorama und allen Pokémon-Paaren zur ausdrücklichen Nutzerabnahme; bekannte kleine Abweichungen einzeln benennen. Abgelehnte Kandidaten bleiben als Befund dokumentiert, nicht als scheinbar freigegebene PDFs.
- [ ] **Step 3: Verify no production drift** `git status`, Master-/Manifest-/PDF-Hashes gegen Task-1-Basis und fokussierte Poster-Tests; erwarteter Befund: keine P16/P37-Produktionsänderung.
- [ ] **Step 4: Commit/push** nur nichtprivate finale Reviews und etwaige geprüfte Transportänderungen; auf menschliche Bildentscheidung warten, bevor ein neuer Promotions-/PDF-Schritt beginnt.
