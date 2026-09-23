"""The P16 fallback prepares one sealed trial, never a production poster."""
from __future__ import annotations

import json

import pytest

from scripts.poster_assets.poster_subject import PosterSubject
from scripts.poster_assets.region_joint.geometry import build_p16_region_contract
from scripts.poster_assets.region_joint.prepare_p16_trial import (
    PILOT_VARIANT,
    pin_trial_b_scales,
    build_p16_prompts,
    build_p16_workflow,
    prepare_p16_trial,
)


def test_p16_graph_has_one_sampler_decode_and_subject_isolated_references():
    graph = build_p16_workflow(
        "empty coastal landscape", ("left source", "right source"),
        build_p16_region_contract(),
    )
    classes = [node["class_type"] for node in graph.values()]
    assert classes.count("SamplerCustomAdvanced") == 1
    assert classes.count("VAEDecode") == 1
    assert classes.count("EmptyFlux2LatentImage") == 1
    assert classes.count("RegionConstrainedJointGuider") == 1
    assert classes.count("ReferenceLatent") == 4
    assert not ({"ConditioningSetMask", "ImageCompositeMasked", "VAEEncodeForInpaint"} & set(classes))
    assert graph["6"]["inputs"]["width"] == 1200
    assert graph["6"]["inputs"]["height"] == 1664
    assert graph["70"]["inputs"]["global_conditioning"] == ["4", 0]
    assert graph["70"]["inputs"]["left_conditioning"] == ["36", 0]
    assert graph["70"]["inputs"]["right_conditioning"] == ["46", 0]
    assert json.loads(graph["70"]["inputs"]["region_contract"]) == build_p16_region_contract()

    assert graph["31"]["inputs"]["image"] == "individual_spatial_reference_1.png"
    assert graph["34"]["inputs"]["image"] == "identity_reference_1.png"
    assert graph["41"]["inputs"]["image"] == "individual_spatial_reference_2.png"
    assert graph["44"]["inputs"]["image"] == "identity_reference_2.png"
    assert graph["33"]["inputs"]["conditioning"] == ["20", 0]
    assert graph["36"]["inputs"]["conditioning"] == ["33", 0]
    assert graph["43"]["inputs"]["conditioning"] == ["30", 0]
    assert graph["46"]["inputs"]["conditioning"] == ["43", 0]


def test_global_graph_prompt_must_remain_species_free():
    with pytest.raises(ValueError, match="landscape-only"):
        build_p16_workflow(
            "Primal Kyogre over a coast", ("left", "right"),
            build_p16_region_contract(),
        )


def test_p16_prompt_bindings_use_position_first_and_own_source_details_only():
    manifest = {
        "asset_key": "ExGen2/sections/primal",
        "layout": {"name": "standard_3x3"},
        "artwork": {
            "scene": {
                "concept": "ancient ocean and land conflict",
                "setting": "a broad volcanic coast",
                "lighting": "cold ocean light meets warm rock light",
                "rendering": "crisp cel-painted linework",
                "ground_noun": "coastal stone",
                "constraints": [],
            },
            "source_details": {
                "pokeapi:official-artwork:10077": {"sha256": "a" * 64, "traits": "Keep separated rear fins."},
                "pokeapi:official-artwork:10078": {"sha256": "b" * 64, "traits": "Keep two clawed feet."},
            },
        },
    }
    items = [
        {"pokemon_id": 382, "name_en": "Primal Kyogre", "poster_subject": PosterSubject(382, 10077).as_mapping()},
        {"pokemon_id": 383, "name_en": "Primal Groudon", "poster_subject": PosterSubject(383, 10078).as_mapping()},
    ]
    placement = [
        {"left_per_mille": 40, "right_per_mille": 290, "top_per_mille": 730, "bottom_per_mille": 965},
        {"left_per_mille": 710, "right_per_mille": 960, "top_per_mille": 730, "bottom_per_mille": 965},
    ]
    global_prompt, locals_ = build_p16_prompts(manifest, {}, items, placement)
    assert "Primal Kyogre" not in global_prompt
    assert "Primal Groudon" not in global_prompt
    assert "no creatures" in global_prompt
    assert "IMAGE 1" in locals_[0] and "position" in locals_[0]
    assert "IMAGE 2" in locals_[0] and "detail" in locals_[0]
    assert "Keep separated rear fins." in locals_[0]
    assert "Keep two clawed feet." not in locals_[0]
    assert "Keep two clawed feet." in locals_[1]
    assert "Keep separated rear fins." not in locals_[1]


def test_p16_trial_refuses_existing_variant_without_overwriting(tmp_path):
    existing = tmp_path / "tmp/oneshot-trials" / PILOT_VARIANT
    existing.mkdir(parents=True)
    marker = existing / "owner.txt"
    marker.write_text("untouched", encoding="utf-8")
    with pytest.raises(FileExistsError, match="already exists"):
        prepare_p16_trial(PILOT_VARIANT, tmp_path)
    assert marker.read_text(encoding="utf-8") == "untouched"


def test_p16_trial_refuses_missing_evidence_before_creating_files(tmp_path):
    with pytest.raises(FileNotFoundError):
        prepare_p16_trial(PILOT_VARIANT, tmp_path)
    assert not (tmp_path / "tmp/oneshot-trials" / PILOT_VARIANT).exists()


def test_p16_trial_refuses_any_other_variant(tmp_path):
    with pytest.raises(ValueError, match="single approved P16"):
        prepare_p16_trial("p37-region-20260923-a", tmp_path)


def test_p16_trial_inherits_only_missing_trial_b_scales():
    fresh = {"artwork": {"scene": {"concept": "coast"}}}
    baseline = {"artwork": {"spatial_reference_scales": {
        "pokeapi:official-artwork:10077": 0.55,
        "pokeapi:official-artwork:10078": 0.55,
    }}}
    pin_trial_b_scales(fresh, baseline)
    assert fresh["artwork"]["spatial_reference_scales"] == baseline["artwork"]["spatial_reference_scales"]
    assert fresh["artwork"]["scene"] == {"concept": "coast"}


def test_p16_trial_rejects_conflicting_existing_scale():
    fresh = {"artwork": {"spatial_reference_scales": {"pokeapi:official-artwork:10077": 0.7}}}
    baseline = {"artwork": {"spatial_reference_scales": {
        "pokeapi:official-artwork:10077": 0.55,
        "pokeapi:official-artwork:10078": 0.55,
    }}}
    with pytest.raises(ValueError, match="scale drift"):
        pin_trial_b_scales(fresh, baseline)
