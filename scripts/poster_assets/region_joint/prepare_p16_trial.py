"""Prepare the single opt-in P16 region-constrained one-shot trial."""
from __future__ import annotations

import json
import copy
from pathlib import Path
import re

import yaml

from scripts.poster_assets.composition import (
    joint_scene_canvas_placements,
    normalized_visible_placement_contract,
)
from scripts.poster_assets.create_comfyui_poster_workflow import node
from scripts.poster_assets.poster_config import build_regional_joint_scene_prompts
from scripts.poster_assets.poster_io import load_cutout_items, load_poster_scope_data, poster_bundle
from scripts.poster_assets.poster_subject import resolve_poster_subject
from scripts.poster_assets.prepare_comfyui_poster import (
    build_individual_spatial_joint_references,
    build_joint_scene_references,
)
from scripts.poster_assets.render_job import prepare_job, sha256_file
from scripts.poster_assets.review_batch_source_detail import build_trial_manifest, trial_manifest_bundle
from scripts.poster_assets.source_detail import validate_source_details

from .comfy_extension.guider import P16_CONTRACT_SHA256
from .eligibility import P16_SCOPE, require_p16_evidence
from .geometry import build_p16_region_contract, validate_p16_region_contract


PILOT_VARIANT = "p16-region-20260923-b"
PREVIOUS_FAILED_VARIANT = "p16-region-20260923-a"
PREVIOUS_FAILURE_LOG_SHA256 = "d7376db5eb5f9d70d6da16e49f0e67c86856a6f13ed5cc3b33648b3dc9180054"
SEED = 653315091
MODEL_NAMES = (
    ("diffusion_models", "model", "model_sha256"),
    ("text_encoders", "encoder", "encoder_sha256"),
    ("vae", "vae", "vae_sha256"),
)


def pin_trial_b_scales(manifest: dict, baseline: dict) -> None:
    """Carry forward only B's exact two opt-in scales, never invent new ones."""
    expected = baseline["artwork"].get("spatial_reference_scales")
    if (
        not isinstance(expected, dict)
        or set(expected) != {"pokeapi:official-artwork:10077", "pokeapi:official-artwork:10078"}
        or any(type(value) is not float or value != 0.55 for value in expected.values())
    ):
        raise ValueError("P16 trial B scale drift")
    current = manifest["artwork"].get("spatial_reference_scales")
    if current is not None and current != expected:
        raise ValueError("P16 source scale drift from trial B")
    manifest["artwork"]["spatial_reference_scales"] = copy.deepcopy(expected)


def build_p16_prompts(
    manifest: dict,
    scope_data: dict,
    items: list[dict],
    placement_contract: list[dict[str, int]],
) -> tuple[str, tuple[str, str]]:
    """Reuse the reviewed scene, but bind each local branch to its own source."""
    if len(items) != 2:
        raise ValueError("P16 requires exactly two source Pokémon")
    details = validate_source_details(manifest, items)
    regions = build_p16_region_contract()
    global_prompt, _older_local_prompts = build_regional_joint_scene_prompts(
        manifest, scope_data, items,
        placement_contract=placement_contract,
        global_scene_everywhere=False,
    )
    if re.search(r"\b(?:primal\s+)?(?:kyogre|groudon)\b", global_prompt, re.IGNORECASE):
        raise ValueError("P16 global branch must be landscape-only")
    locals_: list[str] = []
    for item, side in zip(items, ("left", "right"), strict=True):
        key = resolve_poster_subject(item).subject_key
        if key != regions[side]["subject_id"]:
            raise ValueError("P16 source order differs from physical region contract")
        name = item.get("name_en") or key
        x0, y0, x1, y1 = regions[side]["inner_xyxy"]
        locals_.append(
            f"Generate exactly one complete {name} in the lower-{side} region of the SAME unified coastal landscape. "
            f"IMAGE 1 is the position and small-scale reference for this subject only; retain its pose, orientation and ground contact. "
            f"IMAGE 2 is the unscaled anatomical detail reference for this same subject only; preserve its full silhouette, face, limbs, fins, tail, colors and markings. "
            f"Keep every visible body part strictly inside x {x0}..{x1}, y {y0}..{y1} of the 1200x1664 canvas. "
            f"Do not create a second figure, another landscape, a new horizon, text, panels or borders. "
            f"Inherit terrain, weather, lighting, camera, palette and depth from the shared global landscape. "
            f"Source-specific traits for {key}: {details[key]['traits']} "
            "Natural foreground elements may plausibly overlap lower body edges without hiding or changing anatomy."
        )
    return global_prompt, (locals_[0], locals_[1])


