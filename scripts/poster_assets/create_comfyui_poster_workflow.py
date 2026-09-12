#!/usr/bin/env python3
"""Create one of the supported FLUX.2 poster workflows."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .grounding import grounding_config
    from .poster_config import GROUNDED_PROMPT_FILE, build_grounded_prompt_snapshot
    from .composition import (
        joint_scene_canvas_placements,
        normalized_visible_placement_contract,
    )
    from .layout import (
        build_source_layout,
        latent_canvas_dimensions,
        page_canvas_dimensions,
    )
    from .poster_config import (
        IDENTITY_LOCK_PROMPT_FILE,
        INDIVIDUAL_SPATIAL_JOINT_PROMPT_FILE,
        JOINT_SCENE_PROMPT_FILE,
        REGIONAL_JOINT_SCENE_PROMPT_FILE,
        build_individual_spatial_joint_prompt,
        build_joint_scene_prompt,
        build_identity_lock_prompt,
        build_regional_joint_scene_prompts,
        format_individual_spatial_joint_prompt_snapshot,
        format_regional_joint_prompt_snapshot,
        format_joint_prompt_snapshot,
        identity_lock_overscan,
    )
    from .generation_contract import (
        CANONICAL_REFERENCE_MODES,
        SUPPORTED_REFERENCE_MODES,
    )
    from .poster_io import (
        POSTER_ASSETS,
        load_cutout_items,
        load_poster_scope_data,
        poster_asset_slug,
        poster_bundle,
    )
except ImportError:
    from grounding import grounding_config
    from poster_config import GROUNDED_PROMPT_FILE, build_grounded_prompt_snapshot
    from composition import (
        joint_scene_canvas_placements,
        normalized_visible_placement_contract,
    )
    from layout import (
        build_source_layout,
        latent_canvas_dimensions,
        page_canvas_dimensions,
    )
    from poster_config import (
        IDENTITY_LOCK_PROMPT_FILE,
        INDIVIDUAL_SPATIAL_JOINT_PROMPT_FILE,
        JOINT_SCENE_PROMPT_FILE,
        REGIONAL_JOINT_SCENE_PROMPT_FILE,
        build_individual_spatial_joint_prompt,
        build_joint_scene_prompt,
        build_identity_lock_prompt,
        build_regional_joint_scene_prompts,
        format_individual_spatial_joint_prompt_snapshot,
        format_regional_joint_prompt_snapshot,
        format_joint_prompt_snapshot,
        identity_lock_overscan,
    )
    from generation_contract import (
        CANONICAL_REFERENCE_MODES,
        SUPPORTED_REFERENCE_MODES,
    )
    from poster_io import (
        POSTER_ASSETS,
        load_cutout_items,
        load_poster_scope_data,
        poster_asset_slug,
        poster_bundle,
    )


ROOT = Path(__file__).resolve().parents[2]
REGIONAL_GLOBAL_SCENE_STRENGTH = 0.2


def node(class_type: str, **inputs: object) -> dict[str, object]:
    return {"class_type": class_type, "inputs": inputs}


def megapixel_marker(megapixels: float) -> str:
    return f"{megapixels:g}mp".replace(".", "p")


def is_flux2_dev_model(unet_name: str) -> bool:
    """Select the official Dev guider graph from the configured model name."""
    normalized = Path(unet_name).name.lower().replace("-", "_").replace(".", "_")
    return "flux2_dev" in normalized or "flux_2_dev" in normalized


def output_dimensions(scope: str, megapixels: float) -> tuple[int, int]:
    if megapixels <= 0:
        raise ValueError("megapixels must be positive")
    manifest = poster_bundle(
        scope,
        poster_assets=POSTER_ASSETS,
    ).manifest
    return latent_canvas_dimensions(
        manifest.get("layout", {}).get("name", "standard_3x3"),
        megapixels,
    )


def regional_conditioning_area(
    contract: dict[str, int],
) -> dict[str, float]:
    """Expand a subject target without aligning conditioning to card edges."""
    left = contract["left_per_mille"]
    right = contract["right_per_mille"]
    top = contract["top_per_mille"]
    bottom = contract["bottom_per_mille"]
    width = min(1000.0, (right - left) * 1.35)
    height = min(1000.0, (bottom - top) * 2.0)
    x = min(max((left + right - width) / 2, 0.0), 1000.0 - width)
    y = min(max((top + bottom - height) / 2, 0.0), 1000.0 - height)
    return {
        "width": width / 1000,
        "height": height / 1000,
        "x": x / 1000,
        "y": y / 1000,
    }


def regional_conditioning_mask(
    area: dict[str, float],
    *,
    canvas_size: tuple[int, int],
) -> dict[str, int]:
    """Return a broad subject mask with soft internal scene transitions."""
    canvas_width, canvas_height = canvas_size
    x = round(area["x"] * canvas_width)
    y = round(area["y"] * canvas_height)
    width = min(
        canvas_width - x,
        max(1, round(area["width"] * canvas_width)),
    )
    height = min(
        canvas_height - y,
        max(1, round(area["height"] * canvas_height)),
    )
    horizontal_feather = round(width * 0.25)
    vertical_feather = round(height * 0.25)
    return {
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "left": 0 if x == 0 else horizontal_feather,
        "top": 0 if y == 0 else vertical_feather,
        "right": (
            0
            if x + width >= canvas_width
            else horizontal_feather
        ),
        "bottom": (
            0
            if y + height >= canvas_height
            else vertical_feather
        ),
    }


def page_dimensions(scope: str, megapixels: float) -> tuple[int, int]:
    """Return an exact physical card-grid ratio using the latent-aligned width."""
    manifest = poster_bundle(
        scope,
        poster_assets=POSTER_ASSETS,
    ).manifest
    return page_canvas_dimensions(
        manifest.get("layout", {}).get("name", "standard_3x3"),
        megapixels,
    )


def _build_full_frame_reference_workflow(
    *,
    prompt: str,
    reference_names: tuple[str, ...],
    width: int,
    height: int,
    seed: int,
    unet_name: str,
    clip_name: str,
    vae_name: str,
    steps: int,
    filename_prefix: str,
) -> dict[str, object]:
    """Build one empty-target sampler conditioned by ordered image references."""
    dev_profile = is_flux2_dev_model(unet_name)
    workflow: dict[str, object] = {
        "1": node("UNETLoader", unet_name=unet_name, weight_dtype="default"),
        "2": node(
            "CLIPLoader",
            clip_name=clip_name,
            type="flux2",
            device="default",
        ),
        "3": node("VAELoader", vae_name=vae_name),
        "4": node("CLIPTextEncode", text=prompt, clip=["2", 0]),
        "6": node(
            "EmptyFlux2LatentImage",
            width=width,
            height=height,
            batch_size=1,
        ),
        "7": node(
            "Flux2Scheduler",
            steps=steps,
            width=width,
            height=height,
        ),
        "8": node("RandomNoise", noise_seed=seed),
        "10": node("KSamplerSelect", sampler_name="euler"),
    }

    if dev_profile:
        workflow["60"] = node(
            "FluxGuidance",
            conditioning=["4", 0],
            guidance=4.0,
        )
        positive_conditioning: list[object] = ["60", 0]
        negative_conditioning: list[object] | None = None
    else:
        workflow["5"] = node("ConditioningZeroOut", conditioning=["4", 0])
        positive_conditioning = ["4", 0]
        negative_conditioning = ["5", 0]
    for index, reference_name in enumerate(reference_names):
        load_id = str(30 + index * 4)
        encode_id = str(31 + index * 4)
        positive_id = str(32 + index * 4)
        negative_id = str(33 + index * 4)
        workflow[load_id] = node("LoadImage", image=reference_name)
        workflow[encode_id] = node(
            "VAEEncode",
            pixels=[load_id, 0],
            vae=["3", 0],
        )
        workflow[positive_id] = node(
            "ReferenceLatent",
            conditioning=positive_conditioning,
            latent=[encode_id, 0],
        )
        positive_conditioning = [positive_id, 0]
        if negative_conditioning is not None:
            workflow[negative_id] = node(
                "ReferenceLatent",
                conditioning=negative_conditioning,
                latent=[encode_id, 0],
            )
            negative_conditioning = [negative_id, 0]

    if dev_profile:
        workflow["70"] = node(
            "BasicGuider",
            model=["1", 0],
            conditioning=positive_conditioning,
        )
    else:
        workflow["70"] = node(
            "CFGGuider",
            model=["1", 0],
            positive=positive_conditioning,
            negative=negative_conditioning,
            cfg=1.0,
        )
    workflow["71"] = node(
        "SamplerCustomAdvanced",
        noise=["8", 0],
        guider=["70", 0],
        sampler=["10", 0],
        sigmas=["7", 0],
        latent_image=["6", 0],
    )
    workflow["72"] = node(
        "VAEDecode",
        samples=["71", 0],
        vae=["3", 0],
    )
    workflow["73"] = node(
        "SaveImage",
        images=["72", 0],
        filename_prefix=filename_prefix,
    )
    return workflow


def build_joint_scene_workflow(
    scope: str,
    seed: int,
    megapixels: float,
    *,
    unet_name: str,
    clip_name: str,
    vae_name: str,
    steps: int,
) -> dict[str, object]:
    """Build one whole-image pass from spatial and identity references."""
    bundle = poster_bundle(scope, poster_assets=POSTER_ASSETS)
    manifest = bundle.manifest
    scope_data = load_poster_scope_data(bundle)
    items = load_cutout_items(bundle.source_dir)
    width, height = output_dimensions(scope, megapixels)
    placement_contract = normalized_visible_placement_contract(
        joint_scene_canvas_placements(
            bundle.source_dir,
            layout_name=str(
                manifest.get("layout", {}).get(
                    "name",
                    "standard_3x3",
                )
            ),
            canvas_size=(width, height),
        ),
        canvas_size=(width, height),
    )
    final_prompt = build_joint_scene_prompt(
        manifest,
        scope_data,
        items,
        placement_contract=placement_contract,
    )

    reference_names = (
        "joint_scene_cast_reference.png",
        *(
            f"identity_reference_{index}.png"
            for index in range(1, len(items) + 1)
        ),
    )
    return _build_full_frame_reference_workflow(
        prompt=final_prompt,
        reference_names=reference_names,
        width=width,
        height=height,
        seed=seed,
        unet_name=unet_name,
        clip_name=clip_name,
        vae_name=vae_name,
        steps=steps,
        filename_prefix=(
            f"{poster_asset_slug(scope)}_flux2_joint_scene_"
            f"{megapixel_marker(megapixels)}_seed_{seed}"
        ),
    )


def build_individual_spatial_prompt(
    scope: str,
    *,
    megapixels: float,
) -> str:
    """Build the reviewed prompt for one positioned reference per subject."""
    bundle = poster_bundle(scope, poster_assets=POSTER_ASSETS)
    manifest = bundle.manifest
    items = load_cutout_items(bundle.source_dir)
    width, height = output_dimensions(scope, megapixels)
    layout_name = str(
        manifest.get("layout", {}).get("name", "standard_3x3")
    )
    placement_contract = normalized_visible_placement_contract(
        joint_scene_canvas_placements(
            bundle.source_dir,
            layout_name=layout_name,
            canvas_size=(width, height),
        ),
        canvas_size=(width, height),
    )
    return build_individual_spatial_joint_prompt(
        manifest,
        load_poster_scope_data(bundle),
        items,
        placement_contract=placement_contract,
    )


def build_individual_spatial_joint_workflow(
    scope: str,
    seed: int,
    megapixels: float,
    *,
    unet_name: str,
    clip_name: str,
    vae_name: str,
    steps: int,
) -> dict[str, object]:
    """Build one full-frame sampler from one positioned identity per subject."""
    bundle = poster_bundle(scope, poster_assets=POSTER_ASSETS)
    items = load_cutout_items(bundle.source_dir)
    width, height = output_dimensions(scope, megapixels)
    reference_names = tuple(
        f"individual_spatial_reference_{index}.png"
        for index in range(1, len(items) + 1)
    )
    return _build_full_frame_reference_workflow(
        prompt=build_individual_spatial_prompt(
            scope,
            megapixels=megapixels,
        ),
        reference_names=reference_names,
        width=width,
        height=height,
        seed=seed,
        unet_name=unet_name,
        clip_name=clip_name,
        vae_name=vae_name,
        steps=steps,
        filename_prefix=(
            f"{poster_asset_slug(scope)}_flux2_joint_scene_"
            f"individual_spatial_{megapixel_marker(megapixels)}_seed_{seed}"
        ),
    )


def build_regional_joint_scene_workflow(
    scope: str,
    seed: int,
    megapixels: float,
    *,
    unet_name: str,
    clip_name: str,
    vae_name: str,
    steps: int,
) -> dict[str, object]:
    """Build one cast-free pass with one identity-bound subject-safe region."""
    bundle = poster_bundle(scope, poster_assets=POSTER_ASSETS)
    manifest = bundle.manifest
    scope_data = load_poster_scope_data(bundle)
    items = load_cutout_items(bundle.source_dir)
    width, height = output_dimensions(scope, megapixels)
    layout_name = str(
        manifest.get("layout", {}).get(
            "name",
            "standard_3x3",
        )
    )
    layout = build_source_layout(
        layout_name,
        width_px=width,
        height_px=height,
    )
    placements = joint_scene_canvas_placements(
        bundle.source_dir,
        layout_name=layout_name,
        canvas_size=(width, height),
    )
    placement_contract = normalized_visible_placement_contract(
        placements,
        canvas_size=(width, height),
    )
    global_prompt, subject_prompts = build_regional_joint_scene_prompts(
        manifest,
        scope_data,
        items,
        placement_contract=placement_contract,
    )

    workflow = {
        "1": node("UNETLoader", unet_name=unet_name, weight_dtype="default"),
        "2": node(
            "CLIPLoader",
            clip_name=clip_name,
            type="flux2",
            device="default",
        ),
        "3": node("VAELoader", vae_name=vae_name),
        "4": node("CLIPTextEncode", text=global_prompt, clip=["2", 0]),
        "5": node("ConditioningZeroOut", conditioning=["4", 0]),
        "6": node(
            "EmptyFlux2LatentImage",
            width=width,
            height=height,
            batch_size=1,
        ),
        "7": node(
            "Flux2Scheduler",
            steps=steps,
            width=width,
            height=height,
        ),
        "8": node("RandomNoise", noise_seed=seed),
        "9": node(
            "ConditioningSetAreaStrength",
            conditioning=["4", 0],
            strength=REGIONAL_GLOBAL_SCENE_STRENGTH,
        ),
        "10": node("KSamplerSelect", sampler_name="euler"),
        "11": node("SolidMask", value=0.0, width=width, height=height),
    }

    regional_conditioning: list[list[object]] = []
    for index, (contract, prompt) in enumerate(
        zip(placement_contract, subject_prompts, strict=True),
        start=1,
    ):
        base = 20 + (index - 1) * 10
        prompt_id = str(base)
        load_id = str(base + 1)
        encode_id = str(base + 2)
        reference_id = str(base + 3)
        solid_mask_id = str(base + 4)
        feather_mask_id = str(base + 5)
        composite_mask_id = str(base + 6)
        masked_conditioning_id = str(base + 7)
        area = regional_conditioning_area(contract)
        mask = regional_conditioning_mask(
            area,
            canvas_size=(width, height),
        )
        workflow[prompt_id] = node(
            "CLIPTextEncode",
            text=prompt,
            clip=["2", 0],
        )
        workflow[load_id] = node(
            "LoadImage",
            image=f"identity_reference_{index}.png",
        )
        workflow[encode_id] = node(
            "VAEEncode",
            pixels=[load_id, 0],
            vae=["3", 0],
        )
        workflow[reference_id] = node(
            "ReferenceLatent",
            conditioning=[prompt_id, 0],
            latent=[encode_id, 0],
        )
        workflow[solid_mask_id] = node(
            "SolidMask",
            value=1.0,
            width=mask["width"],
            height=mask["height"],
        )
        workflow[feather_mask_id] = node(
            "FeatherMask",
            mask=[solid_mask_id, 0],
            left=mask["left"],
            top=mask["top"],
            right=mask["right"],
            bottom=mask["bottom"],
        )
        workflow[composite_mask_id] = node(
            "MaskComposite",
            destination=["11", 0],
            source=[feather_mask_id, 0],
            x=mask["x"],
            y=mask["y"],
            operation="add",
        )
        workflow[masked_conditioning_id] = node(
            "ConditioningSetMask",
            conditioning=[reference_id, 0],
            mask=[composite_mask_id, 0],
            set_cond_area="mask bounds",
            strength=1.0,
        )
        regional_conditioning.append([masked_conditioning_id, 0])

    combine_start = max(60, 20 + len(placement_contract) * 10)
    combined = regional_conditioning[0]
    for offset, current in enumerate(
        regional_conditioning[1:],
        start=0,
    ):
        combine_id = str(combine_start + offset)
        workflow[combine_id] = node(
            "ConditioningCombine",
            conditioning_1=combined,
            conditioning_2=current,
        )
        combined = [combine_id, 0]
    final_start = max(
        69,
        combine_start + len(regional_conditioning) - 1,
    )
    positive_id = str(final_start)
    guider_id = str(final_start + 1)
    sampler_id = str(final_start + 2)
    decode_id = str(final_start + 3)
    save_id = str(final_start + 4)
    workflow[positive_id] = node(
        "ConditioningCombine",
        conditioning_1=combined,
        conditioning_2=["9", 0],
    )
    workflow[guider_id] = node(
        "CFGGuider",
        model=["1", 0],
        positive=[positive_id, 0],
        negative=["5", 0],
        cfg=1.0,
    )
    workflow[sampler_id] = node(
        "SamplerCustomAdvanced",
        noise=["8", 0],
        guider=[guider_id, 0],
        sampler=["10", 0],
        sigmas=["7", 0],
        latent_image=["6", 0],
    )
    workflow[decode_id] = node(
        "VAEDecode",
        samples=[sampler_id, 0],
        vae=["3", 0],
    )
    workflow[save_id] = node(
        "SaveImage",
        images=[decode_id, 0],
        filename_prefix=(
            f"{poster_asset_slug(scope)}_flux2_joint_scene_"
            f"regional_identity_{megapixel_marker(megapixels)}_seed_{seed}"
        ),
    )
    return workflow


def build_workflow(
    scope: str,
    seed: int,
    megapixels: float,
    *,
    unet_name: str = "flux-2-klein-4b-fp8.safetensors",
    clip_name: str = "qwen_3_4b.safetensors",
    vae_name: str = "flux2-vae.safetensors",
    generation_mode: str = "joint_scene",
    reference_mode: str | None = None,
    steps: int = 4,
) -> dict[str, object]:
    if generation_mode not in {"identity_lock", "joint_scene"}:
        raise ValueError(f"Unsupported FLUX generation mode: {generation_mode}")
    if steps <= 0:
        raise ValueError("steps must be positive")
    key = ("flux", generation_mode)
    effective_reference_mode = (
        reference_mode
        if reference_mode is not None
        else CANONICAL_REFERENCE_MODES[key]
    )
    if effective_reference_mode not in SUPPORTED_REFERENCE_MODES[key]:
        expected = ", ".join(sorted(SUPPORTED_REFERENCE_MODES[key]))
        raise ValueError(
            f"Unsupported reference mode for {generation_mode}: "
            f"{effective_reference_mode!r}; expected one of {expected}"
        )
    if generation_mode == "joint_scene":
        if effective_reference_mode == "individual_spatial_joint":
            return build_individual_spatial_joint_workflow(
                scope,
                seed,
                megapixels,
                unet_name=unet_name,
                clip_name=clip_name,
                vae_name=vae_name,
                steps=steps,
            )
        if effective_reference_mode == "regional_identity_joint":
            return build_regional_joint_scene_workflow(
                scope,
                seed,
                megapixels,
                unet_name=unet_name,
                clip_name=clip_name,
                vae_name=vae_name,
                steps=steps,
            )
        return build_joint_scene_workflow(
            scope,
            seed,
            megapixels,
            unet_name=unet_name,
            clip_name=clip_name,
            vae_name=vae_name,
            steps=steps,
        )
    bundle = poster_bundle(scope, poster_assets=POSTER_ASSETS)
    manifest = bundle.manifest
    prompt = build_identity_lock_prompt(
        manifest,
        load_poster_scope_data(bundle),
    )
    width, height = output_dimensions(scope, megapixels)
    workflow = {
        "1": node("UNETLoader", unet_name=unet_name, weight_dtype="default"),
        "2": node("CLIPLoader", clip_name=clip_name, type="flux2", device="default"),
        "3": node("VAELoader", vae_name=vae_name),
        "4": node("CLIPTextEncode", text=prompt, clip=["2", 0]),
        "5": node("ConditioningZeroOut", conditioning=["4", 0]),
        "7": node("Flux2Scheduler", steps=steps, width=width, height=height),
        "8": node("RandomNoise", noise_seed=seed),
        "9": node("CFGGuider", model=["1", 0], positive=["17", 0], negative=["5", 0], cfg=1.0),
        "10": node("KSamplerSelect", sampler_name="euler"),
        "11": node(
            "SamplerCustomAdvanced",
            noise=["8", 0],
            guider=["9", 0],
            sampler=["10", 0],
            sigmas=["7", 0],
            latent_image=["15", 0],
        ),
        "12": node("VAEDecode", samples=["11", 0], vae=["3", 0]),
        "13": node(
            "SaveImage",
            images=["12", 0],
            filename_prefix=(
                f"{poster_asset_slug(scope)}_flux2_{generation_mode}_"
                f"{megapixel_marker(megapixels)}_scene_seed_{seed}"
            ),
        ),
        "14": node(
            "LoadImage",
            image="inpaint_reference.png",
        ),
    }
    if generation_mode == "identity_lock":
        # Pass one creates a clean, continuous scene without character-shaped
        # context. The reviewed source figures are then placed on that common
        # ground before pass two. Pass two sees their exact final composition
        # but may edit only the upper scene, safely away from every silhouette.
        stage_one_width, stage_one_height = identity_lock_overscan(
            width,
            height,
            manifest,
        )
        workflow["15"] = node(
            "EmptySD3LatentImage",
            width=stage_one_width,
            height=stage_one_height,
            batch_size=1,
        )
        workflow["7"]["inputs"]["width"] = stage_one_width
        workflow["7"]["inputs"]["height"] = stage_one_height
        workflow["9"]["inputs"]["positive"] = ["4", 0]
        workflow["26"] = node(
            "Flux2Scheduler",
            steps=steps,
            width=width,
            height=height,
        )
        workflow["27"] = node(
            "ImageCrop",
            image=["12", 0],
            width=width,
            height=height,
            x=(stage_one_width - width) // 2,
            y=(stage_one_height - height) // 2,
        )
        workflow["18"] = node("InvertMask", mask=["14", 1])
        workflow["19"] = node(
            "ImageCompositeMasked",
            destination=["27", 0],
            source=["14", 0],
            x=0,
            y=0,
            resize_source=False,
            mask=["18", 0],
        )
        if effective_reference_mode == "grounded_source_pixels":
            if steps != 4:
                raise ValueError("Grounded source pixels requires four sampling steps")
            workflow.update(
                {
                    "20": node("LoadImage", image="grounding_mask.png"),
                    "28": node("LoadImage", image="grounding_sampling_mask.png"),
                    "21": node("VAEEncode", pixels=["19", 0], vae=["3", 0]),
                    "22": node("RandomNoise", noise_seed=seed + 1),
                    "29": node(
                        "SetLatentNoiseMask", samples=["21", 0], mask=["28", 1],
                    ),
                    "30": node(
                        "CLIPTextEncode", text=grounding_config(manifest)["prompt"],
                        clip=["2", 0],
                    ),
                    "31": node(
                        "ReferenceLatent", conditioning=["30", 0], latent=["21", 0],
                    ),
                    "32": node(
                        "CFGGuider", model=["1", 0], positive=["31", 0],
                        negative=["5", 0], cfg=1.0,
                    ),
                    "23": node(
                        "SamplerCustomAdvanced", noise=["22", 0],
                        guider=["32", 0], sampler=["10", 0], sigmas=["26", 0],
                        latent_image=["29", 0],
                    ),
                    "24": node("VAEDecode", samples=["23", 0], vae=["3", 0]),
                    "25": node(
                        "ImageCompositeMasked", destination=["19", 0],
                        source=["24", 0], x=0, y=0, resize_source=False,
                        mask=["20", 1],
                    ),
                }
            )
            prefix = (
                f"{poster_asset_slug(scope)}_flux2_grounded_source_pixels_"
                f"{megapixel_marker(megapixels)}_seed_{seed}"
            )
            workflow["13"] = node(
                "SaveImage", images=["25", 0], filename_prefix=prefix + "_final",
            )
            workflow["33"] = node(
                "SaveImage", images=["19", 0], filename_prefix=prefix + "_baseline",
            )
            return workflow
        workflow["20"] = node(
            "LoadImage", image="upper_context_mask.png"
        )
        workflow["28"] = node(
            "LoadImage",
            image="upper_context_generation_mask.png",
        )
        workflow["21"] = node(
            "VAEEncodeForInpaint",
            pixels=["19", 0],
            vae=["3", 0],
            # Sampling uses a separate binary mask whose latent edge lies
            # below the visible RGB feather. Reusing the feather here lets the
            # VAE switch source images around its midpoint and exposes a
            # horizontal brightness seam.
            mask=["28", 1],
            grow_mask_by=0,
        )
        workflow["22"] = node("RandomNoise", noise_seed=seed + 1)
        workflow["23"] = node(
            "SamplerCustomAdvanced",
            noise=["22", 0],
            guider=["9", 0],
            sampler=["10", 0],
            sigmas=["26", 0],
            latent_image=["21", 0],
        )
        workflow["24"] = node(
            "VAEDecode", samples=["23", 0], vae=["3", 0]
        )
        workflow["25"] = node(
            "ImageCompositeMasked",
            destination=["19", 0],
            source=["24", 0],
            x=0,
            y=0,
            resize_source=False,
            mask=["20", 1],
        )
        workflow["13"]["inputs"]["images"] = ["25", 0]
    return workflow


def write_workflow(
    scope: str,
    seed: int,
    megapixels: float,
    *,
    generation_mode: str = "joint_scene",
    reference_mode: str | None = None,
    unet_name: str = "flux-2-klein-4b-fp8.safetensors",
    steps: int = 4,
    clip_name: str = "qwen_3_4b.safetensors",
    vae_name: str = "flux2-vae.safetensors",
    output_dir: Path | None = None,
) -> Path:
    work_dir = poster_bundle(scope, poster_assets=POSTER_ASSETS).work_dir
    target_dir = output_dir or work_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    if generation_mode not in {"identity_lock", "joint_scene"}:
        raise ValueError(f"Unsupported FLUX generation mode: {generation_mode}")
    key = ("flux", generation_mode)
    effective_reference_mode = (
        reference_mode
        if reference_mode is not None
        else CANONICAL_REFERENCE_MODES[key]
    )
    workflow_marker = generation_mode
    if effective_reference_mode == "grounded_source_pixels":
        workflow_marker += "_grounded_source_pixels"
    if (
        generation_mode == "joint_scene"
        and effective_reference_mode != "spatial_identity_joint"
    ):
        workflow_marker += f"_{effective_reference_mode}"
    out_path = target_dir / (
        f"workflow_api_{workflow_marker}_"
        f"{megapixel_marker(megapixels)}_{seed}.json"
    )
    workflow = build_workflow(
        scope,
        seed,
        megapixels,
        unet_name=unet_name,
        generation_mode=generation_mode,
        reference_mode=effective_reference_mode,
        steps=steps,
        clip_name=clip_name,
        vae_name=vae_name,
    )
    if effective_reference_mode == "grounded_source_pixels":
        bundle = poster_bundle(scope, poster_assets=POSTER_ASSETS)
        (target_dir / GROUNDED_PROMPT_FILE).write_text(
            build_grounded_prompt_snapshot(
                bundle.manifest, load_poster_scope_data(bundle),
            ) + "\n",
            encoding="utf-8",
        )
    elif generation_mode == "identity_lock":
        (target_dir / IDENTITY_LOCK_PROMPT_FILE).write_text(
            str(workflow["4"]["inputs"]["text"]).strip() + "\n",
            encoding="utf-8",
        )
    elif (
        generation_mode == "joint_scene"
        and effective_reference_mode == "individual_spatial_joint"
    ):
        snapshot = format_individual_spatial_joint_prompt_snapshot(
            str(workflow["4"]["inputs"]["text"])
        )
        (target_dir / INDIVIDUAL_SPATIAL_JOINT_PROMPT_FILE).write_text(
            snapshot.strip() + "\n",
            encoding="utf-8",
        )
    elif (
        generation_mode == "joint_scene"
        and effective_reference_mode == "spatial_identity_joint"
    ):
        snapshot = format_joint_prompt_snapshot(
            str(workflow["4"]["inputs"]["text"])
        )
        (target_dir / JOINT_SCENE_PROMPT_FILE).write_text(
            snapshot.strip() + "\n",
            encoding="utf-8",
        )
    elif generation_mode == "joint_scene":
        items = load_cutout_items(
            poster_bundle(scope, poster_assets=POSTER_ASSETS).source_dir
        )
        snapshot = format_regional_joint_prompt_snapshot(
            str(workflow["4"]["inputs"]["text"]),
            items,
            [
                str(workflow[str(20 + index * 10)]["inputs"]["text"])
                for index in range(len(items))
            ],
        )
        (target_dir / REGIONAL_JOINT_SCENE_PROMPT_FILE).write_text(
            snapshot.strip() + "\n",
            encoding="utf-8",
        )
    out_path.write_text(
        json.dumps(
            workflow,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", default="Base1")
    parser.add_argument("--seed", type=int, default=260715201)
    parser.add_argument("--megapixels", type=float, default=1.0)
    parser.add_argument(
        "--mode",
        choices=("joint_scene", "identity_lock"),
        default="joint_scene",
    )
    parser.add_argument(
        "--reference-mode",
        choices=(
            "individual_spatial_joint",
            "spatial_identity_joint",
            "regional_identity_joint",
            "two_pass_source_pixels",
            "grounded_source_pixels",
        ),
    )
    parser.add_argument("--model", default="flux-2-klein-4b-fp8.safetensors")
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--clip", default="qwen_3_4b.safetensors")
    parser.add_argument("--vae", default="flux2-vae.safetensors")
    args = parser.parse_args()
    print(
        write_workflow(
            args.scope,
            args.seed,
            args.megapixels,
            generation_mode=args.mode,
            reference_mode=args.reference_mode,
            unet_name=args.model,
            steps=args.steps,
            clip_name=args.clip,
            vae_name=args.vae,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
