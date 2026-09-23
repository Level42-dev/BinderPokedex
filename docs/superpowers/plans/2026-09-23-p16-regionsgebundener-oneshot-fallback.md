# P16 Regionsgebundener One-shot Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Einen einzigen, isolierten P16-One-shot mit pro Karte begrenztem Figurenbeitrag erzeugen und das exakte Gesamtbild samt neun Druckeinlegern und Quellen zur Sichtfreigabe vorlegen.

**Architecture:** Ein P16-spezifischer Vorbereiter baut aus den unveränderten, hashgebundenen Quellen zwei lokale Referenzzweige und einen rein landschaftlichen Zweig. Ein job-lokal geladener ComfyUI-Guider verwendet einen gemeinsamen latenten Zustand und Sampler; er begrenzt lokale Vorhersagedifferenzen und deren Attention-Zugriff auf die jeweilige Karten-Innenfläche. Der bestehende `joint_scene`-Graph und seine produktiven Metadatenpfade bleiben unberührt; der Pilot besitzt eine eigene, nicht promotierbare Laufakte.

**Tech Stack:** Python 3.11, pytest, Pillow, PyTorch, ComfyUI-Commit `87d23b81765161624889febfb3b81f19f3c8435b`, FLUX.2 Klein 4B, bestehender nativer MPS-Worker.

**Spec:** `docs/superpowers/specs/2026-09-23-regionsgebundener-oneshot-fallback-design.md`

## Global Constraints

- `joint_scene` bleibt Standard; `region_constrained_joint` ist nur ein ausdrücklicher P16-Pilot nach nachgewiesenen A/B/E/F-Fehlern, ohne automatischen Wechsel und ohne P37-Folgerender.
- Ein gemeinsamer latenter Zustand, ein Sampling-Verlauf, ein finaler VAE-Decode; kein `ImageCompositeMasked`, Inpainting, Einsetzen oder zweiter generativer Lauf.
- Physischer `standard_3x3`-Plan auf 1200 × 1664 Generierungspixeln; 32 px Innenabstand zu jeder P16-Kartenkante; 300 dpi und neun Einleger mit je 750 × 1050 px.
- Gleiche beiden Quell-Pokémon, Landschaftsvorgabe, 4B-Modellfamilie und Seed `653315091` wie Versuch B; vier Sampling-Schritte. Der neue Zweig braucht eigene Positionsreferenzen und deshalb einen neuen, dokumentierten Prompt-/Workflow-Hash.
- Modell `flux-2-klein-4b.safetensors` SHA-256 `ec3d4e733a771f61c052fb4856c48b336c55eaf2c65487c2a1faeb9bbda7a343`, Encoder `qwen_3_4b.safetensors` SHA-256 `6c671498573ac2f7a5501502ccce8d2b08ea6ca2f661c458e708f36b36edfc5a`, VAE `flux2-vae.safetensors` SHA-256 `d64f3a68e1cc4f9f4e29b6e0da38a0204fe9a49f2d4053f0ec1fa1ca02f9c4b5`.
- Vor GPU-Arbeit aktiven ignorierten `renderer.local.yaml` prüfen und bei vollständiger, erreichbarer Konfiguration wiederverwenden; weder Marker noch private Verbindungswerte in Job, Provenienz, Commit oder Bericht übernehmen. ComfyUI bindet nur an Loopback.
- Pilot und Rückgaben bleiben unter `tmp/oneshot-trials/`; produktiver P16-Master, andere Motive, PDFs und bisheriger Graph werden nicht überschrieben. `run.json`, `comfyui.log` und sämtliche Ausgabebilder kommen zurück.
- Das zurückgeholte `run.json` kann Maschinenidentität enthalten: Nur Hashes und bereinigte, relative Artefaktbezüge dürfen in den versionierten Befund, nie der Rohinhalt oder private Worker-Pfade.
- Kein erfolgreicher Prozess gilt als Bildfreigabe. Bei Hook-, Hash-, Speicher-, Karten- oder Quellenfehlern abbrechen, nicht still auf weiche Masken oder mehrstufige Bildmontage wechseln.

## Review Focus

1. Eine fehlende oder geänderte ignorierte A/B/E/F-Prüfdatei muss die P16-Eignung **vor** der Job-Erstellung verweigern (Task 1).
2. Ein Pfad-Ausbruch, Symlink oder manipuliertes Byte in der job-lokalen Erweiterung muss **vor** ComfyUI-Start scheitern (Task 3).
3. Texttokens dürfen im globalen Zweig keinen Figurenbereich als Key lesen und lokale Referenztokens dürfen außerhalb der zugehörigen Karte nicht gelesen werden; sonst entsteht ein indirektes Leck (Task 2 und 4).
4. Abweichende Token-Reihenfolge, Referenzanzahl, latente Maße oder überlappende Regionen müssen fehlschlagen, statt eine falsch ausgerichtete Maske anzuwenden (Task 2 und 4).
5. Eine auf MPS nicht unterstützte additive Maske oder ein zu hoher Masken-Speicherbedarf muss ohne Full-Render/Promotion als technischer Fehlschlag gemeldet werden (Task 4 und 6).

---

## Dateigrenzen

