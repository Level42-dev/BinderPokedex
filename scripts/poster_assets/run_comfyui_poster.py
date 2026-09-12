#!/usr/bin/env python3
"""Run the local FLUX.2 poster pipeline against a running ComfyUI server."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageStat

try:
    from .generation_contract import is_grounded_generation
    from .provenance import grounded_output_record, audit_grounded_generation
    from .create_comfyui_poster_workflow import (
        megapixel_marker,
        page_dimensions,
        write_workflow as write_flux_workflow,
    )
    from .create_comfyui_upscale_workflow import DEFAULT_UPSCALE_MODEL
    from .finalize_comfyui_poster import SUPPORTED_LANGUAGES, finalize
    from .generation_contract import (
        is_joint_scene_generation,
        validate_generation_contract,
    )
    from .generation_options import (
        DEFAULT_FLUX_ENCODER,
        DEFAULT_FLUX_MODE,
        DEFAULT_FLUX_MODEL,
        DEFAULT_FLUX_STEPS,
        DEFAULT_FLUX_VAE,
        metadata_from_workflow_options,
        resolve_generation_options,
    )
    from .layout import build_print_layout
    from .poster_io import POSTER_ASSETS, poster_asset_slug, poster_bundle
    from .prepare_comfyui_poster import prepare
    from .provenance import (
        add_model_artifact_hashes,
        sha256_file,
        write_run_metadata,
    )
    from .queue_comfyui_workflow import (
        queue_workflow,
        server_comfyui_root,
        validate_server_input_directory,
    )
    from .slice_poster import slice_poster
    from .source_pixel_audit import audit_exact_source_pixels
    from .upscale_comfyui_poster import upscale
except ImportError:
    from generation_contract import is_grounded_generation
    from provenance import grounded_output_record, audit_grounded_generation
    from create_comfyui_poster_workflow import (
        megapixel_marker,
        page_dimensions,
        write_workflow as write_flux_workflow,
    )
    from create_comfyui_upscale_workflow import DEFAULT_UPSCALE_MODEL
    from finalize_comfyui_poster import SUPPORTED_LANGUAGES, finalize
    from generation_contract import (
        is_joint_scene_generation,
        validate_generation_contract,
    )
    from generation_options import (
        DEFAULT_FLUX_ENCODER,
        DEFAULT_FLUX_MODE,
        DEFAULT_FLUX_MODEL,
        DEFAULT_FLUX_STEPS,
        DEFAULT_FLUX_VAE,
        metadata_from_workflow_options,
        resolve_generation_options,
    )
    from layout import build_print_layout
    from poster_io import POSTER_ASSETS, poster_asset_slug, poster_bundle
    from prepare_comfyui_poster import prepare
    from provenance import (
        add_model_artifact_hashes,
        sha256_file,
        write_run_metadata,
    )
    from queue_comfyui_workflow import (
        queue_workflow,
        server_comfyui_root,
        validate_server_input_directory,
    )
    from slice_poster import slice_poster
    from source_pixel_audit import audit_exact_source_pixels
    from upscale_comfyui_poster import upscale


ENGINE = "flux"
DEFAULT_GENERATION_MEGAPIXELS = 1.0
DEFAULT_OUTPUT_DPI = 300


def select_generation_outputs(
    outputs: list[dict], workflow_path: Path, work_dir: Path, generation: dict,
) -> dict[str, Path]:
    """Resolve labeled outputs without trusting worker result order."""
    images = [
        item for item in outputs
        if item.get("type") == "output" and item.get("filename")
    ]
    grounded = is_grounded_generation(generation)
    if len(images) != (2 if grounded else 1):
        expected = "two labeled" if grounded else "exactly one"
        raise RuntimeError(f"Expected {expected} output image(s), got: {outputs}")
    root = (work_dir / "output").resolve()
    paths = []
    for item in images:
        path = (
            root / str(item.get("subfolder", "")) / str(item["filename"])
        ).resolve()
        if not path.is_relative_to(root):
            raise ValueError("ComfyUI output escapes the current job directory")
        if not path.is_file():
            raise FileNotFoundError(f"ComfyUI reported a missing output: {path}")
        paths.append(path)
    if not grounded:
        return {"final": paths[0]}
    graph = json.loads(workflow_path.read_text(encoding="utf-8"))
    result = {}
    for role in ("final", "baseline"):
        prefixes = [
            n["inputs"]["filename_prefix"] for n in graph.values()
            if n.get("class_type") == "SaveImage"
            and str(n.get("inputs", {}).get("filename_prefix", "")).endswith("_" + role)
        ]
        matches = [
            path for path in paths
            if len(prefixes) == 1
            and path.name.startswith(Path(prefixes[0]).name + "_")
        ]
        if len(matches) != 1:
            raise ValueError(f"Grounding job lacks one distinct {role} output")
        grounded_output_record(matches[0], workflow_path, role)
        result[role] = matches[0]
    if result["final"] == result["baseline"]:
        raise ValueError("Grounding job output roles must be distinct")
    return result


def configured_generation(scope: str) -> dict[str, object]:
    """Load the reviewed generation contract used as production CLI defaults."""
    bundle = poster_bundle(scope, poster_assets=POSTER_ASSETS)
    generation = bundle.manifest.get("artwork", {}).get("generation")
    if not isinstance(generation, dict) or not generation:
        raise ValueError(
            "Poster scope has no artwork.generation contract: "
            f"{bundle.manifest_path}"
        )
    return generation


def validate_raw_artwork(path: Path) -> None:
    image = Image.open(path).convert("RGB")
    extrema = image.getextrema()
    variation = ImageStat.Stat(image).stddev
    if max(high for _low, high in extrema) < 12 or max(variation) < 2.0:
        raise RuntimeError(
            f"ComfyUI produced blank or near-constant artwork: {path}"
        )


def validate_identity_lock_pixels(
    scope: str,
    raw_artwork: Path,
    reference_path: Path | None = None,
) -> dict[str, int | str | bool]:
    """Require every fully opaque source pixel to survive diffusion unchanged."""
    reference_path = reference_path or (
        poster_bundle(scope, poster_assets=POSTER_ASSETS).work_dir
        / "inpaint_reference.png"
    )
    return audit_exact_source_pixels(
        reference_path,
        raw_artwork,
        require_match=True,
    )


def resize_artwork(
    scope: str,
    source: Path,
    destination: Path,
    megapixels: float,
) -> Path:
    target_size = page_dimensions(scope, megapixels)
    image = Image.open(source).convert("RGB")
    if image.size != target_size:
        image = image.resize(target_size, Image.Resampling.LANCZOS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG", optimize=True)
    validate_raw_artwork(destination)
    return destination


def resize_artwork_to_dpi(
    scope: str,
    source: Path,
    destination: Path,
    dpi: int,
) -> Path:
    """Resize deterministically to the exact physical card-grid raster."""
    if dpi <= 0:
        raise ValueError("dpi must be positive")
    bundle = poster_bundle(scope, poster_assets=POSTER_ASSETS)
    layout_name = str(
        bundle.manifest.get("layout", {}).get(
            "name",
            "standard_3x3",
        )
    )
    print_layout = build_print_layout(layout_name, dpi)
    target_size = (print_layout.width_px, print_layout.height_px)
    image = Image.open(source).convert("RGB")
    if image.size != target_size:
        image = image.resize(target_size, Image.Resampling.LANCZOS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(
        destination,
        format="PNG",
        optimize=True,
        dpi=(dpi, dpi),
    )
    validate_raw_artwork(destination)
    return destination


def write_engine_workflow(
    engine: str,
    scope: str,
    seed: int,
    megapixels: float,
    *,
    flux_mode: str = DEFAULT_FLUX_MODE,
    flux_reference_mode: str | None = None,
    flux_model: str = DEFAULT_FLUX_MODEL,
    flux_steps: int = DEFAULT_FLUX_STEPS,
    flux_clip: str = DEFAULT_FLUX_ENCODER,
    flux_vae: str = DEFAULT_FLUX_VAE,
    workflow_output_dir: Path | None = None,
) -> Path:
    """Write one supported FLUX.2 workflow graph."""
    if engine != ENGINE:
        raise ValueError(
            f"Unsupported engine {engine!r}; only {ENGINE!r} is supported"
        )
    return write_flux_workflow(
        scope,
        seed,
        megapixels,
        generation_mode=flux_mode,
        reference_mode=flux_reference_mode,
        unet_name=flux_model,
        steps=flux_steps,
        clip_name=flux_clip,
        vae_name=flux_vae,
        output_dir=workflow_output_dir,
    )


def resolve_output_target(
    configured: dict[str, object],
    effective_mode: str,
    *,
    output_dpi: int | None,
    output_megapixels: float | None,
) -> tuple[int | None, float | None]:
    """Resolve output size without leaking one mode's policy into the other."""
    if output_dpi is not None and output_megapixels is not None:
        raise ValueError(
            "Choose either output_megapixels or output_dpi, not both"
        )
    if output_dpi is not None or output_megapixels is not None:
        return output_dpi, output_megapixels

    configured_mode = configured.get("mode")
    if (
        configured_mode == effective_mode
        and configured.get("output_method") == "lanczos"
        and configured.get("output_megapixels") is not None
        and configured.get("output_dpi") is None
    ):
        return None, float(configured["output_megapixels"])
    # Both reviewed modes default to the physical 300-dpi raster. The run()
    # function selects Lanczos for joint_scene and model upscale for IL.
    return int(configured.get("output_dpi") or DEFAULT_OUTPUT_DPI), None