def build_p16_workflow(
    global_prompt: str,
    local_prompts: tuple[str, str],
    regions: dict,
) -> dict[str, object]:
    """One FLUX sampler and decoder with two isolated reference chains."""
    regions = validate_p16_region_contract(regions)
    if not isinstance(global_prompt, str) or not global_prompt.strip() or re.search(
        r"\b(?:primal\s+)?(?:kyogre|groudon)\b", global_prompt, re.IGNORECASE,
    ):
        raise ValueError("P16 global prompt must be landscape-only")
    if len(local_prompts) != 2 or any(not isinstance(prompt, str) or not prompt.strip() for prompt in local_prompts):
        raise ValueError("P16 requires two nonempty local prompts")
    graph: dict[str, object] = {
        "1": node("UNETLoader", unet_name="flux-2-klein-4b.safetensors", weight_dtype="default"),
        "2": node("CLIPLoader", clip_name="qwen_3_4b.safetensors", type="flux2", device="default"),
        "3": node("VAELoader", vae_name="flux2-vae.safetensors"),
        "4": node("CLIPTextEncode", text=global_prompt, clip=["2", 0]),
        "6": node("EmptyFlux2LatentImage", width=1200, height=1664, batch_size=1),
        "7": node("Flux2Scheduler", steps=4, width=1200, height=1664),
        "8": node("RandomNoise", noise_seed=SEED),
        "10": node("KSamplerSelect", sampler_name="euler"),
        "20": node("CLIPTextEncode", text=local_prompts[0], clip=["2", 0]),
        "30": node("CLIPTextEncode", text=local_prompts[1], clip=["2", 0]),
    }
    for index, (text_id, offset) in enumerate((("20", 30), ("30", 40)), start=1):
        position_load, position_encode, position_condition = (str(offset + n) for n in (1, 2, 3))
        detail_load, detail_encode, detail_condition = (str(offset + n) for n in (4, 5, 6))
        graph[position_load] = node("LoadImage", image=f"individual_spatial_reference_{index}.png")
        graph[position_encode] = node("VAEEncode", pixels=[position_load, 0], vae=["3", 0])
        graph[position_condition] = node("ReferenceLatent", conditioning=[text_id, 0], latent=[position_encode, 0])
        graph[detail_load] = node("LoadImage", image=f"identity_reference_{index}.png")
        graph[detail_encode] = node("VAEEncode", pixels=[detail_load, 0], vae=["3", 0])
        graph[detail_condition] = node("ReferenceLatent", conditioning=[position_condition, 0], latent=[detail_encode, 0])
    graph["70"] = node(
        "RegionConstrainedJointGuider", model=["1", 0],
        global_conditioning=["4", 0], left_conditioning=["36", 0],
        right_conditioning=["46", 0],
        region_contract=json.dumps(regions, sort_keys=True, separators=(",", ":")),
    )
    graph["71"] = node(
        "SamplerCustomAdvanced", noise=["8", 0], guider=["70", 0],
        sampler=["10", 0], sigmas=["7", 0], latent_image=["6", 0],
    )
    graph["72"] = node("VAEDecode", samples=["71", 0], vae=["3", 0])
    graph["73"] = node("SaveImage", images=["72", 0], filename_prefix="p16_region_joint_653315091")
    return graph


def _relative(root: Path, path: Path) -> str:
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("P16 trial artifact escaped repository")
    return resolved.relative_to(root).as_posix()


def _production_masters_before(root: Path) -> list[dict[str, str]]:
    records = []
    for scope in (P16_SCOPE, "ME03"):
        for name in ("poster-flux2-artwork.png", "poster-flux2-provenance.json"):
            path = root / "assets/posters" / scope / name
            if not path.is_file():
                raise FileNotFoundError(path)
            records.append({"path": _relative(root, path), "sha256": sha256_file(path)})
    return records


def require_previous_failed_trial(root: Path) -> dict[str, str]:
    """Bind this corrected attempt to the reviewed, image-free first failure."""
    old_job = Path(root) / "tmp/oneshot-trials" / PREVIOUS_FAILED_VARIANT / "job"
    log = old_job / "comfyui.log"
    if not log.is_file():
        raise FileNotFoundError("previous P16 failure log is missing")
    if sha256_file(log) != PREVIOUS_FAILURE_LOG_SHA256:
        raise ValueError("previous P16 failure log hash differs")
    if (old_job / "run.json").exists() or any((old_job / "output").glob("*.png")):
        raise ValueError("previous P16 attempt is no longer an image-free failure")
    return {"variant": PREVIOUS_FAILED_VARIANT, "comfyui_log_sha256": PREVIOUS_FAILURE_LOG_SHA256}