- `docs/reviews/2026-09-23-p16-region-fallback-evidence.json`: versionierter Eignungsnachweis mit den vier tatsächlich gescheiterten Artefakthashes und P16-Kartenbindung; keine Maschinenpfade.
- `scripts/poster_assets/region_joint/eligibility.py`: nur Eignung, Dateihashes und sicheren ignorierten Pilotbereich prüfen.
- `scripts/poster_assets/region_joint/geometry.py`: physische Karten- und Latent-Regionen ohne Bildmodell berechnen.
- `scripts/poster_assets/region_joint/comfy_extension/`: selbstständige, mit dem Job kopierte Attention-/Guider-Erweiterung; keine Imports aus dem Worker-Checkout.
- `scripts/poster_assets/region_joint/prepare_p16_trial.py`: alleiniger Opt-in-Einstieg für P16-Prompt, Referenzen, Workflow und unveränderlichen Job.
- `scripts/poster_assets/region_joint/review_p16_trial.py`: nur Rückgabe-, 300-dpi-, Zuschnitt- und Quellenakten erzeugen; nie promotieren.
- `scripts/poster_assets/render_job.py`: optionales hashgebundenes Erweiterungsformat und isolierte ComfyUI-Startkonfiguration; alte Jobs bleiben Format 1 und starten unverändert.
- `scripts/poster_assets/review_batch_source_detail.py`: optionaler ignorierter Arbeitsordner für genau einen Trial-Kontext; Standardverhalten bleibt identisch.
- `scripts/tests/test_region_joint_*.py`, `scripts/tests/test_render_job.py`, `scripts/tests/test_review_batch_source_detail.py`: Tests an der jeweils verantwortlichen Grenze.

### Task 1: P16-Eignung und isolierter Arbeitsbereich

**Files:**
- Create: `docs/reviews/2026-09-23-p16-region-fallback-evidence.json`
- Create: `scripts/poster_assets/region_joint/__init__.py`
- Create: `scripts/poster_assets/region_joint/eligibility.py`
- Modify: `scripts/poster_assets/review_batch_source_detail.py:138-174`
- Test: `scripts/tests/test_region_joint_eligibility.py`
- Test: `scripts/tests/test_review_batch_source_detail.py`

**Interfaces:**
- Consumes: bestehende `tmp/oneshot-trials/p16-batch-*/review/{poster-de.png,evidence.json}`, `trial_manifest_bundle()`.
- Produces: `require_p16_evidence(root: Path, evidence_path: Path) -> str` (SHA-256 der Eignungsakte) und `trial_manifest_bundle(..., isolated_work_dir: Path | None = None)`.

- [ ] **Step 1: Failing tests schreiben.** Vier Hashbindungen müssen gültig sein; ein fehlender Bogen wirft `FileNotFoundError`, geänderte Bytes, falscher Scope, fremder Trial-Pfad oder leere Fehlerbegründung `ValueError`. Der neue `isolated_work_dir` muss innerhalb `tmp/oneshot-trials/<variant>/` liegen und den bisherigen `bundle.work_dir` nur im Kontext ersetzen.

```python
def make_p16_fixture_with_four_failed_trials(root):
    records = []
    for variant in REQUIRED_VARIANTS:
        review = root / "tmp/oneshot-trials" / variant / "review"
        review.mkdir(parents=True)
        (review / "poster-de.png").write_bytes(variant.encode())
        (review / "evidence.json").write_bytes((variant + " evidence").encode())
        records.append({"variant": variant, "failure": "physical card cut",
                        "poster_sha256": sha256_file(review / "poster-de.png"),
                        "evidence_sha256": sha256_file(review / "evidence.json")})
    path = root / "docs/reviews/p16-region-evidence.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"schema_version": 1, "scope": P16_SCOPE,
                                "failed_trials": records}), encoding="utf-8")
    return path

def test_p16_evidence_rejects_changed_review_image(tmp_path):
    record = make_p16_fixture_with_four_failed_trials(tmp_path)
    assert len(require_p16_evidence(tmp_path, record)) == 64
    (tmp_path / "tmp/oneshot-trials/p16-batch-20260922-b/review/poster-de.png").write_bytes(b"changed")
    with pytest.raises(ValueError, match="poster SHA-256 mismatch"):
        require_p16_evidence(tmp_path, record)

def test_trial_bundle_keeps_canonical_work_dir(self):
    trial_manifest = self.build()
    isolated = self.root / "tmp/oneshot-trials/p99-region-a/prepared"
    roots = {"poster_assets": self.root / "assets/posters",
             "poster_configs": self.root / "config/posters",
             "poster_workspaces": self.root / "tmp/poster-workspaces"}
    with trial_manifest_bundle(self.scope, trial_manifest,
                               repository_root=self.root, isolated_work_dir=isolated):
        self.assertEqual(poster_io.poster_bundle(self.scope, **roots).work_dir, isolated)
    self.assertEqual(poster_io.poster_bundle(self.scope, **roots).work_dir.name, "comfyui_poster")
```

Im bestehenden `test_review_batch_source_detail.py` dafür `from scripts.poster_assets import poster_io` ergänzen; `self.build()` und `self.root` kommen aus der vorhandenen Testklasse.

