"""Configuration helpers shared by local poster-generation engines."""
from __future__ import annotations

import math
from typing import Any

try:
    from .grounding import grounding_config
    from .generation_contract import (
        INDIVIDUAL_SPATIAL_REFERENCE_MEGAPIXELS,
        JOINT_SCENE_CAST_MAX_MEGAPIXELS,
        JOINT_SCENE_IDENTITY_CANVAS_PX,
    )
    from .layout import resolve_layout_name
    from .poster_subject import resolve_poster_subject
except ImportError:
    from grounding import grounding_config
    from generation_contract import (
        INDIVIDUAL_SPATIAL_REFERENCE_MEGAPIXELS,
        JOINT_SCENE_CAST_MAX_MEGAPIXELS,
        JOINT_SCENE_IDENTITY_CANVAS_PX,
    )
    from layout import resolve_layout_name
    from poster_subject import resolve_poster_subject


IDENTITY_LOCK_PROMPT_FILE = "identity_lock_prompt.generated.txt"
GROUNDED_PROMPT_FILE = "grounded_source_pixels_prompt.generated.txt"
JOINT_SCENE_PROMPT_FILE = "joint_scene_prompt.generated.txt"
INDIVIDUAL_SPATIAL_JOINT_PROMPT_FILE = (
    "individual_spatial_joint_prompt.generated.txt"
)
REGIONAL_JOINT_SCENE_PROMPT_FILE = (
    "joint_scene_regional_identity_prompt.generated.txt"
)
DEFAULT_IDENTITY_LOCK = {
    "overscan_ratio": 0.04,
    "max_protected_start_ratio": 0.70,
    "transition_ratio": 0.10,
    "subject_clearance_ratio": 0.02,
}


def build_grounded_prompt_snapshot(manifest: dict, scope_data: dict) -> str:
    """Audit the two independently encoded prompts in their graph order."""
    return (
        "SCENE PROMPT\n" + build_identity_lock_prompt(manifest, scope_data)
        + "\n\nGROUNDING PROMPT\n" + grounding_config(manifest)["prompt"]
    )