def prepare_p16_trial(variant: str, root: Path) -> Path:
    """Create one non-promotable, sealed P16 job below ignored trial space."""
    if variant != PILOT_VARIANT:
        raise ValueError("Only the single approved P16 pilot variant is allowed")
    root = Path(root).resolve()
    trial_dir = root / "tmp/oneshot-trials" / variant
    if trial_dir.exists():
        raise FileExistsError("P16 pilot variant already exists; refusing overwrite")
    preceding_attempt = require_previous_failed_trial(root)
    evidence = root / "docs/reviews/2026-09-23-p16-region-fallback-evidence.json"
    evidence_sha = require_p16_evidence(root, evidence)
    b_manifest_path = root / "tmp/review-batch-manifests/p16-batch-20260922-b/poster.yaml"
    baseline = yaml.safe_load(b_manifest_path.read_text(encoding="utf-8"))
    before = _production_masters_before(root)

    manifest_path = build_trial_manifest(
        P16_SCOPE, variant, SEED, repository_root=root,
        traits_path=root / "docs/reviews/2026-09-22-panorama-source-traits.yaml",
        retriage_path=root / "docs/reviews/2026-09-14-panorama-retriage.json",
    )
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    pin_trial_b_scales(manifest, baseline)
    for field in ("scene", "source_details", "spatial_reference_scales"):
        if manifest["artwork"].get(field) != baseline["artwork"].get(field):
            raise ValueError(f"P16 source or scene drift from trial B: {field}")
    if manifest["artwork"]["generation"] != baseline["artwork"]["generation"]:
        raise ValueError("P16 model, seed or generation settings drifted from trial B")
    if manifest.get("layout") != baseline.get("layout"):
        raise ValueError("P16 layout drifted from trial B")
    scales = manifest["artwork"]["spatial_reference_scales"]
    if set(scales) != {"pokeapi:official-artwork:10077", "pokeapi:official-artwork:10078"} or any(value != 0.55 for value in scales.values()):
        raise ValueError("P16 subject scales differ from trial B")
    manifest["artwork"]["generation"]["reference_mode"] = "region_constrained_joint"
    manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")

    prepared = trial_dir / "prepared"
    trial_dir.mkdir(parents=True, exist_ok=False)
    with trial_manifest_bundle(P16_SCOPE, manifest_path, repository_root=root, isolated_work_dir=prepared):
        bundle = poster_bundle(P16_SCOPE, poster_assets=root / "assets/posters")
        items = load_cutout_items(bundle.source_dir)
        if [resolve_poster_subject(item).subject_key for item in items] != [
            "pokeapi:official-artwork:10077", "pokeapi:official-artwork:10078",
        ]:
            raise ValueError("P16 cached source order differs from trial B")
        validate_source_details(manifest, items, bundle.source_dir)
        build_joint_scene_references(
            P16_SCOPE, prepared, megapixels=2.0, include_cast=False, subject_scales=scales,
        )
        build_individual_spatial_joint_references(P16_SCOPE, prepared, subject_scales=scales)
        if (prepared / "joint_scene_cast_reference.png").exists():
            raise ValueError("P16 global branch must not receive a cast image")
        placements = joint_scene_canvas_placements(
            bundle.source_dir, layout_name="standard_3x3",
            canvas_size=(1200, 1664), subject_scales=scales,
        )
        placement = normalized_visible_placement_contract(placements, canvas_size=(1200, 1664))
        scope_data = load_poster_scope_data(bundle, scope_data_dir=root / "data/output")
        global_prompt, local_prompts = build_p16_prompts(manifest, scope_data, items, placement)

    regions = build_p16_region_contract()
    graph = build_p16_workflow(global_prompt, local_prompts, regions)
    workflow_path = prepared / "workflow_api.json"
    workflow_path.write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for name, content in (("global", global_prompt), ("left", local_prompts[0]), ("right", local_prompts[1])):
        (prepared / f"prompt-{name}.txt").write_text(content + "\n", encoding="utf-8")
    references = [
        prepared / f"{name}_{index}.png"
        for index in (1, 2)
        for name in ("individual_spatial_reference", "identity_reference")
    ]
    if not all(path.is_file() for path in references):
        raise FileNotFoundError("P16 trial is missing a subject reference")
    job_dir = trial_dir / "job"
    manifest_job_path = prepare_job(
        workflow_path, job_dir,
        [f"{path}={path.name}" for path in references],
        [f"{folder}/{manifest['artwork']['generation'][name]}={manifest['artwork']['generation'][sha]}"
         for folder, name, sha in MODEL_NAMES],
        extension_source=Path(__file__).resolve().parent / "comfy_extension",
    )
    job = json.loads(manifest_job_path.read_text(encoding="utf-8"))
    cutout_records = []
    for item in items:
        key = resolve_poster_subject(item).subject_key
        source = bundle.source_dir / "cutouts" / item["file"]
        cutout_records.append({"subject_id": key, "path": _relative(root, source), "sha256": sha256_file(source)})
    provenance = {
        "schema_version": 1,
        "variant": variant,
        "scope": P16_SCOPE,
        "status": "pilot_only_not_promoted",
        "reference_mode": "region_constrained_joint",
        "seed": SEED,
        "evidence_sha256": evidence_sha,
        "previous_failed_attempt": preceding_attempt,
        "trial_b_manifest_sha256": sha256_file(b_manifest_path),
        "manifest_path": _relative(root, manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "job_path": _relative(root, job_dir),
        "workflow_sha256": job["workflow"]["sha256"],
        "region_contract": regions,
        "region_contract_sha256": P16_CONTRACT_SHA256,
        "prompt_sha256": {
            name: sha256_file(prepared / f"prompt-{name}.txt")
            for name in ("global", "left", "right")
        },
        "source_cutouts": cutout_records,
        "input_references": job["inputs"],
        "extension_files": job["extensions"]["files"],
        "models": job["models"],
        "production_masters_before": before,
    }
    (trial_dir / "trial_provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    if _production_masters_before(root) != before:
        raise ValueError("Production master changed while preparing P16 trial")
    return job_dir