- [ ] **Step 2: Rot prüfen.** `venv/bin/python -m pytest scripts/tests/test_region_joint_eligibility.py scripts/tests/test_review_batch_source_detail.py -q`; die neuen Tests scheitern an fehlenden Funktionen.
- [ ] **Step 3: Minimal implementieren.** Die Akte enthält die vier Varianten A/B/E/F, je einen Bogen- und Evidenz-SHA sowie konkrete Zuschnitt-/Anatomiefehler. `require_p16_evidence` löst Pfade nur unter dem erwarteten Trial-Root auf, hasht beide Dateien und akzeptiert nur `ExGen2/sections/primal`. `trial_manifest_bundle` prüft den isolierten Pfad vor `replace(bundle, work_dir=...)`.

```python
P16_SCOPE = "ExGen2/sections/primal"
REQUIRED_VARIANTS = (
    "p16-batch-20260922-a", "p16-batch-20260922-b",
    "p16-batch-20260922-e", "p16-batch-20260923-f",
)

def require_p16_evidence(root: Path, evidence_path: Path) -> str:
    record = json.loads(evidence_path.read_text(encoding="utf-8"))
    trials = record.get("failed_trials")
    if (record.get("schema_version") != 1 or record.get("scope") != P16_SCOPE
            or not isinstance(trials, list) or len(trials) != 4
            or tuple(x.get("variant") for x in trials if isinstance(x, dict)) != REQUIRED_VARIANTS):
        raise ValueError("P16 fallback evidence is incomplete")
    for trial in trials:
        base = (root / "tmp/oneshot-trials" / trial["variant"] / "review").resolve()
        if not base.is_relative_to((root / "tmp/oneshot-trials").resolve()) or not isinstance(trial.get("failure"), str) or not trial["failure"].strip():
            raise ValueError("Unsafe or unexplained P16 trial")
        for name, field in (("poster-de.png", "poster_sha256"), ("evidence.json", "evidence_sha256")):
            if sha256_file(base / name) != trial[field]:
                raise ValueError(f"{name} SHA-256 mismatch")
    return sha256_file(evidence_path)
```

Die echte Akte verwendet für A/B/E/F der Reihe nach die Bogen-Hashes
`32df9b54f87b2ed0ba298073d246f653944ab9b3c1b6c5fde7039b2e6ca024aa`,
`34ddb7ce161ed5dc300f3c0484e7c231a1efb1b4bdf556c963281c2dc71e2dfc`,
`df574615aea53df57de4e13362d92242dbdd880af47ea08b65aa87dce9dd4e59`,
`53f0269bb9a5d713bd3cd5975eac1772bd241f198a611e0bff638932aa5c61e9`
und die Evidenz-Hashes
`be30251cb66e77c4ebb8bea0704a77a7be14f7fccad763e170cda1bbf6a347cf`,
`26817447065da72d6d23210d5d6a05845d66b3775e0cd1503bf2e97d86929bff`,
`4b837de12c0fbec5ecfda645e07059a780c7f1fc0356e3a992f83beb34b64a0e`,
`55e449738ea2f90daaea8a2b1673b575eac81226e4ded333226c997fc9ade881`.
Die Fehlertexte beschreiben A/B-Grenzübertritt, E-Figurenverlagerung und
F-Flossen-/Schwanzübertritt in r3c2.

- [ ] **Step 4: Grün prüfen.** Dieselben Tests bestehen; ein zusätzlicher Test belegt, dass der bisherige Kontext-Aufruf ohne `isolated_work_dir` dasselbe Arbeitsverzeichnis wie vor der Änderung liefert.
- [ ] **Step 5: Commit.** Nur diese Akte und Dateien `git add`-en; `git diff --cached --check`, dann `git commit -m "test: gate P16 regional fallback on failed trials"`.

### Task 2: Exakte Kartenregionen und Attention-Sperre

**Files:**
- Create: `scripts/poster_assets/region_joint/geometry.py`
- Create: `scripts/poster_assets/region_joint/comfy_extension/region_math.py`
- Test: `scripts/tests/test_region_joint_geometry.py`
- Test: `scripts/tests/test_region_joint_attention.py`

**Interfaces:**
- Consumes: `build_source_layout("standard_3x3", width_px=1200, height_px=1664)` und die bindenden Karten `10077 -> r3c1`, `10078 -> r3c3`.
- Produces: `build_p16_region_contract() -> dict`, `latent_weight(rect: tuple[int,int,int,int], latent_hw: tuple[int,int]) -> torch.Tensor`, `attention_bias(text_count: int, main_hw: tuple[int,int], reference_counts: tuple[int,...], protected_main: torch.Tensor, allowed_reference_queries: torch.Tensor | None, *, dtype: torch.dtype, device: torch.device) -> torch.Tensor`.

- [ ] **Step 1: Failing Geometrie- und Lecktests schreiben.** Source-Spans sind `x=(0,380),(410,790),(820,1200)` und `y=(0,535),(565,1099),(1129,1664)`; Druck-Spans bei 300 dpi sind `x=(0,750),(809,1559),(1618,2368)` und `y=(0,1050),(1109,2159),(2218,3268)`. Daraus folgen P16-Innenrechtecke links `(32,1161,348,1632)` und rechts `(852,1161,1168,1632)`. An den Schnittlinien gilt exakt Null-Gewicht; Text-/Außenabfragen dürfen keine geschützten Keys sehen.

