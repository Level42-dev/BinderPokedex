import sys

import pytest

from scripts.fetcher.fetch import get_all_scopes
from scripts.poster_assets import run_comfyui_poster as poster_runner
from scripts.poster_assets.generation_contract import (
    validate_generation_contract,
    validate_promotable_generation_contract,
)
from scripts.poster_assets.generation_options import (
    DEFAULT_FLUX_ENCODER,
    DEFAULT_FLUX_MODE,
    DEFAULT_FLUX_MODEL,
    DEFAULT_FLUX_VAE,
    metadata_from_workflow_options,
    resolve_generation_options,
)


def test_me05_is_a_release_scope():
    assert "ME05" in get_all_scopes()


def test_matching_flux_manifest_drives_workflow_and_canonical_metadata():
    configured = {
        "engine": "flux",
        "model": "manifest-model.safetensors",
        "model_sha256": "a" * 64,
        "encoder": "manifest-encoder.safetensors",
        "vae": "manifest-vae.safetensors",
        "mode": "identity_lock",
        "reference_mode": "two_pass_source_pixels",
        "steps": "7",
        "seed": 123,
        "generation_megapixels": 1.0,
    }

    resolved = resolve_generation_options("flux", configured)

    assert resolved.workflow_options == {
        "flux_model": "manifest-model.safetensors",
        "flux_clip": "manifest-encoder.safetensors",
        "flux_vae": "manifest-vae.safetensors",
        "flux_mode": "identity_lock",
        "flux_reference_mode": "two_pass_source_pixels",
        "flux_steps": 7,
    }
    assert resolved.metadata == {
        "engine": "flux",
        "model": "manifest-model.safetensors",
        "encoder": "manifest-encoder.safetensors",
        "vae": "manifest-vae.safetensors",
        "mode": "identity_lock",
        "steps": 7,
        "reference_mode": "two_pass_source_pixels",
    }


def test_joint_scene_is_the_code_default():
    resolved = resolve_generation_options()

    assert DEFAULT_FLUX_MODE == "joint_scene"
    assert resolved.metadata == {
        "engine": "flux",
        "model": DEFAULT_FLUX_MODEL,
        "encoder": DEFAULT_FLUX_ENCODER,
        "vae": DEFAULT_FLUX_VAE,
        "mode": "joint_scene",
        "steps": 4,
        "reference_mode": "individual_spatial_joint",
    }


def test_mode_override_switches_the_whole_reference_contract():
    resolved = resolve_generation_options(
        "flux",
        {
            "engine": "flux",
            "mode": "joint_scene",
            "reference_mode": "spatial_identity_joint",
        },
        {"flux_mode": "identity_lock"},
    )

    assert resolved.workflow_options["flux_mode"] == "identity_lock"
    assert resolved.metadata["reference_mode"] == "two_pass_source_pixels"


def test_regional_joint_scene_reference_mode_is_selectable():
    resolved = resolve_generation_options(
        "flux",
        {
            "engine": "flux",
            "mode": "joint_scene",
            "reference_mode": "regional_identity_joint",
        },
    )

    assert (
        resolved.workflow_options["flux_reference_mode"]
        == "regional_identity_joint"
    )
    assert resolved.metadata["reference_mode"] == "regional_identity_joint"


def test_individual_spatial_joint_reference_mode_is_selectable():
    resolved = resolve_generation_options(
        "flux",
        {
            "engine": "flux",
            "mode": "joint_scene",
            "reference_mode": "individual_spatial_joint",
        },
    )

    assert (
        resolved.workflow_options["flux_reference_mode"]
        == "individual_spatial_joint"
    )
    assert resolved.metadata["reference_mode"] == "individual_spatial_joint"


def test_reference_mode_override_can_select_regional_joint_scene():
    resolved = resolve_generation_options(
        "flux",
        {
            "engine": "flux",
            "mode": "joint_scene",
            "reference_mode": "spatial_identity_joint",
        },
        {"flux_reference_mode": "regional_identity_joint"},
    )

    assert resolved.metadata["reference_mode"] == "regional_identity_joint"


def test_manifest_rejects_wrong_canonical_reference_mode():
    with pytest.raises(ValueError, match="reference_mode is incompatible"):
        resolve_generation_options(
            "flux",
            {
                "engine": "flux",
                "mode": "joint_scene",
                "reference_mode": "identity",
            },
        )


@pytest.mark.parametrize("mode", ("edit", "inpaint", "generate"))
def test_removed_flux_modes_fail_closed(mode):
    with pytest.raises(ValueError, match="flux.mode must be one of"):
        resolve_generation_options(
            "flux",
            {"engine": "flux", "mode": mode},
        )


@pytest.mark.parametrize("engine", ("anima", "flux1_canny", "qwen_edit"))
def test_removed_engines_fail_closed(engine):
    with pytest.raises(ValueError, match="only 'flux' is supported"):
        resolve_generation_options(engine)


def test_metadata_is_rebuilt_from_exact_workflow_options():
    resolved = resolve_generation_options(
        "flux",
        None,
        {
            "flux_model": "model.safetensors",
            "flux_clip": "encoder.safetensors",
            "flux_vae": "vae.safetensors",
            "flux_mode": "identity_lock",
            "flux_steps": 6,
        },
    )

    assert (
        metadata_from_workflow_options(
            "flux",
            resolved.workflow_options,
        )
        == resolved.metadata
    )


