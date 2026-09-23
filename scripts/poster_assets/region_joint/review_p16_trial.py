"""Audit the returned, non-promotable P16 regional one-shot pilot."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps
import yaml

from scripts.poster_assets.finalize_comfyui_poster import finalize
from scripts.poster_assets.render_job import (
    COMFYUI_COMMIT,
    _validate_extension,
    safe_relative_path,
    sha256_file,
    verify_file,
)
from scripts.poster_assets.review_batch_source_detail import trial_manifest_bundle
from scripts.poster_assets.run_comfyui_poster import resize_artwork_to_dpi
from scripts.poster_assets.slice_poster import slice_poster

from .comfy_extension.guider import P16_CONTRACT_SHA256
from .eligibility import P16_SCOPE
from .prepare_p16_trial import MODEL_NAMES, PILOT_VARIANT


PRINT_DPI = 300
PRINT_SIZE = (2368, 3268)
CARD_SIZE = (750, 1050)
SOURCE_CARDS = (
    ("pokeapi:official-artwork:10077", "card_r3_c1.png", "compare-kyogre-r3c1.png"),
    ("pokeapi:official-artwork:10078", "card_r3_c3.png", "compare-groudon-r3c3.png"),
)
EXPECTED_INPUTS = {
    f"{name}_{index}.png"
    for index in (1, 2)
    for name in ("individual_spatial_reference", "identity_reference")
}
EXPECTED_PRODUCTION_MASTERS = {
    f"assets/posters/{scope}/{name}"
    for scope in (P16_SCOPE, "ME03")
    for name in ("poster-flux2-artwork.png", "poster-flux2-provenance.json")
}
PINNED_MODEL_NAMES = {
    "model": "flux-2-klein-4b.safetensors",
    "encoder": "qwen_3_4b.safetensors",
    "vae": "flux2-vae.safetensors",
}


def _root_file(root: Path, relative_value: str, *, field: str) -> Path:
    relative = safe_relative_path(relative_value, field=field)
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"{field} escapes repository")
    return path


def _job_file(base: Path, relative_value: str, *, field: str, job_root: Path) -> Path:
    relative = safe_relative_path(relative_value, field=field)
    if base.is_symlink() or not base.resolve().is_relative_to(job_root.resolve()):
        raise ValueError(f"{field} base escapes pilot job")
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError(f"{field} escapes pilot job")
    return path


def _verify_record(root: Path, item: dict, *, label: str) -> Path:
    path = _root_file(root, str(item["path"]), field=f"{label} path")
    verify_file(path, str(item["sha256"]), label=label)
    return path


def _artifact(root: Path, path: Path) -> dict[str, str]:
    relative = path.resolve().relative_to(root.resolve())
    return {"path": relative.as_posix(), "sha256": sha256_file(path)}


def verify_print_raster(path: Path) -> str:
    """Require the exact nine-card raster and embedded 300-dpi metadata."""
    with Image.open(path) as image:
        if image.size != PRINT_SIZE:
            raise ValueError(f"Incorrect print raster: {path.name}")
        dpi = image.info.get("dpi")
        if not dpi or len(dpi) != 2 or any(abs(float(value) - PRINT_DPI) > 1 for value in dpi):
            raise ValueError(f"Expected 300 dpi in {path.name}")
        image.verify()
    return sha256_file(path)


def verify_print_crops(cards_dir: Path) -> dict[str, str]:
    """Require all nine and only nine exact-size 300-dpi physical cards."""
    expected = [cards_dir / f"card_r{row}_c{col}.png" for row in range(1, 4) for col in range(1, 4)]
    for card in expected:
        if not card.is_file():
            raise FileNotFoundError(card.name)
        with Image.open(card) as image:
            if image.size != CARD_SIZE:
                raise ValueError(f"Incorrect print crop: {card.name}")
            dpi = image.info.get("dpi")
            if not dpi or len(dpi) != 2 or any(abs(float(value) - PRINT_DPI) > 1 for value in dpi):
                raise ValueError(f"Expected 300 dpi in {card.name}")
            image.verify()
    actual = {path.name for path in cards_dir.glob("card_r*_c*.png")}
    if actual != {path.name for path in expected}:
        raise ValueError("Unexpected additional print crops")
    return {card.name: sha256_file(card) for card in expected}


def verify_pinned_models(model_records: object, generation: dict) -> None:
    """Require the exact FLUX.2 4B, Qwen and VAE records from the trial manifest."""
    if not isinstance(generation, dict) or any(generation.get(name) != filename for name, filename in PINNED_MODEL_NAMES.items()):
        raise ValueError("P16 pinned model names drift")
    expected = {
        f"{folder}/{generation[name]}": generation[sha]
        for folder, name, sha in MODEL_NAMES
    }
    if (
        not isinstance(model_records, list)
        or len(model_records) != 3
        or any(not isinstance(item, dict) or "path" not in item or "sha256" not in item for item in model_records)
        or {item["path"]: item["sha256"] for item in model_records} != expected
    ):
        raise ValueError("P16 pinned model inventory drift")


def _source_card_pair(source: Path, card: Path, destination: Path, label: str) -> Path:
    """Make a review-only juxtaposition without changing either source or card."""
    canvas = Image.new("RGB", (1520, 1100), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 15), "Quelle", fill="black")
    draw.text((782, 15), label, fill="black")
    with Image.open(source) as loaded:
        cutout = ImageOps.contain(loaded.convert("RGBA"), (740, 1000), Image.Resampling.LANCZOS)
    left = Image.new("RGBA", cutout.size, "white")
    left.alpha_composite(cutout)
    canvas.paste(left.convert("RGB"), ((750 - cutout.width) // 2, 50 + (1050 - cutout.height) // 2))
    with Image.open(card) as loaded:
        if loaded.size != CARD_SIZE:
            raise ValueError("Comparison card has incorrect size")
        canvas.paste(loaded.convert("RGB"), (770, 50))
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, format="PNG", optimize=True)
    return destination


def audit_p16_trial(trial_dir: Path, root: Path) -> dict:
    """Verify returned hashes and prepare review images, never production assets."""
    root = Path(root).resolve()
    trial_dir = Path(trial_dir).resolve()
    expected_job = root / "tmp/oneshot-trials" / PILOT_VARIANT / "job"
    if trial_dir != expected_job:
        raise ValueError("Only the sealed P16 pilot job may be reviewed")
    review_dir = trial_dir / "review"
    if review_dir.exists() or review_dir.is_symlink():
        raise FileExistsError("P16 review directory already exists")
    run_path = trial_dir / "run.json"
    log_path = trial_dir / "comfyui.log"
    for path in (run_path, log_path):
        if not path.is_file():
            raise FileNotFoundError(path.name)
    provenance_path = trial_dir.parent / "trial_provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if (provenance.get("scope"), provenance.get("variant")) != (P16_SCOPE, PILOT_VARIANT):
        raise ValueError("P16 trial provenance identifies another pilot")
    if provenance.get("region_contract_sha256") != P16_CONTRACT_SHA256:
        raise ValueError("P16 region contract hash drift")
    masters = provenance.get("production_masters_before")
    if (
        not isinstance(masters, list)
        or len(masters) != 4
        or any(not isinstance(item, dict) or "path" not in item for item in masters)
        or {item["path"] for item in masters} != EXPECTED_PRODUCTION_MASTERS
    ):
        raise ValueError("P16/P37 production master inventory drift")
    for item in masters:
        _verify_record(root, item, label="production master")
    source_records = provenance.get("source_cutouts")
    expected_subjects = {subject for subject, _card, _name in SOURCE_CARDS}
    if (
        not isinstance(source_records, list)
        or len(source_records) != 2
        or any(not isinstance(item, dict) or "subject_id" not in item for item in source_records)
        or {item["subject_id"] for item in source_records} != expected_subjects
    ):
        raise ValueError("P16 source cutout inventory drift")
    sources = {
        item["subject_id"]: _verify_record(root, item, label="source cutout")
        for item in source_records
    }
    run = json.loads(run_path.read_text(encoding="utf-8"))
    if len(run.get("outputs", [])) != 1:
        raise ValueError("Expected exactly one final ComfyUI image")
    output_record = run["outputs"][0]
    raw = _job_file(trial_dir / "output", str(output_record["path"]), field="output path", job_root=trial_dir)
    verify_file(raw, str(output_record["sha256"]), label="output")
    with Image.open(raw) as image:
        if image.size != (1200, 1664):
            raise ValueError("P16 raw output has incorrect generation dimensions")
        image.verify()

    job = json.loads((trial_dir / "job.json").read_text(encoding="utf-8"))
    if job.get("format_version") != 2 or run.get("format_version") != 2:
        raise ValueError("P16 return is not an extension job")
    if job.get("comfyui_commit") != COMFYUI_COMMIT or run.get("comfyui_commit") != COMFYUI_COMMIT:
        raise ValueError("P16 return uses another ComfyUI revision")
    if run.get("device") != "mps" or "Device: mps" not in log_path.read_text(encoding="utf-8", errors="replace"):
        raise ValueError("P16 return has no MPS log evidence")
    workflow = job["workflow"]
    verify_file(_job_file(trial_dir, workflow["path"], field="workflow path", job_root=trial_dir), workflow["sha256"], label="workflow")
    if run.get("workflow_sha256") != workflow["sha256"] or provenance.get("workflow_sha256") != workflow["sha256"]:
        raise ValueError("P16 workflow hash drift")
    if run.get("inputs") != job["inputs"] or provenance.get("input_references") != job["inputs"]:
        raise ValueError("P16 input reference drift")
    if {item["path"] for item in job["inputs"]} != EXPECTED_INPUTS or len(job["inputs"]) != 4:
        raise ValueError("P16 requires four exact input references")
    for item in job["inputs"]:
        verify_file(_job_file(trial_dir / "input", item["path"], field="input path", job_root=trial_dir), item["sha256"], label="input")
    if run.get("models") != job["models"] or provenance.get("models") != job["models"]:
        raise ValueError("P16 model record drift")
    _validate_extension(trial_dir, job.get("extensions"))
    if provenance.get("extension_files") != job["extensions"]["files"]:
        raise ValueError("P16 extension record drift")
    manifest = _root_file(root, str(provenance["manifest_path"]), field="trial manifest")
    verify_file(manifest, str(provenance["manifest_sha256"]), label="trial manifest")
    generation = yaml.safe_load(manifest.read_text(encoding="utf-8"))["artwork"]["generation"]
    verify_pinned_models(job["models"], generation)

    review_dir.mkdir(mode=0o700, exist_ok=False)
    with trial_manifest_bundle(P16_SCOPE, manifest, repository_root=root,
                               isolated_work_dir=trial_dir.parent / "prepared"):
        master = resize_artwork_to_dpi(P16_SCOPE, raw, review_dir / "master.png", PRINT_DPI)
        poster = finalize(P16_SCOPE, master, review_dir / "poster-de.png", "de")
        slice_poster(P16_SCOPE, poster, output_dir=review_dir / "cards")
    verify_print_raster(master)
    verify_print_raster(poster)
    cards = verify_print_crops(review_dir / "cards")
    pairs = {}
    for subject, card_name, name in SOURCE_CARDS:
        pair = _source_card_pair(sources[subject], review_dir / "cards" / card_name,
                                 review_dir / name, card_name)
        pairs[name] = _artifact(root, pair)
    evidence = {
        "schema_version": 1,
        "scope": P16_SCOPE,
        "variant": PILOT_VARIANT,
        "status": "technical_pass_visual_pending",
        "run_sha256": sha256_file(run_path),
        "comfyui_log_sha256": sha256_file(log_path),
        "provenance_sha256": sha256_file(provenance_path),
        "workflow_sha256": workflow["sha256"],
        "region_contract_sha256": P16_CONTRACT_SHA256,
        "source_cutouts": provenance["source_cutouts"],
        "raw": _artifact(root, raw),
        "master": _artifact(root, master),
        "poster_de": _artifact(root, poster),
        "cards": cards,
        "comparisons": pairs,
    }
    (review_dir / "evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return evidence