```python
def test_p16_regions_are_inside_physical_cards():
    contract = build_p16_region_contract()
    assert contract["left"]["inner_xyxy"] == [32, 1161, 348, 1632]
    assert contract["right"]["inner_xyxy"] == [852, 1161, 1168, 1632]
    assert contract["latent_hw"] == [208, 150]
    assert contract["token_hw"] == [104, 75]

def test_text_and_other_card_queries_cannot_read_subject_keys():
    protected = torch.tensor([[False, True, False]])
    own_card = torch.tensor([[False, True, False]])
    bias = attention_bias(1, (1, 3), (1, 1), protected_main=protected,
                          allowed_reference_queries=own_card, dtype=torch.float32,
                          device=torch.device("cpu"))
    assert torch.isneginf(bias[0, 2])     # Text -> geschützter Bildtoken
    assert torch.isneginf(bias[1, -1])    # Fremdkartenbild -> Referenztoken
    assert bias[2, -1] == 0                # Eigene Karte -> eigene Referenz
```

- [ ] **Step 2: Rot prüfen.** `venv/bin/python -m pytest scripts/tests/test_region_joint_geometry.py scripts/tests/test_region_joint_attention.py -q` scheitert erwartungsgemäß.
- [ ] **Step 3: Geometrie und pure Torch-Mathematik implementieren.** `build_source_layout` statt Bilddritteln; Guard `ceil(0.08 * card.width / 16) * 16`; `16` Generierungspixel pro FLUX.2-Bildtoken; `8` pro latentem Pixel. Additive Attention-Maske mit `0`/`-inf` und Form `[T+M+R,T+M+R]`: globale Text- und Fremdkarten-Queries lesen keine geschützten Main-Keys; lokale Referenz-Keys sind nur für Main-Queries ihrer eigenen Region offen. Jede Query behält mindestens ihren eigenen Key. Eingabeformen, Tokenzahl und Nichtüberlappung vor Tensor-Allokation prüfen; pro Maske höchstens 384 MiB, alle drei Masken zusammen höchstens 1 GiB.

```python
def attention_bias(text_count, main_hw, reference_counts, protected_main,
                   allowed_reference_queries, *, dtype, device):
    main_count = math.prod(main_hw)
    total = text_count + main_count + sum(reference_counts)
    if total * total * torch.empty((), dtype=dtype).element_size() > 384 * 1024**2:
        raise MemoryError("Region attention mask exceeds 384 MiB")
    bias = torch.zeros((total, total), dtype=dtype, device=device)
    main = torch.arange(text_count, text_count + main_count, device=device)
    outside = main[~protected_main.flatten()]
    protected_keys = main[protected_main.flatten()]
    bias[torch.cat((torch.arange(text_count, device=device), outside))[:, None], protected_keys] = -torch.inf
    if reference_counts:
        ref_keys = torch.arange(text_count + main_count, total, device=device)
        denied = main[~allowed_reference_queries.flatten()]
        bias[torch.cat((torch.arange(text_count, device=device), denied))[:, None], ref_keys] = -torch.inf
    return bias
```

`latent_weight` rasterisiert nur den Innerbereich in ein `[1,1,H,W]`-Tensor;
die ersten und letzten zwei Latent-Pixel an jeder Innenkante laufen linear auf
null zu.
Außerhalb der vier Innergrenzen sind alle Werte **exakt** null. Prüfe zusätzlich
`torch.max(left_weight + right_weight) <= 1`.

- [ ] **Step 4: Grün und Gegenproben.** Teste zusätzlich überlappende Regionen, unpassende Grid-Größe, zu hohe Speicherabschätzung und `torch.nn.functional.scaled_dot_product_attention` mit kleiner additiver Maske auf CPU. `venv/bin/python -m pytest scripts/tests/test_region_joint_geometry.py scripts/tests/test_region_joint_attention.py -q` muss bestehen.
- [ ] **Step 5: Commit.** `git diff --cached --check`; `git commit -m "feat: bind P16 subject influence to print-safe regions"`.

### Task 3: Hashgebundene Job-Erweiterung ohne Worker-Installation

**Files:**
- Modify: `scripts/poster_assets/render_job.py:89-211,241-352,357-381`
- Test: `scripts/tests/test_render_job.py`

**Interfaces:**
- Consumes: `prepare_job(workflow_path, job_dir, input_specs, model_specs, *, extension_source: Path | None = None)`.
- Produces: Format-2-Jobs mit `extensions/binder_region_joint/` und Dateihashes; Format-1-Jobs sowie deren Startkommando bleiben unverändert. `run_job` erzeugt die absolute ComfyUI-Pfadkonfiguration nur in einem automatisch entfernten temporären Verzeichnis.

- [ ] **Step 1: Failing Jobtests ergänzen.** Teste unverändertes Format 1, Format 2 mit vollständig gehashten `.py`-Dateien, Hashänderung, Symlink, `../`-Pfad und doppelten Namen. Mocke den Startbefehl: nur Format 2 erhält `--extra-model-paths-config`, `--disable-all-custom-nodes`, `--whitelist-custom-nodes binder_region_joint`; im `job.json` stehen keine absoluten Pfade.

```python
def test_extension_job_rejects_tampering(tmp_path):
    workflow = tmp_path / "workflow.json"
    workflow.write_text(json.dumps({"1": {"class_type": "SaveImage", "inputs": {}}}))
    extension = tmp_path / "binder_region_joint"
    extension.mkdir()
    (extension / "__init__.py").write_text("NODE_CLASS_MAPPINGS = {}")
    manifest = prepare_job(workflow, tmp_path / "job", [], [], extension_source=extension)
    assert json.loads(manifest.read_text())["format_version"] == 2
    (tmp_path / "job/extensions/binder_region_joint/__init__.py").write_text("changed")
    with pytest.raises(ValueError, match="extension SHA-256 mismatch"):
        validate_job(tmp_path / "job", tmp_path / "models")
```