def test_metadata_rebuild_rejects_partial_workflow_options():
    options = resolve_generation_options().workflow_options
    with pytest.raises(ValueError, match="missing: flux_vae"):
        metadata_from_workflow_options(
            "flux",
            {key: value for key, value in options.items() if key != "flux_vae"},
        )


def test_joint_scene_contract_rejects_a_learned_upscaler():
    with pytest.raises(ValueError, match="learned upscaler"):
        validate_generation_contract(
            {
                "engine": "flux",
                "mode": "joint_scene",
                "reference_mode": "spatial_identity_joint",
                "output_method": "lanczos",
                "output_dpi": 300,
                "upscale_model": "learned.pth",
            }
        )


def test_identity_lock_promotion_requires_300dpi_model_upscale():
    generation = {
        "engine": "flux",
        "mode": "identity_lock",
        "reference_mode": "two_pass_source_pixels",
        "output_method": "model_upscale",
        "output_dpi": 300,
        "upscale_model": "anime-upscaler.pth",
        "upscale_model_sha256": "a" * 64,
    }

    validate_promotable_generation_contract(generation)

    with pytest.raises(ValueError, match="model_upscale"):
        validate_promotable_generation_contract(
            {
                **generation,
                "output_method": "lanczos",
            }
        )
    with pytest.raises(ValueError, match="upscale_model_sha256"):
        without_hash = dict(generation)
        without_hash.pop("upscale_model_sha256")
        validate_promotable_generation_contract(without_hash)


def _capture_cli_run(monkeypatch, tmp_path, configured, argv):
    captured = {}

    def fake_run(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return (
            tmp_path / "raw.png",
            tmp_path / "artwork.png",
            tmp_path / "final.png",
            tmp_path / "run.json",
        )

    monkeypatch.setattr(
        poster_runner,
        "configured_generation",
        lambda _scope: configured,
    )
    monkeypatch.setattr(poster_runner, "run", fake_run)
    monkeypatch.setattr(sys, "argv", argv)
    assert poster_runner.main() == 0
    return captured


def test_joint_scene_cli_defaults_to_lanczos_300dpi(monkeypatch, tmp_path):
    configured = {
        "engine": "flux",
        "model": "model.safetensors",
        "encoder": "encoder.safetensors",
        "vae": "vae.safetensors",
        "mode": "joint_scene",
        "reference_mode": "spatial_identity_joint",
        "steps": 4,
        "seed": 123,
        "generation_megapixels": 1.0,
        "output_method": "lanczos",
        "output_dpi": 300,
    }

    captured = _capture_cli_run(
        monkeypatch,
        tmp_path,
        configured,
        ["run_comfyui_poster.py", "--scope", "Example"],
    )

    assert captured["kwargs"]["flux_mode"] == "joint_scene"
    assert (
        captured["kwargs"]["flux_reference_mode"]
        == "spatial_identity_joint"
    )
    assert captured["kwargs"]["output_dpi"] == 300
    assert captured["kwargs"]["output_megapixels"] is None


def test_cli_can_select_regional_joint_scene(monkeypatch, tmp_path):
    configured = {
        "engine": "flux",
        "model": "model.safetensors",
        "encoder": "encoder.safetensors",
        "vae": "vae.safetensors",
        "mode": "joint_scene",
        "reference_mode": "spatial_identity_joint",
        "steps": 4,
        "seed": 123,
        "generation_megapixels": 1.0,
        "output_method": "lanczos",
        "output_dpi": 300,
    }

    captured = _capture_cli_run(
        monkeypatch,
        tmp_path,
        configured,
        [
            "run_comfyui_poster.py",
            "--scope",
            "Example",
            "--flux-reference-mode",
            "regional_identity_joint",
        ],
    )

    assert captured["kwargs"]["flux_mode"] == "joint_scene"
    assert (
        captured["kwargs"]["flux_reference_mode"]
        == "regional_identity_joint"
    )


def test_identity_lock_override_gets_model_upscale_300dpi_default(
    monkeypatch,
    tmp_path,
):
    configured = {
        "engine": "flux",
        "model": "model.safetensors",
        "encoder": "encoder.safetensors",
        "vae": "vae.safetensors",
        "mode": "joint_scene",
        "reference_mode": "spatial_identity_joint",
        "steps": 4,
        "seed": 123,
        "generation_megapixels": 1.0,
        "output_method": "lanczos",
        "output_dpi": 300,
    }

    captured = _capture_cli_run(
        monkeypatch,
        tmp_path,
        configured,
        [
            "run_comfyui_poster.py",
            "--scope",
            "Example",
            "--flux-mode",
            "identity_lock",
        ],
    )

    assert captured["kwargs"]["flux_mode"] == "identity_lock"
    assert captured["kwargs"]["output_dpi"] == 300
    assert captured["kwargs"]["output_megapixels"] is None


def test_explicit_preview_output_is_preserved():
    dpi, megapixels = poster_runner.resolve_output_target(
        {"mode": "joint_scene"},
        "identity_lock",
        output_dpi=None,
        output_megapixels=0.25,
    )

    assert dpi is None
    assert megapixels == 0.25


def test_non_mapping_inputs_are_rejected():
    with pytest.raises(TypeError, match="configured_generation"):
        resolve_generation_options("flux", configured_generation=[])
    with pytest.raises(TypeError, match="overrides"):
        resolve_generation_options("flux", overrides=[])
    with pytest.raises(TypeError, match="workflow_options"):
        metadata_from_workflow_options("flux", [])