def _mapping(value: object, path: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be a mapping")
    return value


def _text(value: object, path: str, *, default: str = "") -> str:
    if value is None:
        return default
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be a non-empty string")
    return value.strip()


def _scene_constraints(scene: dict[str, Any]) -> list[str]:
    """Return validated scope-specific constraints for every scene pass."""
    constraints = scene.get("constraints", [])
    if isinstance(constraints, str):
        constraints = [constraints]
    if not isinstance(constraints, list) or not all(
        isinstance(item, str) and item.strip() for item in constraints
    ):
        raise ValueError(
            "artwork.scene.constraints must be a string or list of strings"
        )
    return [item.strip() for item in constraints]


def identity_lock_config(manifest: dict[str, Any]) -> dict[str, float]:
    """Return validated, scope-overridable source-pixel-lock geometry."""
    artwork = _mapping(manifest.get("artwork"), "artwork")
    configured = _mapping(
        artwork.get("identity_lock"),
        "artwork.identity_lock",
    )
    result = {
        key: float(configured.get(key, default))
        for key, default in DEFAULT_IDENTITY_LOCK.items()
    }
    if not 0.0 < result["overscan_ratio"] <= 0.20:
        raise ValueError(
            "artwork.identity_lock.overscan_ratio must be between 0 and 0.20"
        )
    if not 0.45 <= result["max_protected_start_ratio"] <= 0.85:
        raise ValueError(
            "artwork.identity_lock.max_protected_start_ratio must be "
            "between 0.45 and 0.85"
        )
    if not 0.02 <= result["transition_ratio"] <= 0.25:
        raise ValueError(
            "artwork.identity_lock.transition_ratio must be between 0.02 and 0.25"
        )
    if not 0.0 <= result["subject_clearance_ratio"] <= 0.10:
        raise ValueError(
            "artwork.identity_lock.subject_clearance_ratio must be "
            "between 0 and 0.10"
        )
    if (
        result["transition_ratio"]
        >= result["max_protected_start_ratio"]
    ):
        raise ValueError(
            "artwork.identity_lock.transition_ratio must be smaller than "
            "max_protected_start_ratio"
        )
    return result


def identity_lock_overscan(
    width: int,
    height: int,
    manifest: dict[str, Any],
) -> tuple[int, int]:
    """Return latent-aligned stage-one dimensions for any poster layout."""
    if width <= 0 or height <= 0:
        raise ValueError("Poster dimensions must be positive")
    ratio = identity_lock_config(manifest)["overscan_ratio"]

    def expanded(value: int) -> int:
        result = round((value * (1.0 + ratio)) / 16) * 16
        if result <= value:
            result = value + 16
        return result

    return expanded(width), expanded(height)


def _layout_region(
    row: int,
    column: int,
    rows: int,
    columns: int,
) -> str:
    if not 1 <= row <= rows or not 1 <= column <= columns:
        raise ValueError(
            f"Text cell ({row}, {column}) lies outside {columns}x{rows} layout"
        )

    if rows == 1:
        vertical = ""
    elif row == 1:
        vertical = "upper"
    elif row == rows:
        vertical = "lower"
    elif rows == 3 and row == 2:
        vertical = "middle"
    else:
        vertical = f"row-{row}"

    if columns == 1:
        horizontal = "center"
    elif columns == 2:
        horizontal = ("left", "right")[column - 1]
    elif columns == 3:
        horizontal = ("left", "center", "right")[column - 1]
    else:
        horizontal = f"column-{column}"
    return "-".join(part for part in (vertical, horizontal) if part)


def _safe_area_regions(manifest: dict[str, Any]) -> tuple[str, str]:
    layout_name = _mapping(manifest.get("layout"), "layout").get(
        "name",
        "standard_3x3",
    )
    layout = resolve_layout_name(str(layout_name))
    rows = int(layout["rows"])
    columns = int(layout["columns"])
    text_cells = _mapping(manifest.get("text_cells"), "text_cells")
    title = _mapping(
        text_cells.get("title", {"row": 1, "column": max(1, (columns + 1) // 2)}),
        "text_cells.title",
    )
    information = _mapping(
        text_cells.get(
            "set_info",
            {"row": min(2, rows), "column": max(1, (columns + 1) // 2)},
        ),
        "text_cells.set_info",
    )
    title_region = _layout_region(
        int(title["row"]),
        int(title["column"]),
        rows,
        columns,
    )
    information_region = _layout_region(
        int(information["row"]),
        int(information["column"]),
        rows,
        columns,
    )
    return title_region, information_region


def _safe_area_sentence(
    manifest: dict[str, Any],
    scene: dict[str, Any],
) -> str:
    explicit = scene.get("safe_areas")
    if explicit is not None:
        return _text(
            explicit,
            "artwork.scene.safe_areas",
        )

    title_region, information_region = _safe_area_regions(manifest)
    if title_region == information_region:
        return (
            f"Keep the entire {title_region} cell as uninterrupted, "
            "low-detail atmosphere with no object, emblem, signage, "
            "lettering, or high-contrast focal detail."
        )
    return (
        f"Keep the entire {title_region} cell as uninterrupted, low-detail "
        "atmosphere with no object, emblem, signage, lettering, or "
        f"high-contrast focal detail. Keep the {information_region} cell "
        "open and low contrast with no foreground object, structure, or "
        "focal subject."
    )


def _default_scene_concept(
    manifest: dict[str, Any],
    scope_data: dict[str, Any],
) -> str:
    set_name = str(
        scope_data.get("name")
        or manifest.get("scope")
        or "this card set"
    ).strip()
    series = str(
        scope_data.get("serie_name")
        or scope_data.get("serie")
        or ""
    ).strip()
    release_date = str(scope_data.get("release_date") or "").strip()
    year = release_date[:4] if len(release_date) >= 4 else ""
    details = f"the {set_name} expansion"
    if series and series.lower() not in set_name.lower():
        series_label = (
            series
            if series.lower().endswith("series")
            else f"{series} series"
        )
        details += f" from the {series_label}"
    if year.isdigit():
        details += f", released in {year}"
    return f"a creature-collecting card-set collection inspired by {details}"


def build_identity_lock_prompt(
    manifest: dict[str, Any],
    scope_data: dict[str, Any],
) -> str:
    """Build the production landscape prompt from one scope's creative brief.

    The manifest controls only the creative scene. The source-pixel contract,
    layout-safe regions, continuous-ground rule, and graphic exclusions remain
    centralized so a newly initialized scope cannot silently omit them.
    """
    artwork = _mapping(manifest.get("artwork"), "artwork")
    scene = _mapping(artwork.get("scene"), "artwork.scene")
    concept = _text(
        scene.get("concept"),
        "artwork.scene.concept",
        default=_default_scene_concept(manifest, scope_data),
    )
    setting = _text(
        scene.get("setting"),
        "artwork.scene.setting",
        default=(
            "The artwork contains a broad natural landscape whose terrain, "
            "flora, distant landmarks, and atmosphere subtly echo the set's "
            "theme without copying existing card art."
        ),
    )
    lighting = _text(
        scene.get("lighting"),
        "artwork.scene.lighting",
        default="Soft directional daylight enters from the upper left.",
    )
    rendering = _text(
        scene.get("rendering"),
        "artwork.scene.rendering",
        default=(
            "Use polished trading-card illustration, clean cel-painted "
            "linework, restrained natural colors, and gentle atmospheric depth."
        ),
    )
    ground_noun = _text(
        scene.get("ground_noun"),
        "artwork.scene.ground_noun",
        default="ground",
    )
    safe_areas = _safe_area_sentence(manifest, scene)
    additional = _scene_constraints(scene)

    opening = " ".join(
        part.strip()
        for part in (setting, lighting, rendering, *additional)
        if part.strip()
    )
    return "\n\n".join(
        (
            (
                "Create one cohesive full-bleed vertical scene for "
                f"{concept}. {opening}"
            ),
            (
                "The complete protected lower subject band is one continuous "
                f"low {ground_noun} surface with only short, low-contrast "
                "texture and soft horizontal shadows. It is a single natural "
                "ground plane, never separate clearings, halos, platforms, "
                "circles, or landing pads. Put no tall plants, flowers, rocks, "
                "bushes, branches, strong color patches, hard-edged shadows, "
                "vertical strokes, or isolated foreground objects in this "
                "lower band."
            ),
            (
                "If finished opaque source subjects are visible, they are the "
                "exact final cast and their final composition. Treat every "
                "source pixel as immutable. Build one consistent environment "
                "for them without replacing, continuing, tracing, redrawing, "
                "echoing, duplicating, or adding anatomy to them. Draw no "
                "additional living subject, face, eyes, body, mascot, animal, "
                "creature, person, trainer, statue, silhouette, or "
                "character-shaped plant anywhere."
            ),
            (
                "Fill the image naturally to every edge with no margin, page, "
                f"frame, or border. {safe_areas} The {ground_noun} is "
                "continuous, with no path or route. Do not draw text, letters, "
                "numbers, logos, title art, boxes, plaques, panels, cards, "
                "borders, UI, watermarks, or crop marks."
            ),
        )
    )


def build_joint_scene_prompt(
    manifest: dict[str, Any],
    scope_data: dict[str, Any],
    items: list[dict[str, Any]],
    *,
    placement_contract: list[dict[str, int]],
    prefer_natural_separation: bool = True,
    avoid_foreground_intersections: bool = True,
) -> str:
    """Build one final-scene prompt from spatial and identity references."""
    if not items:
        raise ValueError("Joint scene generation needs at least one subject")
    artwork = _mapping(manifest.get("artwork"), "artwork")
    scene = _mapping(artwork.get("scene"), "artwork.scene")
    concept = _text(
        scene.get("concept"),
        "artwork.scene.concept",
        default=_default_scene_concept(manifest, scope_data),
    )
    setting = _text(
        scene.get("setting"),
        "artwork.scene.setting",
        default=(
            "Build a broad natural landscape whose terrain, flora, distant "
            "landmarks, and atmosphere subtly echo the set's theme."
        ),
    )
    lighting = _text(
        scene.get("lighting"),
        "artwork.scene.lighting",
        default="Soft directional daylight enters from the upper left.",
    )
    rendering = _text(
        scene.get("rendering"),
        "artwork.scene.rendering",
        default=(
            "Use polished trading-card illustration, clean cel-painted "
            "linework, restrained natural colors, and gentle atmospheric depth."
        ),
    )
    ground_noun = _text(
        scene.get("ground_noun"),
        "artwork.scene.ground_noun",
        default="ground",
    )
    safe_areas = _safe_area_sentence(manifest, scene)
    additional = _scene_constraints(scene)
    final_scene_description = " ".join(
        part.strip()
        for part in (setting, lighting, rendering, *additional)
        if part.strip()
    )
    cast_names = [
        str(
            item.get("name_en")
            or f"Pokemon #{item.get('pokemon_id', '?')}"
        )
        for item in items
    ]
    if len(cast_names) == 1:
        cast = cast_names[0]
    else:
        cast = ", ".join(cast_names[:-1]) + f", and {cast_names[-1]}"
    if avoid_foreground_intersections:
        separation_guidance = (
            "Treat every mandatory character silhouette bound and its "
            "surrounding two-percent clearance as an invisible no-crossing "
            "volume for camera-near landscape elements. Inside these volumes, "
            "continue only the same low ground plane and unobtrusive ground "
            "texture beneath the feet. Place foreground and midground grass "
            "tufts, tall blades, leaves, flowers, branches, rocks, water "
            "edges, and other scenery outside the volumes or clearly behind "
            "the characters. This is ordinary natural spacing, never a "
            "visible clearing, halo, platform, path, circle, landing pad, or "
            "character-shaped gap. "
        )
        intersection_guidance = (
            "Avoid landscape-character intersections instead of trying to "
            "repair their depth order. If any nearer landscape element would "
            "cross a character silhouette, relocate, bend, shorten, or lower "
            "that landscape element during the unified synthesis. Keep the "
            "continuous landscape naturally detailed around the protected "
            "volumes and keep every complete print-safe silhouette readable."
        )
        permitted_adjustments = (
            "Permitted changes are limited to scene lighting, reflected color, "
            "and cast shadow. Do not conceal any character part with landscape "
            "occlusion. Do "
        )
    else:
        separation_guidance = (
            "Prefer clean natural separation: arrange nearer landscape "
            "elements around, rather than across, every character silhouette. "
            "Achieve this through ordinary composition and spacing, never "
            "through halos, artificial gaps, isolated clearings, or "
            "character-shaped empty areas. "
            if prefer_natural_separation
            else ""
        )
        intersection_guidance = (
            "Resolve depth ordering explicitly at every "
            "landscape-character intersection. A blade, leaf, branch, rock, "
            "water edge, or other landscape element that is genuinely "
            "closer to the camera must continue naturally in front of the "
            "corresponding small exterior part of the character; never "
            "truncate that element exactly at the character silhouette and "
            "never paint the character as a flat top layer. A connected "
            "plant, leaf cluster, stem, branch, or other continuous object "
            "must keep the same physically plausible depth relationship "
            "along its visible length instead of arbitrarily switching from "
            "behind a character to in front of it. Landscape elements that "
            "are farther away remain naturally behind. If a closer element "
            "would hide an identity-critical body part, marking, facial "
            "feature, or silhouette detail, bend, move, shorten, lower, or "
            "regenerate that landscape element instead of placing the "
            "character over it. Keep defining anatomy and the print-safe "
            "silhouette readable."
        )
        permitted_adjustments = (
            "Permitted changes are limited to scene lighting, reflected color, "
            "cast shadow, and small physically plausible edge occlusions. Do "
        )

    return "\n\n".join(
        (
            build_spatial_identity_reference_prompt(
                items,
                manifest,
                placement_contract=placement_contract,
            ),
            (
                "Generate the complete final image in one unified denoising "
                "pass from an empty target. There is no supplied landscape "
                "image and no pre-generated background plate. Invent the "
                "landscape around the referenced characters from the first "
                "noise step, and synthesize every final landscape and character "
                "pixel together. There is no later character overlay, mask "
                "repair, silhouette restore, or cutout compositing. Ground "
                "contact, cast shadows, reflected light, color grading, "
                "perspective, and depth must therefore agree naturally."
            ),
            (
                f"Render exactly these {len(items)} characters once: {cast}. "
                "IMAGE 1 is the strict authority for count, pose, orientation, "
                "target scale, baseline, and poster position. The corresponding "
                "individual identity image is the strict authority for each "
                "character's exact silhouette shape, stature, anatomy, facial "
                "features, colors, markings, and defining design details. "
                f"{permitted_adjustments}"
                "not redesign, restyle, humanize, merge, duplicate, simplify, "
                "add, remove, enlarge, or reshape any referenced body part, "
                "appendage, marking, eye, or facial feature. Never invent a "
                "design trait that is absent from that subject's reference."
            ),
            (
                "Match every character's complete silhouette to the normalized "
                "bounding rectangle, scale, baseline, and visible landscape "
                "padding specified above; do not move or enlarge a character "
                "to fill its region. Copy every "
                "visible color boundary, marking contour, small anatomical "
                "detail, and appendage from that character's individual identity "
                "reference. Preserve every open negative "
                "space between limbs, body parts, or appendages: continuous "
                "landscape may remain visible through that gap, but do not "
                "enclose, outline, or fill it as a new body patch. When a small "
                "feature is ambiguous, preserve the reference instead of "
                "simplifying or inventing it."
            ),
            (
                f"Create one cohesive full-bleed scene for {concept}. "
                f"{final_scene_description} The characters and the {ground_noun} "
                "share one camera space and one globally coherent depth order. "
                f"{separation_guidance}"
                f"{intersection_guidance}"
            ),
            (
                f"{safe_areas} Keep one continuous natural {ground_noun} plane "
                "with no character-specific clearings, circles, platforms, "
                "landing pads, spotlight patches, or paths. Fill the image "
                "naturally to every edge. Do not draw extra creatures, people, "
                "trainers, character-shaped scenery, text, letters, numbers, "
                "logos, title art, boxes, plaques, panels, cards, borders, UI, "
                "watermarks, or crop marks."
            ),
        )
    )


def build_joint_prompt_snapshot(
    manifest: dict[str, Any],
    scope_data: dict[str, Any],
    items: list[dict[str, Any]],
    *,
    placement_contract: list[dict[str, int]],
    prefer_natural_separation: bool = True,
    avoid_foreground_intersections: bool = True,
) -> str:
    """Return the one-shot prompt as a stable provenance snapshot."""
    return format_joint_prompt_snapshot(
        build_joint_scene_prompt(
            manifest,
            scope_data,
            items,
            placement_contract=placement_contract,
            prefer_natural_separation=prefer_natural_separation,
            avoid_foreground_intersections=avoid_foreground_intersections,
        )
    )


def build_regional_joint_scene_prompts(
    manifest: dict[str, Any],
    scope_data: dict[str, Any],
    items: list[dict[str, Any]],
    *,
    placement_contract: list[dict[str, int]],
    prefer_natural_separation: bool = True,
    global_scene_everywhere: bool = True,
    repeat_global_scene_in_regions: bool = True,
    local_scene_continuity: bool = True,
    abstract_region_language: bool = True,
    minimal_local_scene_context: bool = True,
    identity_only_local_context: bool = True,
) -> tuple[str, list[str]]:
    """Build one global landscape prompt and one regional prompt per subject."""
    if not items:
        raise ValueError("Regional joint scene generation needs at least one subject")
    if len(placement_contract) != len(items):
        raise ValueError(
            "Regional joint-scene placement contract must describe every subject"
        )

    artwork = _mapping(manifest.get("artwork"), "artwork")
    scene = _mapping(artwork.get("scene"), "artwork.scene")
    concept = _text(
        scene.get("concept"),
        "artwork.scene.concept",
        default=_default_scene_concept(manifest, scope_data),
    )
    setting = _text(
        scene.get("setting"),
        "artwork.scene.setting",
        default=(
            "Build a broad natural landscape whose terrain, flora, distant "
            "landmarks, and atmosphere subtly echo the set's theme."
        ),
    )
    lighting = _text(
        scene.get("lighting"),
        "artwork.scene.lighting",
        default="Soft directional daylight enters from the upper left.",
    )
    rendering = _text(
        scene.get("rendering"),
        "artwork.scene.rendering",
        default=(
            "Use polished trading-card illustration, clean cel-painted "
            "linework, restrained natural colors, and gentle atmospheric depth."
        ),
    )
    ground_noun = _text(
        scene.get("ground_noun"),
        "artwork.scene.ground_noun",
        default="ground",
    )
    safe_areas = _safe_area_sentence(manifest, scene)
    additional = _scene_constraints(scene)
    scene_description = " ".join(
        part.strip()
        for part in (setting, lighting, rendering, *additional)
        if part.strip()
    )
    separation_guidance = (
        "Prefer natural placement that routes nearer landscape elements "
        "around the complete character silhouette without halos, artificial "
        "gaps, or character-shaped clearings. Resolve every remaining "
        "intersection "
        if prefer_natural_separation
        else "Resolve every intersection "
    )
    if global_scene_everywhere:
        global_role = (
            "This full-canvas branch establishes the shared landscape around "
            "and beneath the locally conditioned subjects. Keep every local "
            "subject region part of the same continuous terrain, perspective, "
            "light, atmosphere, and depth. Do not introduce any additional "
            "creatures, people, or trainers beyond those locally conditioned; "
            "do not draw text, logos, signs, boxes, panels, cards, borders, "
            "watermarks, paths, platforms, landing pads, character-shaped "
            "clearings, or crop marks."
        )
    else:
        global_role = (
            "This global branch contains landscape only: no creatures, "
            "people, trainers, text, logos, signs, boxes, panels, cards, "
            "borders, watermarks, paths, platforms, landing pads, "
            "character-shaped clearings, or crop marks."
        )
    global_prompt = (
        "Generate one cohesive full-bleed scene for "
        f"{concept} from an empty target in the shared unified denoising "
        f"pass. {scene_description} Use one continuous natural {ground_noun} "
        f"plane, globally coherent perspective, light, shadows, and depth. "
        f"{safe_areas} {global_role}"
    )

    def percentage(value: int) -> str:
        if not isinstance(value, int) or not 0 <= value <= 1000:
            raise ValueError(
                "Regional joint-scene placement coordinates must be per-mille "
                "integers between 0 and 1000"
            )
        return f"{value / 10:.1f}%"

    local_prompts = []
    for index, (item, contract) in enumerate(
        zip(items, placement_contract, strict=True)
    ):
        if not isinstance(contract, dict):
            raise ValueError(
                "Regional joint-scene placement contract entries must be mappings"
            )
        name = str(
            item.get("name_en")
            or f"Pokemon #{item.get('pokemon_id', '?')}"
        )
        region = reference_region_label(index, len(items))
        if abstract_region_language:
            spatial_region = (
                f"lower-{region} foreground area"
                if region in {"left", "center", "right"}
                else f"bottom foreground area in {region}"
            )
        elif region in {"left", "center", "right"}:
            spatial_region = f"lower-{region} physical card region"
        else:
            spatial_region = f"bottom physical card region in {region}"
        bounds = (
            f"x {percentage(contract['left_per_mille'])} to "
            f"{percentage(contract['right_per_mille'])}, y "
            f"{percentage(contract['top_per_mille'])} to "
            f"{percentage(contract['bottom_per_mille'])}"
        )
        if local_scene_continuity:
            if identity_only_local_context:
                regional_scene_context = (
                    "This is only a local subject-identity condition inside "
                    "the enclosing full-canvas scene. Do not invent, repeat, "
                    "describe, or restyle any environment here; inherit all "
                    "landscape, terrain, horizon, sky, weather, lighting, "
                    "atmosphere, depth, and rendering from the global branch. "
                )
            elif minimal_local_scene_context:
                regional_scene_context = (
                    "This is a local foreground part of one continuous scene "
                    f"for {concept}. Continue only the nearby {ground_noun} "
                    f"beneath the subject. Match this lighting: {lighting} "
                    f"Match this rendering: {rendering} Do not compose another "
                    "horizon, sky, celestial body, rainbow, landmark, distant "
                    "vista, framed scene, or separate landscape here. "
                )
            else:
                regional_scene_context = (
                    "The enclosing poster uses this exact environment and "
                    f"appearance: {scene_description} Treat that description "
                    "only as shared terrain material, palette, weather, "
                    "illumination, camera, and rendering context for this local "
                    f"region. Continue only the nearby {ground_noun} beneath "
                    "the subject; do not compose another horizon, sky panel, "
                    "distant vista, framed scene, or separate landscape here. "
                )
        elif repeat_global_scene_in_regions:
            regional_scene_context = (
                f"{global_prompt} Within this same shared scene, "
            )
        else:
            regional_scene_context = ""
        prompt = (
            f"{regional_scene_context}IMAGE 1 is the sole exact identity and anatomy reference for "
            f"{name}. Generate exactly one complete {name}, once, in the "
            f"{spatial_region} of the globally conditioned full-canvas "
            "scene. Place its complete visible silhouette between "
            f"{bounds} of the overall composition, with natural padding and "
            "ground contact. Make the character the clear dominant subject "
            "of this local foreground area, closely approaching those target "
            "coordinates instead of "
            "shrinking into a distant figure. Preserve the "
            "reference's exact silhouette, stature, anatomy, face, colors, "
            "markings, limbs, appendages, and defining details; do not "
            "redesign, restyle, humanize, merge, duplicate, simplify, add, "
            "remove, enlarge, or reshape any body part. "
        )
        if global_scene_everywhere:
            if abstract_region_language:
                prompt += (
                    "The full-canvas global landscape conditioning remains "
                    "active here. Continue its terrain, camera, horizon, "
                    "palette, lighting, atmosphere, perspective, and depth "
                    "seamlessly. Add only the character, its coherent ground "
                    "contact, contact shadow, and reflected light in the "
                    "shared unified denoising pass. Keep the landscape "
                    "uninterrupted and unframed. "
                )
            else:
                prompt += (
                    "The full-canvas global landscape conditioning remains active "
                    "inside this region. Inherit its terrain, camera, horizon, "
                    "palette, lighting, atmosphere, perspective, and depth without "
                    "creating or restyling a separate background patch, clearing, "
                    "platform, card-shaped zone, or lighting field. Add only the "
                    "character, its coherent ground contact, contact shadow, and "
                    "reflected light in the shared unified denoising pass. "
                )
        else:
            prompt += (
                "Generate the "
                f"character, local {ground_noun}, contact shadow, nearby "
                "vegetation, reflected light, and scene edges together in the "
                "shared unified denoising pass. "
            )
        prompt += (
            f"{separation_guidance}"
            "physically: a connected landscape element closer to the camera "
            "may continue naturally in front of a small exterior part, while "
            "farther elements stay behind; never truncate vegetation at the "
            "character silhouette or paint the character as a flat top layer. "
            "Move landscape elements instead of hiding identity-critical "
            "anatomy. No other creature, text, logo, box, panel, platform, "
            "path, border, watermark, or crop mark."
        )
        specific_notes = subject_prompt_notes([item], manifest)
        if specific_notes:
            prompt = f"{prompt}\n\n{' '.join(specific_notes)}"
        local_prompts.append(prompt)

    return global_prompt, local_prompts


def build_regional_joint_prompt_snapshot(
    manifest: dict[str, Any],
    scope_data: dict[str, Any],
    items: list[dict[str, Any]],
    *,
    placement_contract: list[dict[str, int]],
    prefer_natural_separation: bool = True,
    global_scene_everywhere: bool = True,
    repeat_global_scene_in_regions: bool = True,
    local_scene_continuity: bool = True,
    abstract_region_language: bool = True,
    minimal_local_scene_context: bool = True,
    identity_only_local_context: bool = True,
) -> str:
    """Return regional joint-scene prompts as a stable provenance snapshot."""
    global_prompt, local_prompts = build_regional_joint_scene_prompts(
        manifest,
        scope_data,
        items,
        placement_contract=placement_contract,
        prefer_natural_separation=prefer_natural_separation,
        global_scene_everywhere=global_scene_everywhere,
        repeat_global_scene_in_regions=repeat_global_scene_in_regions,
        local_scene_continuity=local_scene_continuity,
        abstract_region_language=abstract_region_language,
        minimal_local_scene_context=minimal_local_scene_context,
        identity_only_local_context=identity_only_local_context,
    )
    return format_regional_joint_prompt_snapshot(
        global_prompt,
        items,
        local_prompts,
    )


def format_regional_joint_prompt_snapshot(
    global_prompt: str,
    items: list[dict[str, Any]],
    local_prompts: list[str],
) -> str:
    """Format the exact regional prompts used by a workflow."""
    if len(items) != len(local_prompts):
        raise ValueError(
            "Regional prompt snapshot must contain one prompt per subject"
        )
    sections = [
        "REGIONAL JOINT SCENE - ONE-SHOT FINAL SYNTHESIS",
        f"GLOBAL LANDSCAPE\n\n{global_prompt}",
    ]
    for index, (item, prompt) in enumerate(
        zip(items, local_prompts, strict=True),
        start=1,
    ):
        name = str(
            item.get("name_en")
            or f"Pokemon #{item.get('pokemon_id', '?')}"
        )
        sections.append(f"LOCAL SUBJECT {index} - {name}\n\n{prompt}")
    return "\n\n".join(sections)


def format_joint_prompt_snapshot(prompt: str) -> str:
    """Add the stable heading shared by saved and fingerprinted prompts."""
    return "\n\n".join(
        ("JOINT SCENE - ONE-SHOT FINAL SYNTHESIS", prompt.strip())
    )


def subject_conditioning(
    manifest: dict[str, Any], item: dict[str, Any]
) -> dict[str, Any]:
    """Return explicit conditioning overrides for one cutout-manifest item."""
    subjects = manifest.get("conditioning", {}).get("subjects", {})
    if not isinstance(subjects, dict):
        raise ValueError("conditioning.subjects must be a mapping")

    pokemon_id = item.get("pokemon_id")
    subject = resolve_poster_subject(item)
    keys: tuple[object, ...] = (
        subject.subject_key,
        subject.official_artwork_id,
        str(subject.official_artwork_id),
        pokemon_id,
        str(pokemon_id),
    )
    config = None
    for key in keys:
        if key in subjects:
            config = subjects[key]
            break
    if config is None:
        return {}
    if not isinstance(config, dict):
        raise ValueError(
            f"Conditioning for Pokemon #{pokemon_id} must be a mapping"
        )
    return config


def joint_scene_conditioning_contract(
    manifest: dict[str, Any],
    items: list[dict[str, Any]],
    reference_mode: str = "spatial_identity_joint",
) -> dict[str, Any]:
    """Return only conditioning fields that affect joint-scene pixels."""
    if not items:
        raise ValueError("Joint-scene conditioning needs at least one subject")
    if reference_mode not in {
        "spatial_source_detail_joint",
        "individual_spatial_joint",
        "spatial_identity_joint",
        "regional_identity_joint",
    }:
        raise ValueError(
            f"Unknown joint-scene reference mode: {reference_mode}"
        )
    conditioning = manifest.get("conditioning", {})
    if not isinstance(conditioning, dict):
        raise ValueError("conditioning must be a mapping")
    identity_defaults = conditioning.get("identity_defaults", {})
    if not isinstance(identity_defaults, dict):
        raise ValueError("conditioning.identity_defaults must be a mapping")
    neutral = identity_defaults.get(
        "neutral_rgb",
        [226, 224, 211],
    )
    if (
        not isinstance(neutral, list)
        or len(neutral) != 3
        or not all(
            isinstance(value, int) and 0 <= value <= 255
            for value in neutral
        )
    ):
        raise ValueError(
            "conditioning.identity_defaults.neutral_rgb must contain "
            "3 RGB integers"
        )
    contract = {
        "reference_strategy": "spatial_cast_plus_unscaled_identity",
        "reference_neutral_rgb": neutral,
        "cast_max_megapixels": JOINT_SCENE_CAST_MAX_MEGAPIXELS,
        "identity_canvas_px": JOINT_SCENE_IDENTITY_CANVAS_PX,
        "identity_source_resampling": "none",
    }
    if reference_mode == "individual_spatial_joint":
        contract = {
            "reference_strategy": "individual_spatial_identity_per_subject",
            "reference_neutral_rgb": neutral,
            "reference_megapixels": (
                INDIVIDUAL_SPATIAL_REFERENCE_MEGAPIXELS
            ),
            "identity_source_resampling": "canonical_card_fit",
        }
    elif reference_mode == "regional_identity_joint":
        contract = {
            "reference_strategy": "regional_identity_per_physical_card",
            "reference_neutral_rgb": neutral,
            "identity_canvas_px": JOINT_SCENE_IDENTITY_CANVAS_PX,
            "identity_source_resampling": "none",
        }
    return contract


def reference_region_label(index: int, count: int) -> str:
    """Describe a subject's invisible horizontal print-safe region."""
    if count == 1:
        return "center"
    if count == 2:
        return ("left", "right")[index]
    if count == 3:
        return ("left", "center", "right")[index]
    return f"column {index + 1} of {count}"


def subject_prompt_notes(
    items: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> list[str]:
    """Return validated per-subject constraints in cast order."""
    specific_notes = []
    for item in items:
        name = item.get("name_en") or f"Pokemon #{item.get('pokemon_id', '?')}"
        notes = subject_conditioning(manifest, item).get("prompt_notes", [])
        if isinstance(notes, str):
            notes = [notes]
        if not isinstance(notes, list) or not all(
            isinstance(note, str) for note in notes
        ):
            raise ValueError(
                f"prompt_notes for Pokemon #{item.get('pokemon_id')} "
                "must be a string or list of strings"
            )
        if notes:
            specific_notes.append(
                f"{name}-specific constraints: {' '.join(notes)}"
            )
    return specific_notes


def build_spatial_identity_reference_prompt(
    items: list[dict[str, Any]],
    manifest: dict[str, Any],
    *,
    placement_contract: list[dict[str, int]],
) -> str:
    """Assign distinct spatial and identity roles to the joint references."""
    if not items:
        raise ValueError("Joint scene generation needs at least one cutout")
    if len(placement_contract) != len(items):
        raise ValueError(
            "Joint-scene placement contract must describe every subject"
        )

    regions = [
        reference_region_label(index, len(items))
        for index in range(len(items))
    ]
    region_summary = (
        regions[0]
        if len(regions) == 1
        else ", ".join(regions[:-1]) + f", or {regions[-1]}"
    )

    def percentage(value: int) -> str:
        if not isinstance(value, int) or not 0 <= value <= 1000:
            raise ValueError(
                "Joint-scene placement coordinates must be per-mille "
                "integers between 0 and 1000"
            )
        return f"{value / 10:.1f}%"

    coordinates = []
    identity_descriptions = []
    for index, (item, contract) in enumerate(
        zip(items, placement_contract, strict=True),
        start=2,
    ):
        if not isinstance(contract, dict):
            raise ValueError(
                "Joint-scene placement contract entries must be mappings"
            )
        name = item.get("name_en") or f"Pokemon #{item.get('pokemon_id', '?')}"
        identity_descriptions.append(
            f"IMAGE {index} is the exact identity and anatomy reference "
            f"for {name}."
        )
        coordinates.append(
            (
                f"{name}: x {percentage(contract['left_per_mille'])} to "
                f"{percentage(contract['right_per_mille'])}, y "
                f"{percentage(contract['top_per_mille'])} to "
                f"{percentage(contract['bottom_per_mille'])}"
            )
        )

    paragraphs = [
        (
            "IMAGE 1 is the sole spatial cast-layout reference. It contains exactly "
            f"{len(items)} complete characters on a flat neutral field, "
            f"ordered across the {region_summary} bottom-row regions. The "
            "reference is the authority only for character count, pose, "
            "orientation, relative scale, shared baseline, poster coordinates, "
            "and outer placement bounds. Its "
            "neutral field is empty reference space, not sky, terrain, a "
            "background plate, or a style request. Do not paste the "
            "characters as a foreground layer; redraw the complete scene "
            "and all character edges together from the empty target."
        ),
        (
            f"{' '.join(identity_descriptions)} Each identity image is the sole "
            "authority for that character's exact silhouette shape, stature, "
            "anatomy, facial features, colors, markings, appendages, and defining "
            "design details. Its centered position and scale on the neutral "
            "canvas carry no placement meaning and must not override IMAGE 1. "
            "These are detail views of the same cast already present in IMAGE 1, "
            "not additional subjects. Their neutral fields are empty reference "
            "space, not scenery."
        ),
        (
            "The following normalized target silhouette rectangles are the "
            "mandatory placement and scale contract: "
            f"{'; '.join(coordinates)}. Match every complete silhouette, "
            "baseline, and surrounding landscape clearance to these bounds "
            "within two percent of the full canvas. Each rectangle is a "
            "hard outer limit for every visible pixel of that character, "
            "including every outermost referenced detail and appendage; do "
            "not crop or extend any part beyond it. Render each character "
            f"exactly once in its assigned {region_summary} bottom-row "
            "region. No character may cross above the bottom row or an "
            "invisible vertical region division. The coordinates and "
            "divisions must never be drawn."
        ),
    ]
    specific_notes = subject_prompt_notes(items, manifest)
    if specific_notes:
        paragraphs.append(" ".join(specific_notes))
    return "\n\n".join(paragraphs)


def build_individual_spatial_reference_prompt(
    items: list[dict[str, Any]],
    manifest: dict[str, Any],
    *,
    placement_contract: list[dict[str, int]],
) -> str:
    """Assign one combined identity-and-position reference per subject."""
    if not items:
        raise ValueError(
            "Individual spatial joint generation needs at least one cutout"
        )
    if len(items) != len(placement_contract):
        raise ValueError(
            "Individual spatial placement contract must describe every subject"
        )

    def percentage(value: int) -> str:
        if not isinstance(value, int) or not 0 <= value <= 1000:
            raise ValueError(
                "Individual spatial coordinates must be per-mille integers "
                "between 0 and 1000"
            )
        return f"{value / 10:.1f}%"

    roles = []
    bounds = []
    for image_index, (item, contract) in enumerate(
        zip(items, placement_contract, strict=True),
        start=1,
    ):
        name = str(
            item.get("name_en")
            or f"Pokemon #{item.get('pokemon_id', '?')}"
        )
        roles.append(
            (
                f"IMAGE {image_index} is the sole poster-shaped identity and "
                f"position reference for {name}. It contains exactly one "
                f"complete {name} at the required final pose, orientation, "
                "scale, baseline, and poster position."
            )
        )
        bounds.append(
            (
                f"{name}: x {percentage(contract['left_per_mille'])} to "
                f"{percentage(contract['right_per_mille'])}, y "
                f"{percentage(contract['top_per_mille'])} to "
                f"{percentage(contract['bottom_per_mille'])}"
            )
        )

    paragraphs = [
        (
            f"The {len(items)} supplied poster-shaped images describe the "
            f"complete final cast. {' '.join(roles)} Across all images, render "
            f"exactly these {len(items)} characters once each."
        ),
        (
            "Each reference is authoritative only for its named character's "
            "exact identity, silhouette, stature, anatomy, face, colors, "
            "markings, appendages, pose, orientation, target scale, baseline, "
            "poster coordinates, and outer placement bounds. The flat neutral "
            "fields are empty coordinate space, not sky, terrain, separate "
            "pictures, panels, cards, or a background plate. Do not paste any "
            "reference as a foreground layer; redraw all scene and character "
            "edges together from the empty target."
        ),
        (
            "The mandatory normalized final silhouette bounds are "
            f"{'; '.join(bounds)}. Match every complete silhouette, baseline, "
            "and surrounding landscape clearance within two percent of the "
            "full canvas. Keep every appendage inside its named bounds. The "
            "coordinates and invisible regions must never be drawn."
        ),
    ]
    specific_notes = subject_prompt_notes(items, manifest)
    if specific_notes:
        paragraphs.append(" ".join(specific_notes))
    return "\n\n".join(paragraphs)


def build_landscape_first_individual_spatial_prompt(
    manifest: dict[str, Any],
    items: list[dict[str, Any]],
    *,
    placement_contract: list[dict[str, int]],
) -> str:
    """Build the reviewed two-subject landscape-first prompt profile."""
    if len(items) != 2 or len(placement_contract) != 2:
        raise ValueError(
            "landscape_first_v1 is reviewed for exactly two subjects"
        )
    layout_name = str(
        manifest.get("layout", {}).get("name", "standard_3x3")
    )
    if layout_name != "standard_3x3":
        raise ValueError(
            "landscape_first_v1 is reviewed only for standard_3x3"
        )

    names = [
        str(item.get("name_en") or f"Pokemon #{item.get('pokemon_id', '?')}")
        for item in items
    ]
    if names != ["Primal Kyogre", "Primal Groudon"]:
        raise ValueError(
            "landscape_first_v1 is reviewed only for Primal Kyogre and "
            "Primal Groudon"
        )
    centers = [
        (contract["left_per_mille"] + contract["right_per_mille"]) / 2
        for contract in placement_contract
    ]
    if not centers[0] < 500 < centers[1]:
        raise ValueError(
            "landscape_first_v1 needs ordered lower-left and lower-right subjects"
        )

    def percentage(value: int) -> str:
        if not isinstance(value, int) or not 0 <= value <= 1000:
            raise ValueError(
                "Landscape-first coordinates must be per-mille integers "
                "between 0 and 1000"
            )
        return f"{value / 10:.1f}%"

    bounds = "; ".join(
        (
            f"{name} x={percentage(contract['left_per_mille'])[:-1]}-"
            f"{percentage(contract['right_per_mille'])}, y="
            f"{percentage(contract['top_per_mille'])[:-1]}-"
            f"{percentage(contract['bottom_per_mille'])}"
        )
        for name, contract in zip(names, placement_contract, strict=True)
    )
    minimum_top = min(
        contract["top_per_mille"] for contract in placement_contract
    )
    upper_empty_percent = (minimum_top // 50) * 5
    highest_point_percent = minimum_top // 10
    areas = [
        (
            (contract["right_per_mille"] - contract["left_per_mille"])
            * (contract["bottom_per_mille"] - contract["top_per_mille"])
            / 10_000
        )
        for contract in placement_contract
    ]
    maximum_area_percent = math.ceil(max(areas))
    pokemon_free_percent = math.floor((100 - sum(areas)) / 5) * 5

    common_prefix = ""
    first_words = [name.split(maxsplit=1)[0] for name in names]
    if len(set(first_words)) == 1 and all(" " in name for name in names):
        common_prefix = f"{first_words[0]} "

    artwork = _mapping(manifest.get("artwork"), "artwork")
    scene = _mapping(artwork.get("scene"), "artwork.scene")
    setting = _text(scene.get("setting"), "artwork.scene.setting")
    rendering = _text(scene.get("rendering"), "artwork.scene.rendering")
    ground_noun = _text(
        scene.get("ground_noun"),
        "artwork.scene.ground_noun",
        default="ground",
    )
    compound_ground = ground_noun.replace(" ", "-")

    return "\n\n".join(
        (
            "COMPOSITION IS THE HIGHEST PRIORITY.",
            (
                "This is primarily a vast landscape artwork, not a character "
                "close-up or character poster. Both Pokemon must appear SMALL "
                "and LOW in the composition. Approximately the upper "
                f"{upper_empty_percent}% of the entire canvas contains NO "
                f"Pokemon. More than {pokemon_free_percent}% of the canvas "
                "remains Pokemon-free."
            ),
            (
                f"{names[0]} occupies only the extreme LOWER-LEFT edge of the "
                f"artwork. {names[1]} occupies only the extreme LOWER-RIGHT "
                "edge. Neither Pokemon may approach the vertical center. Their "
                "highest visible points remain below approximately "
                f"{highest_point_percent}% of total canvas height measured from "
                f"the top. Each Pokemon occupies less than "
                f"{maximum_area_percent}% of the total canvas area. Do not "
                "enlarge either Pokemon for facial readability, detail "
                "visibility, dramatic impact, symmetry, confrontation, or "
                "trading-card composition. Do not vertically center them, move "
                "them upward, make them fill their side, or create a "
                "conventional face-off composition."
            ),
            (
                "The visual hierarchy is: first, the vast ancient Hoenn "
                "environment and sky; second, enormous open atmospheric central "
                f"space; third, two small {common_prefix}Pokemon embedded near "
                "the bottom outer corners."
            ),
            (
                "Mandatory OUTER EXTENTS of the final silhouettes: "
                f"{bounds}. No part may extend outside its rectangle. Visible "
                "landscape remains beneath both Pokemon down to the bottom edge."
            ),
            (
                "IMAGE 1 is the sole identity, anatomy, pose, orientation, and "
                f"placement reference for {names[0]}. IMAGE 2 has the same role "
                f"for {names[1]}. Render exactly these two Pokemon once each. "
                "Preserve their referenced silhouette, anatomy, face, colors, "
                "markings, appendages, pose, and orientation. Permitted changes "
                "are limited to coherent scene lighting, reflected color, "
                "ground contact, and cast shadow. Never duplicate, merge, "
                "redesign, simplify, add, remove, enlarge, or reshape a "
                "referenced body part or marking."
            ),
            (
                "Generate one cohesive full-bleed image in a single unified "
                f"denoising pass. Invent {setting}. Monumental scale belongs to "
                f"the environment, never to the Pokemon. {rendering}"
            ),
            (
                f"Continue one low {compound_ground} ground plane through both "
                "subject regions. Keep tall grass, leaves, flowers, branches, "
                "rocks, spray, lava, and water edges outside the silhouette "
                "rectangles or clearly behind the Pokemon. Avoid "
                "landscape-character intersections without creating halos, "
                "platforms, paths, circles, landing pads, or character-shaped "
                "clearings. Keep the upper-center and middle-center cells open "
                "and low-detail. Do not draw extra creatures, people, text, "
                "letters, numbers, logos, boxes, panels, cards, borders, UI, "
                "watermarks, or crop marks."
            ),
        )
    )


def build_individual_spatial_joint_prompt(
    manifest: dict[str, Any],
    scope_data: dict[str, Any],
    items: list[dict[str, Any]],
    *,
    placement_contract: list[dict[str, int]],
    prefer_natural_separation: bool = True,
    avoid_foreground_intersections: bool = True,
) -> str:
    """Reuse the reviewed scene prompt with individual spatial references."""
    artwork = _mapping(manifest.get("artwork"), "artwork")
    prompt_profile = str(
        artwork.get("prompt_profile", "identity_first_v9")
    )
    if prompt_profile == "landscape_first_v1":
        return build_landscape_first_individual_spatial_prompt(
            manifest,
            items,
            placement_contract=placement_contract,
        )
    if prompt_profile != "identity_first_v9":
        raise ValueError(f"Unknown artwork.prompt_profile: {prompt_profile}")
    accepted_reference_prompt = build_spatial_identity_reference_prompt(
        items,
        manifest,
        placement_contract=placement_contract,
    )
    replacement_reference_prompt = build_individual_spatial_reference_prompt(
        items,
        manifest,
        placement_contract=placement_contract,
    )
    prompt = build_joint_scene_prompt(
        manifest,
        scope_data,
        items,
        placement_contract=placement_contract,
        prefer_natural_separation=prefer_natural_separation,
        avoid_foreground_intersections=avoid_foreground_intersections,
    )
    if accepted_reference_prompt not in prompt:
        raise RuntimeError("Accepted reference paragraph was not found")
    prompt = prompt.replace(
        accepted_reference_prompt,
        replacement_reference_prompt,
        1,
    )
    accepted_authority = (
        "IMAGE 1 is the strict authority for count, pose, orientation, "
        "target scale, baseline, and poster position. The corresponding "
        "individual identity image is the strict authority for each "
        "character's exact silhouette shape, stature, anatomy, facial "
        "features, colors, markings, and defining design details."
    )
    replacement_authority = (
        "The ordered individual poster-shaped references jointly control cast "
        "count. Each named reference controls only that character's pose, "
        "orientation, target scale, baseline, poster position, exact "
        "silhouette shape, stature, anatomy, facial features, colors, "
        "markings, and defining design details."
    )
    if accepted_authority not in prompt:
        raise RuntimeError("Accepted authority paragraph was not found")
    prompt = prompt.replace(
        accepted_authority,
        replacement_authority,
        1,
    )
    return prompt.replace(
        "that character's individual identity reference",
        "that character's named poster-shaped reference",
    )


def build_individual_spatial_joint_prompt_snapshot(
    manifest: dict[str, Any],
    scope_data: dict[str, Any],
    items: list[dict[str, Any]],
    *,
    placement_contract: list[dict[str, int]],
    prefer_natural_separation: bool = True,
    avoid_foreground_intersections: bool = True,
) -> str:
    """Return the exact individual-spatial prompt with its stable heading."""
    return format_individual_spatial_joint_prompt_snapshot(
        build_individual_spatial_joint_prompt(
            manifest,
            scope_data,
            items,
            placement_contract=placement_contract,
            prefer_natural_separation=prefer_natural_separation,
            avoid_foreground_intersections=avoid_foreground_intersections,
        )
    )


def format_individual_spatial_joint_prompt_snapshot(prompt: str) -> str:
    """Add the stable heading used by individual-spatial provenance."""
    return "\n\n".join(
        ("INDIVIDUAL SPATIAL JOINT - ISOLATED PREFLIGHT", prompt.strip())
    )