- [ ] **Step 2: Rot prüfen.** `venv/bin/python -m pytest scripts/tests/test_render_job.py -q` zeigt nur neue Fehltests.
- [ ] **Step 3: Erweiterungsformat minimal einbauen.** Erlaube genau einen Verzeichnisnamen `binder_region_joint` aus einer kanonischen, symlinkfreien Quelle; kopiere nur explizit geprüfte `.py`-Dateien und hashe sie. `validate_job` erlaubt ausschließlich Formate 1/2 und prüft jeden Hash vor dem Serverstart. Für Format 2 schreibe zur Laufzeit in `TemporaryDirectory` eine YAML-Datei, deren `custom_nodes` auf `job_dir/extensions` zeigt; übergib sie über die am gepinnten Worker bestätigte `--extra-model-paths-config`-Option. Wenn im normalen Worker-`custom_nodes` bereits ein gleichnamiger Ordner liegt, brich wegen Whitelist-Kollision ab. Der gepinnte Worker unterstützt `--whitelist-custom-nodes`; prüfe vor Queueing `/object_info/RegionConstrainedJointGuider` und brich bei fehlendem Knoten ab.

```python
if manifest["format_version"] == 2:
    with contextlib.ExitStack() as stack:
        temporary = stack.enter_context(tempfile.TemporaryDirectory(prefix="binder-region-node-"))
        config = Path(temporary) / "extra_model_paths.yaml"
        config.write_text(yaml.safe_dump({"pilot": {"custom_nodes": str(job_dir / "extensions")}}))
        command += ["--extra-model-paths-config", str(config),
                    "--disable-all-custom-nodes", "--whitelist-custom-nodes", "binder_region_joint"]
        # Der vorhandene Popen/Queue/finally-Block von run_job bleibt innerhalb
        # dieses Kontexts; Format 1 verwendet denselben Block ohne Zusatzflags.
```

- [ ] **Step 4: Grün und Worker-Quellabgleich.** Format-1-Test muss bytegleich bleiben. Prüfe lesend die gepinnten `main.py`, `comfy/cli_args.py`, `utils/extra_config.py` und `nodes.py` auf Ladepfad und Node-Registrierung; keine Installation. `venv/bin/python -m pytest scripts/tests/test_render_job.py -q` muss bestehen.
- [ ] **Step 5: Commit.** `git diff --cached --check`; `git commit -m "feat: load hashed regional guider per render job"`.

### Task 4: Ein Sampler, drei Vorhersagen, gesperrte Attention

**Files:**
- Create: `scripts/poster_assets/region_joint/comfy_extension/__init__.py`
- Create: `scripts/poster_assets/region_joint/comfy_extension/guider.py`
- Create: `scripts/poster_assets/region_joint/comfy_extension/mixer.py`
- Test: `scripts/tests/test_region_joint_guider.py`

**Interfaces:**
- Consumes: `region_math.attention_bias`, `region_contract` als JSON-Knoten-Eingabe, ComfyUI `CFGGuider`/`sampling_function`/`attn1_patch` des gepinnten Stands.
- Produces: Custom Node `RegionConstrainedJointGuider` mit Inputs `model`, `global_conditioning`, `left_conditioning`, `right_conditioning`, `region_contract` und Output `GUIDER`.

- [ ] **Step 1: Failing CPU-Tests schreiben.** `mix_predictions(base, (left,right), (left_weight,right_weight))` lässt Außenpixel exakt `base`, weist bei Überlappung oder nicht-finiten Werten ab und verwendet dieselbe `x`-/`timestep`-Instanz für alle drei Branch-Aufrufe. Ein Fake-Model-Options-Test belegt, dass beide FLUX-Blockarten den Patch erhalten, lokale Referenzzählung nur `(position, detail)` ist und ein nicht aufgerufener Patch einen Fehler auslöst.

```python
def test_zero_weight_outside_is_exact_global():
    global_prediction = torch.ones((1, 1, 4, 4))
    local = torch.full_like(global_prediction, 7)
    weight = torch.zeros_like(global_prediction)
    weight[..., 1:3, 1:3] = 1
    result = mix_predictions(global_prediction, (local,), (weight,))
    assert torch.equal(result[..., 0, :], global_prediction[..., 0, :])
    assert torch.equal(result[..., 1:3, 1:3], local[..., 1:3, 1:3])
```

- [ ] **Step 2: Rot prüfen.** `venv/bin/python -m pytest scripts/tests/test_region_joint_guider.py -q` scheitert an den fehlenden Funktionen.
- [ ] **Step 3: Guider implementieren.** Der Node erzeugt eine `CFGGuider`-Unterklasse und ruft `inner_set_conds` mit genau `global`, `left`, `right`. `predict_noise` berechnet dreimal `sampling_function(self.inner_model, x, timestep, None, self.conds[branch], 1.0, model_options=branch_options, seed=seed)`. `branch_options` klont vorhandene Modelloptionen und hängt **einen** `attn1_patch` an; vorhandene konfliktierende Attention-Patches sind für den Pilot verboten. Der Patch prüft bei jedem Double-/Single-Stream-Aufruf `img_slice`, `reference_image_num_tokens`, `q.shape[2]` und die erwarteten `[T, Main, Ref]`-Grenzen; im globalen Zweig sind null Referenzen, lokal genau zwei. Er liefert eine additive `attn_mask` zurück. Der Guider prüft nach jeder Vorhersage, dass der Patch tatsächlich aufgerufen wurde, und mischt nur die eingerückten lokalen Differenzen.

