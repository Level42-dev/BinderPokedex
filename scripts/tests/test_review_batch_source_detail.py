"""Trial manifests bind every requested character to the exact cached source."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import yaml

from scripts.poster_assets.review_batch_source_detail import (
    build_trial_manifest,
    trial_manifest_bundle,
)
from scripts.poster_assets.run_comfyui_poster import configured_generation


class ReviewBatchSourceDetailTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.scope = "Fixture"
        config = self.root / "config/posters/Fixture/poster.yaml"
        config.parent.mkdir(parents=True)
        config.write_text(yaml.safe_dump({
            "asset_key": "Fixture", "scope": "Fixture", "layout": {"name": "standard_3x3"},
            "artwork": {"generation": {
                "mode": "joint_scene", "reference_mode": "individual_spatial_joint",
                "seed": 12, "steps": 4, "generation_megapixels": 1.0,
                "output_dpi": 300, "output_method": "lanczos",
            }},
        }), encoding="utf-8")
        self.config = config
        cutouts = self.root / "tmp/poster-workspaces/Fixture/sources/cutouts"
        cutouts.mkdir(parents=True)
        self.items = [
            {"pokemon_id": 1, "name_en": "Bulbasaur", "file": "first.png"},
            {"pokemon_id": 4, "name_en": "Charmander", "file": "second.png"},
        ]
        for item, data in zip(self.items, (b"first-source", b"second-source"), strict=True):
            (cutouts / item["file"]).write_bytes(data)
        (cutouts / "manifest.json").write_text(json.dumps({"items": self.items}), encoding="utf-8")
        reports = []
        for item in self.items:
            path = cutouts / item["file"]
            reports.append({"source": {
                "file": path.relative_to(self.root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }})
        self.retriage = self.root / "docs/reviews/retriage.json"
        self.retriage.parent.mkdir(parents=True)
        self.retriage.write_text(json.dumps({"targets": [{
            "review_id": "P99", "asset_key": "Fixture", "subjects": reports,
        }]}), encoding="utf-8")
        self.traits = self.root / "docs/reviews/traits.yaml"
        self.traits.write_text(yaml.safe_dump({
            "schema_version": 1,
            "scopes": {"P99": "Fixture"},
            "traits": {
                "pokeapi:official-artwork:1": "Keep the bulb and four short legs.",
                "pokeapi:official-artwork:4": "Keep the tail flame and pale belly.",
            },
        }), encoding="utf-8")

    def build(self, *, variant="p99-review-1"):
        return build_trial_manifest(
            self.scope, variant, 42, repository_root=self.root,
            traits_path=self.traits, retriage_path=self.retriage,
        )

    def test_builds_source_bound_overlay_without_touching_production_manifest(self):
        before = self.config.read_bytes()
        output = self.build()
        self.assertEqual(output, (self.root / "tmp/review-batch-manifests/p99-review-1/poster.yaml").resolve())
        self.assertEqual(self.config.read_bytes(), before)
        manifest = yaml.safe_load(output.read_text())
        details = manifest["artwork"]["source_details"]
        self.assertEqual(set(details), {
            "pokeapi:official-artwork:1", "pokeapi:official-artwork:4",
        })
        first = self.root / "tmp/poster-workspaces/Fixture/sources/cutouts/first.png"
        self.assertEqual(details["pokeapi:official-artwork:1"]["sha256"], hashlib.sha256(first.read_bytes()).hexdigest())
        self.assertEqual(manifest["artwork"]["generation"]["reference_mode"], "spatial_source_detail_joint")
        self.assertEqual(manifest["artwork"]["generation"]["generation_megapixels"], 2.0)
        self.assertEqual(manifest["artwork"]["generation"]["seed"], 42)
        with trial_manifest_bundle(self.scope, output, repository_root=self.root):
            self.assertEqual(configured_generation(self.scope)["seed"], 42)

    def test_rejects_source_that_changed_since_hash_bound_retriage(self):
        path = self.root / "tmp/poster-workspaces/Fixture/sources/cutouts/first.png"
        path.write_bytes(b"changed-source")
        with self.assertRaisesRegex(ValueError, "source hash"):
            self.build()
        self.assertFalse((self.root / "tmp/review-batch-manifests/p99-review-1/poster.yaml").exists())

    def test_rejects_missing_trait_and_unlisted_scope(self):
        data = yaml.safe_load(self.traits.read_text())
        data["traits"].pop("pokeapi:official-artwork:4")
        self.traits.write_text(yaml.safe_dump(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "trait"):
            self.build()
        with self.assertRaisesRegex(ValueError, "not listed"):
            build_trial_manifest(
                "Unknown", "unknown-review-1", 42, repository_root=self.root,
                traits_path=self.traits, retriage_path=self.retriage,
            )

    def test_rejects_unsafe_variant_and_refuses_overwrite(self):
        with self.assertRaisesRegex(ValueError, "variant"):
            self.build(variant="../escape")
        output = self.build()
        with self.assertRaisesRegex(FileExistsError, "exists"):
            self.build()
        self.assertTrue(output.is_file())


if __name__ == "__main__":
    unittest.main()