def run(
    scope: str,
    seed: int,
    megapixels: float,
    server: str,
    timeout: int,
    language: str,
    *,
    engine: str = ENGINE,
    flux_mode: str = DEFAULT_FLUX_MODE,
    flux_reference_mode: str | None = None,
    flux_model: str = DEFAULT_FLUX_MODEL,
    flux_steps: int = DEFAULT_FLUX_STEPS,
    flux_clip: str = DEFAULT_FLUX_ENCODER,
    flux_vae: str = DEFAULT_FLUX_VAE,
    output_megapixels: float | None = None,
    output_dpi: int | None = DEFAULT_OUTPUT_DPI,
    upscale_model: str = DEFAULT_UPSCALE_MODEL,
) -> tuple[Path, Path, Path, Path]:
    if engine != ENGINE:
        raise ValueError(
            f"Unsupported engine {engine!r}; only {ENGINE!r} is supported"
        )
    if output_megapixels is not None and output_dpi is not None:
        raise ValueError(
            "Choose either output_megapixels or output_dpi, not both"
        )
    if output_dpi is not None and output_dpi <= 0:
        raise ValueError("output_dpi must be positive")
    workflow_options = {
        "flux_mode": flux_mode,
        "flux_reference_mode": flux_reference_mode,
        "flux_model": flux_model,
        "flux_steps": flux_steps,
        "flux_clip": flux_clip,
        "flux_vae": flux_vae,
    }
    generation_metadata = metadata_from_workflow_options(
        ENGINE,
        workflow_options,
    )
    effective_reference_mode = str(
        generation_metadata["reference_mode"]
    )
    workflow_options["flux_reference_mode"] = effective_reference_mode
    joint_scene = is_joint_scene_generation(generation_metadata)
    work_dir = prepare(
        scope,
        megapixels,
        generation_mode=flux_mode,
        reference_mode=effective_reference_mode,
    )
    validate_server_input_directory(server, work_dir)
    comfy_root = server_comfyui_root(server)
    if comfy_root is None:
        raise RuntimeError(
            "ComfyUI did not report an absolute main.py path; start it with "
            "scripts/poster_assets/start_comfyui_poster.sh"
        )
    workflow_path = write_engine_workflow(
        ENGINE,
        scope,
        seed,
        megapixels,
        **workflow_options,
    )
    outputs = queue_workflow(
        workflow_path,
        server=server,
        timeout=timeout,
    )
    roles = select_generation_outputs(
        outputs, workflow_path, work_dir, generation_metadata,
    )
    raw_path = roles["final"]
    validate_raw_artwork(raw_path)

    validation: dict[str, object] = {}
    if is_grounded_generation(generation_metadata):
        audit_generation = {
            **generation_metadata,
            "seed": seed,
            "generation_megapixels": megapixels,
        }
        if output_dpi is not None:
            audit_generation.update(
                output_dpi=output_dpi,
                output_method="model_upscale",
                upscale_model=upscale_model,
            )
        else:
            audit_generation.update(
                output_megapixels=(
                    output_megapixels
                    if output_megapixels is not None else megapixels
                ),
                output_method="lanczos",
            )
        audited = audit_grounded_generation(
            scope, workflow_path, audit_generation,
            raw_path, roles["baseline"],
        )
        validation = audited["validation"]
    elif flux_mode == "identity_lock":
        source_reference = work_dir / "inpaint_reference.png"
        source_pixel_audit = audit_exact_source_pixels(
            source_reference,
            raw_path,
            require_match=True,
        )
        with Image.open(raw_path) as audited_artwork:
            audit_width, audit_height = audited_artwork.size
        source_pixel_audit.update(
            {
                "stage": "raw_generation",
                "reference_sha256": sha256_file(source_reference),
                "artwork_sha256": sha256_file(raw_path),
                "width": audit_width,
                "height": audit_height,
            }
        )
        validation["source_pixels"] = source_pixel_audit

    final_megapixels = (
        output_megapixels
        if output_megapixels is not None
        else megapixels
    )
    reference_mode = str(generation_metadata["reference_mode"])
    normalized_model = flux_model.lower().replace("-", "_").replace(".", "_")
    if "flux2_dev" in normalized_model or "flux_2_dev" in normalized_model:
        model_variant = "dev32b"
    elif "9b" in flux_model.lower():
        model_variant = "distilled9b"
    elif "base-4b" in flux_model:
        model_variant = "base4b"
    else:
        model_variant = "distilled4b"
    run_marker = (
        f"{flux_mode}_{reference_mode}_{model_variant}_"
        f"{flux_steps}step_{megapixel_marker(megapixels)}"
    )
    if output_dpi is not None:
        run_marker += f"_to_{output_dpi}dpi"
    elif final_megapixels != megapixels:
        run_marker += f"_to_{megapixel_marker(final_megapixels)}"
    final_path = (
        work_dir
        / "output"
        / (
            f"{poster_asset_slug(scope)}_{ENGINE}_{run_marker}_"
            f"poster_{language}_seed_{seed}_final.png"
        )
    )

    upscale_workflow_path = None
    if output_dpi is not None:
        if joint_scene:
            artwork_path = resize_artwork_to_dpi(
                scope,
                raw_path,
                work_dir
                / "temp"
                / f"{raw_path.stem}_to_{output_dpi}dpi.png",
                output_dpi,
            )
        else:
            artwork_path, upscale_workflow_path = upscale(
                scope,
                raw_path,
                server=server,
                timeout=timeout,
                dpi=output_dpi,
                model_name=upscale_model,
            )
    else:
        artwork_marker = (
            f"to_{megapixel_marker(final_megapixels)}"
            if final_megapixels != megapixels
            else "page"
        )
        artwork_path = resize_artwork(
            scope,
            raw_path,
            work_dir / "temp" / f"{raw_path.stem}_{artwork_marker}.png",
            final_megapixels,
        )

    finalize(scope, artwork_path, final_path, language)
    slice_poster(scope, final_path)
    generation = {
        **generation_metadata,
        "seed": seed,
        "generation_megapixels": megapixels,
    }
    if output_dpi is not None:
        generation.update(
            {
                "output_dpi": output_dpi,
                "output_method": (
                    "lanczos" if joint_scene else "model_upscale"
                ),
            }
        )
        if not joint_scene:
            generation["upscale_model"] = upscale_model
    else:
        generation.update(
            {
                "output_megapixels": final_megapixels,
                "output_method": "lanczos",
            }
        )
    validate_generation_contract(generation)
    generation = add_model_artifact_hashes(comfy_root, generation)
    run_metadata_path = write_run_metadata(
        scope,
        artwork_path,
        workflow_path,
        generation,
        raw_artwork_path=raw_path,
        baseline_artwork_path=roles.get("baseline"),
        additional_workflows=(
            {"upscale_workflow": upscale_workflow_path}
            if upscale_workflow_path is not None
            else None
        ),
        validation=validation or None,
    )
    return raw_path, artwork_path, final_path, run_metadata_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", default="Base1")
    parser.add_argument(
        "--seed",
        type=int,
        help="Override the stable seed configured in poster.yaml",
    )
    parser.add_argument(
        "--megapixels",
        type=float,
        help="Override artwork.generation.generation_megapixels",
    )
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--output-dpi",
        type=int,
        help="Write the exact physical print raster (default: 300)",
    )
    output_group.add_argument(
        "--output-megapixels",
        type=float,
        help="Write a deterministic Lanczos preview raster",
    )
    parser.add_argument(
        "--upscale-model",
        help="Override the identity-lock upscale model",
    )
    parser.add_argument("--server", default="http://127.0.0.1:8188")
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument(
        "--language",
        choices=SUPPORTED_LANGUAGES,
        default="en",
    )
    parser.add_argument(
        "--flux-mode",
        choices=("joint_scene", "identity_lock"),
        help="Override the manifest mode; joint_scene is the default",
    )
    parser.add_argument(
        "--flux-reference-mode",
        choices=(
            "individual_spatial_joint",
            "spatial_identity_joint",
            "regional_identity_joint",
            "two_pass_source_pixels",
            "grounded_source_pixels",
        ),
        help="Override the selected mode's reference topology",
    )
    parser.add_argument("--flux-model")
    parser.add_argument("--flux-steps", type=int)
    parser.add_argument(
        "--flux-clip",
        help="FLUX.2 text encoder matching the selected model",
    )
    parser.add_argument("--flux-vae")
    args = parser.parse_args()

    configured = configured_generation(args.scope)
    resolved = resolve_generation_options(
        ENGINE,
        configured,
        vars(args),
    )
    seed = (
        args.seed
        if args.seed is not None
        else int(configured.get("seed", 260715201))
    )
    megapixels = (
        args.megapixels
        if args.megapixels is not None
        else float(
            configured.get(
                "generation_megapixels",
                DEFAULT_GENERATION_MEGAPIXELS,
            )
        )
    )
    output_dpi, output_megapixels = resolve_output_target(
        configured,
        str(resolved.metadata["mode"]),
        output_dpi=args.output_dpi,
        output_megapixels=args.output_megapixels,
    )
    upscale_model = str(
        args.upscale_model
        or configured.get("upscale_model")
        or DEFAULT_UPSCALE_MODEL
    )
    raw_path, artwork_path, final_path, run_metadata_path = run(
        args.scope,
        seed,
        megapixels,
        args.server,
        args.timeout,
        args.language,
        engine=ENGINE,
        **resolved.workflow_options,
        output_megapixels=output_megapixels,
        output_dpi=output_dpi,
        upscale_model=upscale_model,
    )
    mode = resolved.metadata["mode"]
    print(f"[{ENGINE}/{mode}] Raw artwork: {raw_path}")
    print(f"[{ENGINE}/{mode}] Text-free artwork: {artwork_path}")
    print(f"[{ENGINE}/{mode}] Final poster: {final_path}")
    print(
        f"[{ENGINE}/{mode}] Card slices: "
        f"{final_path.with_name(f'{final_path.stem}_cards')}"
    )
    print(f"[{ENGINE}/{mode}] Run metadata: {run_metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