```python
def predict_noise(self, x, timestep, model_options={}, seed=None):
    predictions = []
    for branch in ("global", "left", "right"):
        patch = RegionAttentionPatch(self.regions, branch)
        options = with_region_patch(model_options, patch)
        predictions.append(comfy.samplers.sampling_function(
            self.inner_model, x, timestep, None, self.conds[branch], 1.0,
            model_options=options, seed=seed,
        ))
        if patch.calls == 0:
            raise RuntimeError("Region attention patch was not invoked")
    return mix_predictions(predictions[0], predictions[1:], self.latent_weights)
```

`with_region_patch(model_options: dict, patch: RegionAttentionPatch) -> dict`
verwendet `comfy.model_patcher.create_model_options_clone`, lehnt bereits
vorhandene `transformer_options.patches.attn1_patch` für diesen Pilot ab und
setzt allein `[patch]`. `mix_predictions` prüft Form, Endlichkeit und
Gewichtsüberlappung und rechnet `base + left_weight*(left-base) +
right_weight*(right-base)`; Außenpixel bleiben wegen Nullgewicht exakt `base`.
Der Guider erzeugt `self.latent_weights` beim Initialisieren aus den beiden
JSON-Innenrechtecken mit `latent_weight(rect, (208, 150))`; fremde Maße führen
zu `ValueError` statt stiller Neuskalierung.
Vor dem ersten Schritt addiert der Guider die prognostizierten Größen aller
drei Attention-Masken und lehnt mehr als 1 GiB ab.

- [ ] **Step 4: Grün und Pinned-API-Smoke.** CPU-Tests bestehen. Auf dem konfigurierten Worker: Erweiterung nur job-lokal laden, `/object_info/RegionConstrainedJointGuider` abfragen und eine kleine additive SDPA-Maske auf MPS mit dem nativen Runtime-Python prüfen; kein Modell-Download und noch kein P16-Bildlauf. Fehlende Signatur oder MPS-Maske beendet den Pilot vor dem Full-Render.
- [ ] **Step 5: Commit.** `git diff --cached --check`; `git commit -m "feat: add one-pass region-constrained guider"`.

### Task 5: Unveränderlichen P16-Pilotjob vorbereiten

**Files:**
- Create: `scripts/poster_assets/region_joint/prepare_p16_trial.py`
- Modify: `scripts/poster_assets/prepare_comfyui_poster.py:292-331` (optionale Skalen für einzelne Positionsreferenzen; Default unverändert)
- Test: `scripts/tests/test_region_joint_trial.py`
- Test: `scripts/tests/test_poster_assets.py`

**Interfaces:**
- Consumes: `require_p16_evidence`, `build_p16_region_contract`, `trial_manifest_bundle(... isolated_work_dir=...)`, `build_trial_manifest`, `build_joint_scene_references`, `build_individual_spatial_joint_references`, `prepare_job`.
- Produces: `build_p16_workflow(global_prompt: str, local_prompts: tuple[str,str], regions: dict) -> dict[str, object]` und `prepare_p16_trial(variant: str, root: Path) -> Path` (Rückgabe: Job-Verzeichnis mit `workflow_api.json`, `job.json`; `trial_provenance.json` bleibt eine Ebene höher). Alle Dateien nur unter `tmp/oneshot-trials/<variant>/`.

- [ ] **Step 1: Failing Graph- und Isolationstests schreiben.** Standard-Workflow-Fixture `workflow_api_joint_scene_regional_identity_joint_0p25mp_123.json` und ein `spatial_source_detail_joint`-Snapshot müssen unverändert bleiben. Pilotgraph: ein `SamplerCustomAdvanced`, ein `VAEDecode`, ein `EmptyFlux2LatentImage`, ein `RegionConstrainedJointGuider`, genau zwei `ReferenceLatent`-Ketten pro Pokémon, null `ConditioningSetMask`/`ImageCompositeMasked`/`VAEEncodeForInpaint`. Globale Konditionierung enthält weder Cutout-Referenz noch die Artennamen; lokal enthält jede nur die eigene Positions- und Detailreferenz samt gebundenen Quellmerkmalen. Ein bestehender Variant-Ordner darf nicht überschrieben werden.

```python
def test_p16_graph_has_one_sampler_and_isolated_subject_references():
    workflow = build_p16_workflow("empty coastal landscape", ("left source", "right source"),
                                   build_p16_region_contract())
    classes = [node["class_type"] for node in workflow.values()]
    assert classes.count("SamplerCustomAdvanced") == 1
    assert classes.count("VAEDecode") == 1
    assert classes.count("RegionConstrainedJointGuider") == 1
    assert not ({"ConditioningSetMask", "ImageCompositeMasked", "VAEEncodeForInpaint"} & set(classes))
```

