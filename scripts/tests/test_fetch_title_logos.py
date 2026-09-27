from types import SimpleNamespace

from PIL import Image, ImageChops

from scripts.poster_assets import fetch_title_logos as title_logos
from scripts.poster_assets.finalize_comfyui_poster import title_logo_file
from scripts.poster_assets.poster_io import load_poster_scope_data, poster_bundle


def test_title_logo_fetch_copies_repository_local_source(tmp_path, monkeypatch):
    source = tmp_path / "images" / "logos" / "promo" / "default.png"
    source.parent.mkdir(parents=True)
    Image.new("RGBA", (64, 32), (255, 204, 0, 255)).save(source)

    asset_dir = tmp_path / "poster"
    source_dir = tmp_path / "poster-workspace" / "sources"
    bundle = SimpleNamespace(
        asset_dir=asset_dir,
        source_dir=source_dir,
        manifest_path=asset_dir / "poster.yaml",
        manifest={
            "title_logo": {"files": {"de": "logos/logo-de.png"}}
        },
    )
    monkeypatch.setattr(title_logos, "ROOT", tmp_path)
    monkeypatch.setattr(title_logos, "POSTER_ASSETS", tmp_path)
    monkeypatch.setattr(
        title_logos,
        "poster_bundle",
        lambda *_args, **_kwargs: bundle,
    )
    monkeypatch.setattr(
        title_logos,
        "load_poster_scope_data",
        lambda *_args, **_kwargs: {
            "logo_urls": {"de": "images/logos/promo/default.png"}
        },
    )

    written = title_logos.fetch_title_logos("SVP")

    assert written == [source_dir / "logos" / "logo-de.png"]
    with Image.open(written[0]) as copied, Image.open(source) as original:
        assert copied.mode == "RGBA"
        assert copied.size == original.size
        assert ImageChops.difference(copied, original).getbbox() is None


def test_base2_german_title_resolves_a_real_set_logo():
    bundle = poster_bundle("Base2")
    scope_data = load_poster_scope_data(bundle)

    assert title_logo_file(bundle.manifest, "de") == "logos/logo-de.png"
    assert (
        "de",
        "logos/logo-de.png",
        "https://assets.tcgdex.net/fr/base/base2/logo.png",
    ) in title_logos.resolve_logo_downloads(bundle.manifest, scope_data)
