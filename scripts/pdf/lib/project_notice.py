"""Provenance for generated PDFs; the program itself remains MIT licensed."""

import os
import re
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph

try:
    from .constants import CARD_HEIGHT, CARD_WIDTH, PAGE_HEIGHT, PAGE_WIDTH
except ImportError:
    from constants import CARD_HEIGHT, CARD_WIDTH, PAGE_HEIGHT, PAGE_WIDTH


PROJECT_URL = "https://github.com/Level42-dev/BinderPokedex"
LICENSE_URL = "https://creativecommons.org/licenses/by-nc/4.0/"
FOOTER_TEXT = "BinderPokedex | github.com/Level42-dev/BinderPokedex | Notices: final page"


def build_identity() -> tuple[str, str]:
    """Use explicit build labels; never mislabel a local build as a release."""
    version = os.environ.get("BINDER_POKEDEX_BUILD_VERSION", "local / unversioned")
    source_ref = os.environ.get("BINDER_POKEDEX_BUILD_REF", "")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", source_ref):
        source_ref = "not recorded"
    return version, source_ref


def set_document_provenance(canvas_obj, title: str) -> None:
    version, source_ref = build_identity()
    canvas_obj.setTitle(title)
    canvas_obj.setCreator(f"BinderPokedex ({version})")
    canvas_obj.setSubject(
        f"Source: {PROJECT_URL}; build: {version}; commit: {source_ref}. "
        "See final page for attribution, license scope and third-party exclusions."
    )


def _paragraph(canvas_obj, text, x, top, width, size=9, leading=13):
    style = ParagraphStyle(
        "notice", fontName="Helvetica", fontSize=size, leading=leading,
        textColor=HexColor("#263442"), spaceAfter=0,
    )
    paragraph = Paragraph(text, style)
    _, height = paragraph.wrap(width, PAGE_HEIGHT)
    paragraph.drawOn(canvas_obj, x, top - height)
    return top - height


def append_project_notice(canvas_obj, language: str) -> None:
    """Append one A4 page with a cuttable provenance card and scoped notices.

    The notice identifies project contributions where copyright exists. It
    does not license third-party art, unprotectable output or custom templates.
    """
    version, source_ref = build_identity()
    german = language == "de"
    canvas_obj.saveState()
    canvas_obj.setFillColor(HexColor("#FFFFFF"))
    canvas_obj.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    x = 18 * mm
    top = PAGE_HEIGHT - 20 * mm
    _paragraph(
        canvas_obj,
        "<b>Herkunft &amp; Nutzungshinweise</b>" if german else "<b>Source &amp; usage notes</b>",
        x, top, PAGE_WIDTH - 2 * x, 21, 26,
    )
    _paragraph(
        canvas_obj,
        "Infokarte ausschneiden und zum Binder legen. Bei 100 % drucken."
        if german else "Cut out the information card and keep it with your binder. Print at 100%.",
        x, top - 34, PAGE_WIDTH - 2 * x, 9, 13,
    )

    card_top = top - 62
    canvas_obj.setStrokeColor(HexColor("#78909C"))
    canvas_obj.setDash(3, 3)
    canvas_obj.rect(x, card_top - CARD_HEIGHT, CARD_WIDTH, CARD_HEIGHT, fill=0, stroke=1)
    canvas_obj.setDash()
    card_x = x + 4 * mm
    card_width = CARD_WIDTH - 8 * mm
    cursor = _paragraph(canvas_obj, "<b>BinderPokedex</b>", card_x, card_top - 5 * mm, card_width, 14, 17)
    card_blocks = [
        "Project design / Projektgestaltung:<br/>Björn Teichmann / BinderPokedex<br/>BinderPokedex Contributors",
        "github.com/Level42-dev/BinderPokedex",
        "Marked, protected project design:<br/><b>CC BY-NC 4.0</b><br/>creativecommons.org/licenses/by-nc/4.0/",
        "Pokémon and other third-party material excluded. No endorsement.",
        "Keep credits; identify changes.<br/>As-is, without warranties (CC section 5).<br/>Details: LICENSE-CONTENT.md / NOTICE.md",
        f"Build: {escape(version[:48])}<br/>Source: {escape(source_ref[:12])}",
    ]
    for block in card_blocks:
        cursor = _paragraph(canvas_obj, block, card_x, cursor - 9, card_width, 7, 9)
    if cursor < card_top - CARD_HEIGHT + 3 * mm:
        raise ValueError("Project information card text exceeds its printable area")

    aside_x = x + CARD_WIDTH + 12 * mm
    aside_width = PAGE_WIDTH - aside_x - x
    text = (
        "<b>Was die Kennzeichnung bedeutet</b><br/><br/>"
        "Sie betrifft nur gekennzeichnete, eigene und urheberrechtlich geschützte "
        "Gestaltungsbeiträge des Projekts. Sie beansprucht keine Rechte an Pokémon, "
        "fremden Bildern, Marken, Fakten oder ungeschützten automatisierten Ergebnissen."
        "<br/><br/>Der Programmcode steht unter MIT. Seine Lizenz gilt nicht automatisch "
        "für sämtliche Inhalte einer erzeugten PDF."
        if german else
        "<b>What this notice covers</b><br/><br/>"
        "Only marked, original and copyright-protected project design contributions "
        "are covered. This claims no rights in Pokémon, third-party images, trademarks, "
        "facts or unprotected automated output."
        "<br/><br/>The program code is MIT licensed. Its license does not automatically "
        "apply to every element of a generated PDF."
    )
    _paragraph(canvas_obj, text, aside_x, card_top - 5 * mm, aside_width)

    cursor = card_top - CARD_HEIGHT - 16 * mm
    blocks = [
        f'<b>Project / Quelle:</b> <link href="{PROJECT_URL}">{PROJECT_URL}</link>',
        f"<b>Build:</b> {escape(version)}<br/><b>Source commit:</b> {escape(source_ref)}",
        "<b>Design attribution:</b> Björn Teichmann / BinderPokedex; BinderPokedex Contributors. "
        "The original project layout contributions reproduced here are designated "
        "under CC BY-NC 4.0 only to the extent the licensor controls protectable rights. "
        "Retain attribution and license notices and "
        "identify modifications when sharing. This license does not authorize "
        "commercial distribution of the covered design contributions.",
        f'<b>License:</b> <link href="{LICENSE_URL}">{LICENSE_URL}</link><br/>'
        f'Scope and disclaimers: {PROJECT_URL}/blob/main/LICENSE-CONTENT.md',
        "<b>Third-party material:</b> Pokémon names, artwork and trademarks belong "
        "to their respective rights holders, including Nintendo, Creatures Inc. and "
        "GAME FREAK inc. No rights to that material are granted here. No affiliation "
        "or endorsement is implied. Custom or separately licensed content retains "
        "its own terms. No warranty is provided, as set out in the applicable licenses.",
        "Previously valid license grants remain unaffected. Statutory exceptions "
        "and uses not requiring permission remain available. Full notices and the "
        "license text accompany current release ZIPs (NOTICE.md, LICENSE-CONTENT.md, "
        "LICENSE-CODE and LICENSES/CC-BY-NC-4.0.txt).",
    ]
    for block in blocks:
        cursor = _paragraph(canvas_obj, block, x, cursor, PAGE_WIDTH - 2 * x, 8.5, 11.5) - 9
    if cursor < 15 * mm:
        raise ValueError("Project notice text exceeds its printable page")
    canvas_obj.restoreState()
    canvas_obj.showPage()