- [ ] **Step 2: Rot prüfen.** `venv/bin/python -m pytest scripts/tests/test_region_joint_trial.py scripts/tests/test_poster_assets.py -q` zeigt die neuen Fehltests.
- [ ] **Step 3: Job-Builder implementieren.** `build_trial_manifest` friert P16-Quelltraits unter einem neuen ignorierten Variantnamen ein; der Pilot vergleicht dessen Szene, Quellhashes und beide `0.55`-Skalen mit Versuch B und setzt danach ausschließlich `artwork.generation.reference_mode: region_constrained_joint`. Bei Drift abbrechen. Im isolierten `work_dir` entstehen `identity_reference_{1,2}.png` ohne Cast und `individual_spatial_reference_{1,2}.png` mit denselben P16-B-Skalen; Original-Cutout-Bytes bleiben unverändert. Globalen Landschaftsprompt aus `build_regional_joint_scene_prompts` ohne Bildreferenz verwenden; lokale Prompts benennen Bild 1 als Position und Bild 2 als unverändertes anatomisches Detail und fügen die hashgebundenen `source_details`-Traits hinzu. P16-Modelle/Seed/2 MP/4 Schritte sind die oben gepinnten. Baue die Zweige separat und verbinde sie nur am eigenen Guider. `trial_provenance.json` enthält Modus, Vertragsversion, Kartenrechtecke, relative Manifest-/Masterpfade, die **vorherigen** P16-/P37-Produktivhashes, Prompt-/Quell-/Extension-/Workflow-/Modellhashes, jedoch keine absoluten Worker-Pfade.

```python
workflow["70"] = node("RegionConstrainedJointGuider", model=["1", 0],
    global_conditioning=[global_id, 0], left_conditioning=[left_final_id, 0],
    right_conditioning=[right_final_id, 0], region_contract=json.dumps(regions, sort_keys=True))
workflow["71"] = node("SamplerCustomAdvanced", noise=["8", 0], guider=["70", 0],
    sampler=["10", 0], sigmas=["7", 0], latent_image=["6", 0])
workflow["72"] = node("VAEDecode", samples=["71", 0], vae=["3", 0])
```

- [ ] **Step 4: Grün und Freeze prüfen.** `venv/bin/python -m pytest scripts/tests/test_region_joint_trial.py scripts/tests/test_poster_assets.py -q`; vor und nach Vorbereitung `git status --short` sowie Hashes des produktiven P16-Masters vergleichen. `render_job.py validate` muss die Erweiterung und alle vier Referenzbilder bytegenau akzeptieren. Keinen GPU-Lauf starten.
- [ ] **Step 5: Commit.** Nur Code und Tests, nicht ignorierte Manifest-/Job-/Quellbilder: `git diff --cached --check`; `git commit -m "feat: prepare isolated P16 regional one-shot trial"`.

### Task 6: Einmal rendern, alle neun Karten prüfen, Ergebnis übergeben

**Files:**
- Create: `scripts/poster_assets/region_joint/review_p16_trial.py`
- Test: `scripts/tests/test_region_joint_review.py`
- Create on real attempt only: `docs/reviews/2026-09-23-p16-region-pilot.md`

**Interfaces:**
- Consumes: versiegelter Format-2-Job, zurückgeholte `run.json`, `comfyui.log`, alle ComfyUI-Bilder, P16-Quellen und bestehende Funktionen `resize_artwork_to_dpi`, `finalize`, `slice_poster`.
- Produces: `verify_print_crops(cards_dir: Path) -> dict[str, str]`, `audit_p16_trial(trial_dir: Path, root: Path) -> dict`, ignoriertes `review/evidence.json`, textfreier 300-dpi-Master, deutsches Panorama, neun exakte Karten, zwei Quelle/Karte-Vergleiche und einen knappen versionierten Befund; **keine Promotion**.

- [ ] **Step 1: Failing Rückgabe- und Drucktests schreiben.** Fehlende `run.json`, Log, Ausgabebilder oder Quellhashes verweigern Review. Exakte 300-dpi-Endpunkte und neun 750 × 1050 px Karten werden technisch geprüft; der r3c2-Gliedmaßenbefund gehört zur Sichtprüfung in Schritt 7. Ein Test mit veränderter Produktiv-Masterdatei muss vor Ergebnisübergabe fehlschlagen.

```python
def test_review_requires_all_nine_exact_cards(tmp_path):
    cards = tmp_path / "cards"
    cards.mkdir()
    for row in range(1, 4):
        for col in range(1, 4):
            Image.new("RGB", (750, 1050)).save(cards / f"card_r{row}_c{col}.png")
    (cards / "card_r3_c2.png").unlink()
    with pytest.raises(FileNotFoundError, match="card_r3_c2"):
        verify_print_crops(cards)
```

- [ ] **Step 2: Rot prüfen.** `venv/bin/python -m pytest scripts/tests/test_region_joint_review.py -q` scheitert an der fehlenden Review-Funktion.
- [ ] **Step 3: Review-Funktion implementieren.** Rohbild-/Jobhashes prüfen; mit bestehender Lanczos-Funktion auf `build_print_layout("standard_3x3", 300)` normalisieren, lokalisierten Bogen erzeugen und mit `slice_poster` alle neun physischen Einleger schneiden. `evidence.json` bindet jede Karte, beide Cutouts, Vollbild, Master, Workflow, Guider-Version und Rückgabelog an SHA-256. Ein kleines Gegenüber `source`/`r3c1` und `source`/`r3c3` dient nur der Prüfung, verändert nicht das Panorama.

```python
def verify_print_crops(cards_dir: Path) -> dict[str, str]:
    expected = [cards_dir / f"card_r{row}_c{col}.png"
                for row in range(1, 4) for col in range(1, 4)]
    for card in expected:
        if not card.is_file():
            raise FileNotFoundError(card.name)
        with Image.open(card) as image:
            if image.size != (750, 1050):
                raise ValueError(f"Incorrect print crop: {card.name}")
    return {card.name: sha256_file(card) for card in expected}

def audit_p16_trial(trial_dir: Path, root: Path) -> dict:
    for name in ("run.json", "comfyui.log"):
        if not (trial_dir / name).is_file():
            raise FileNotFoundError(name)
    provenance = json.loads((trial_dir.parent / "trial_provenance.json").read_text(encoding="utf-8"))
    for item in provenance["production_masters_before"]:
        relative = safe_relative_path(item["path"], field="production master path")
        verify_file(root / relative, item["sha256"], label="production master")
    run = json.loads((trial_dir / "run.json").read_text(encoding="utf-8"))
    if len(run.get("outputs", [])) != 1:
        raise ValueError("Expected exactly one final ComfyUI image")
    item = run["outputs"][0]
    raw = trial_dir / "output" / safe_relative_path(item["path"], field="output path")
    verify_file(raw, item["sha256"], label="output")
    manifest = root / safe_relative_path(provenance["manifest_path"], field="trial manifest")
    with trial_manifest_bundle(P16_SCOPE, manifest, repository_root=root,
                               isolated_work_dir=trial_dir.parent / "prepared"):
        master = resize_artwork_to_dpi(P16_SCOPE, raw, trial_dir / "review/master.png", 300)
        poster = finalize(P16_SCOPE, master, trial_dir / "review/poster-de.png", "de")
        slice_poster(P16_SCOPE, poster, output_dir=trial_dir / "review/cards")
    return {"raw_sha256": sha256_file(raw), "master_sha256": sha256_file(master),
            "poster_sha256": sha256_file(poster),
            "cards": verify_print_crops(trial_dir / "review/cards")}
```

- [ ] **Step 4: Grün und reale Vorprüfung.** `venv/bin/python -m pytest scripts/tests/test_region_joint_review.py -q`, danach fokussierte Suite für Tasks 1–6. Marker auf Vollständigkeit und Worker auf Erreichbarkeit prüfen; Modell-Hashes und pinned Commit validieren. Auf dem Worker einen kleinen MPS-SDPA-Maskentest ausführen. Wenn er fehlschlägt oder die 1-GiB-Maskengrenze überschritten würde: Befund schreiben und **keinen** P16-Render starten.
- [ ] **Step 5: Genau einen P16-Job ausführen.** Variante `p16-region-20260923-a`; nur diesen Job mit den in `docs/POSTER_RENDER_WORKER.md` beschriebenen `rsync`-/`render_job.py run`-Befehlen zum bereits konfigurierten Worker übertragen. `render_job.py run` bindet an `127.0.0.1`. Kein Seed-Loop, kein 9B-Modell, keine Ersatzmaske. Bei Worker-/MPS-/Speicherfehlern den Fehler dokumentieren und hier stoppen.
- [ ] **Step 6: Vollständig zurückholen.** Das gesamte unveränderliche Jobverzeichnis mit `run.json`, `comfyui.log` und allen Ausgabebildern unter demselben ignorierten Variantnamen zurückholen; `validate_job` und SHA-256 aus `run.json` erneut prüfen. Private Verbindungseinstellungen nicht mitkopieren.
- [ ] **Step 7: Vollständige Bildabnahme vorbereiten.** Technisches Audit plus eigene Sichtprüfung des Gesamtbilds und **aller neun** 750 × 1050 px Einleger gegen die Originalquellen; besonders Kyogres Flossen r3c1/r3c2, Groudons Schwanz r3c2/r3c3, Anatomie, Bodenkontakt, Nähte und Vordergrundtiefe. Bei Mangel als abgelehnt dokumentieren; bei bestandener Prüfung dem Nutzer Vollbild und Quelle/Karte-Paare vorlegen. Weder P16 noch P37 promotieren, bevor das **exakte** Artefakt ausdrücklich freigegeben ist.
- [ ] **Step 8: Verifizieren und Git sichern.** `venv/bin/python -m pytest scripts/tests/test_region_joint_*.py scripts/tests/test_render_job.py scripts/tests/test_review_batch_source_detail.py -q`, `git diff --check`, produktive P16-/P37-Hashes und `git status --short --branch` prüfen. Nur Code, Tests und den bereinigten Befund committen/pushen; keine Jobs, ZIPs, Quellen-Caches, privaten Marker oder Bilder ungeprüft committen.

## Handoff-Grenze

Dieser Plan endet mit einem **isolierten, geprüften P16-Piloten oder einem klaren technischen/visuellen Fehlschlag**. Er registriert den Modus noch nicht als produktiven Standard und gibt keine PDF oder P37 frei. Erst nach dateigebundener Nutzerfreigabe wird die mögliche Übernahme in den Produktionsrenderer samt vollständiger Generation-Fingerprint-/Provenienzprüfung separat geplant. Der mehrstufige Ansatz bleibt weiterhin nur ein gesondert zu entscheidender letzter Fallback.
