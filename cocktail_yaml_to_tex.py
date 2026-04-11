"""Generate recipe-card TeX from cocktail YAML documents.

Usage:
    bazel run //people/mav/recipes:cocktail_yaml_to_tex -- path/to/file.yaml

The output path is derived from the input path by replacing `.yaml`/`.yml`
with `.tex`.
"""

from __future__ import annotations

import argparse
import html
import os
from pathlib import Path
import re
from typing import Any, Iterable

from jsonschema import Draft202012Validator
import yaml


SCHEMA_FILE_NAME = "cocktail.schema.yaml"
RECIPES_SITE_BASE_URL = "https://poly-repo.github.io/recipes"
BACK_PAGE_QR_HEIGHT = "0.72in"

BASE_SPIRIT_MAP: dict[str, str] = {
    "gin": "Gin",
    "whiskey": "Whiskey",
    "whisky": "Whiskey",
    "rum": "Rum",
    "vodka": "Vodka",
    "tequila": "Tequila",
}

GLASS_CANONICAL_MAP: dict[str, str] = {
    # Canonical recipe-card.cls glass keys.
    "champagneflute": "Champagne Flute",
    "collins": "Collins",
    "collinsglass": "Collins",
    "coupe": "Coupe",
    "coupeglass": "Coupe",
    "highball": "Highball",
    "highballglass": "Highball",
    "hurricane": "Hurricane",
    "hurricaneglass": "Hurricane",
    "martini": "Martini",
    "martiniglass": "Martini",
    "nickandnora": "Nick and Nora",
    "nickandnoraglass": "Nick and Nora",
    "rocks": "Rocks",
    "rockglass": "Rocks",
    "oldfashioned": "Old Fashioned",
    "tikimug": "Tiki Mug",
    "tiki": "Tiki Mug",
    "wine": "Wine",
    "wineglass": "Wine",
    # Practical aliases.
    "rock": "Rocks",
    "rocksglass": "Rocks",
    "oldfashionedglass": "Old Fashioned",
}

METHOD_CANONICAL_MAP: dict[str, str] = {
    # Canonical recipe-card.cls method keys.
    "blend": "Blend",
    "blended": "Blend",
    "build": "Build",
    "built": "Build",
    "flame": "Flame",
    "flamed": "Flame",
    "float": "Float",
    "floated": "Float",
    "layer": "Layer",
    "layered": "Layer",
    "muddle": "Muddle",
    "muddled": "Muddle",
    "reversedryshake": "Reverse Dry Shake",
    "shake": "Shake",
    "shaken": "Shake",
    "stir": "Stir",
    "stirred": "Stir",
    # Practical aliases.
    "blending": "Blend",
    "building": "Build",
    "flaming": "Flame",
    "floating": "Float",
    "layering": "Layer",
    "muddling": "Muddle",
    "shaking": "Shake",
    "stirring": "Stir",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("yaml_path", type=Path, help="Input cocktail YAML file.")
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Write one Markdown file per cocktail document instead of TeX output.",
    )
    return parser.parse_args()


def _normalize_key(value: Any) -> str:
    return str(value).strip().lower().replace("_", " ")


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _escape_latex(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    escaped = text
    for source, target in replacements.items():
        escaped = escaped.replace(source, target)
    return escaped


def _normalize_recipe_card_key(value: Any) -> str:
    return (
        _to_text(value)
        .lower()
        .replace("&", "and")
        .replace("~", "")
        .replace("-", "")
        .replace("_", "")
        .replace(" ", "")
    )


def _resolve_schema_path() -> Path:
    candidate_paths = [Path(__file__).resolve().with_name(SCHEMA_FILE_NAME)]
    workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace_dir:
        candidate_paths.append(Path(workspace_dir) / "people/mav/recipes" / SCHEMA_FILE_NAME)
    for candidate in candidate_paths:
        if candidate.exists():
            return candidate
    searched = ", ".join(str(path) for path in candidate_paths)
    raise FileNotFoundError(
        f"Unable to locate {SCHEMA_FILE_NAME}; searched: {searched}"
    )


def _load_schema(path: Path) -> dict[str, Any]:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"Schema at {path} must be a YAML mapping/object.")
    return parsed


def _json_path(path_segments: Iterable[Any]) -> str:
    path = "$"
    for segment in path_segments:
        if isinstance(segment, int):
            path += f"[{segment}]"
        else:
            path += f".{segment}"
    return path


def _validate_against_schema(
    cocktails: list[dict[str, Any]],
    *,
    schema: dict[str, Any],
) -> None:
    validator = Draft202012Validator(schema)
    for index, doc in enumerate(cocktails, start=1):
        errors = sorted(
            validator.iter_errors(doc),
            key=lambda error: (_json_path(error.absolute_path), error.message),
        )
        if not errors:
            continue
        details = [
            f"- {_json_path(error.absolute_path)}: {error.message}"
            for error in errors[:10]
        ]
        if len(errors) > 10:
            details.append(f"- ... and {len(errors) - 10} additional error(s)")
        detail_text = "\n".join(details)
        raise ValueError(
            f"YAML document #{index} failed schema validation:\n{detail_text}"
        )


def _canonical_base_spirit_value(value: Any) -> str | None:
    if not _to_text(value):
        return None
    return BASE_SPIRIT_MAP.get(_normalize_key(value))


def _canonical_glass_value(value: Any) -> str | None:
    if not _to_text(value):
        return None
    return GLASS_CANONICAL_MAP.get(_normalize_recipe_card_key(value))


def _canonical_method_value(value: Any) -> str | None:
    if not _to_text(value):
        return None
    return METHOD_CANONICAL_MAP.get(_normalize_recipe_card_key(value))


def _normalize_alias_fields(doc: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(doc)
    for key in ("base", "base_spirit"):
        if key in normalized:
            mapped_base = _canonical_base_spirit_value(normalized[key])
            if mapped_base:
                normalized[key] = mapped_base
    if "glass" in normalized:
        mapped_glass = _canonical_glass_value(normalized["glass"])
        if mapped_glass:
            normalized["glass"] = mapped_glass
    for key in ("method", "process"):
        if key in normalized:
            mapped_method = _canonical_method_value(normalized[key])
            if mapped_method:
                normalized[key] = mapped_method
    return normalized


def _canonical_base_spirit(doc: dict[str, Any]) -> str:
    base = doc.get("base") or doc.get("base_spirit")
    mapped_base = _canonical_base_spirit_value(base)
    if mapped_base:
        return mapped_base
    ingredients = doc.get("ingredients")
    if isinstance(ingredients, list):
        for entry in ingredients:
            if isinstance(entry, dict):
                ingredient_name = entry.get("name")
            else:
                ingredient_name = entry
            mapped = _canonical_base_spirit_value(ingredient_name)
            if mapped:
                return mapped
    return "Gin"


def _canonical_glass(doc: dict[str, Any]) -> str:
    raw = doc.get("glass")
    if raw is None:
        return "Rocks"
    return _canonical_glass_value(raw) or _to_text(raw).title()


def _canonical_method(doc: dict[str, Any]) -> str:
    raw = doc.get("method") or doc.get("process")
    if raw is None:
        return "Stir"
    return _canonical_method_value(raw) or _to_text(raw).title()


def _render_ingredients(doc: dict[str, Any], *, glass: str, method: str) -> list[str]:
    lines = [r"\begin{ingredients}"]
    raw_ingredients = doc.get("ingredients")
    if isinstance(raw_ingredients, list):
        for ingredient in raw_ingredients:
            if isinstance(ingredient, dict):
                amount = _to_text(ingredient.get("amount"))
                unit = _to_text(ingredient.get("unit"))
                amount_label = " ".join(part for part in [amount, unit] if part).strip()
                name = _to_text(ingredient.get("name"))
            else:
                amount_label = ""
                name = _to_text(ingredient)
            if name:
                lines.append(
                    rf"\ingredient{{{_escape_latex(amount_label)}}}{{{_escape_latex(name)}}}"
                )

    garnish = _to_text(doc.get("garnish"))
    if garnish:
        lines.append(r"\group{Garnish}")
        lines.append(rf"\ingredient{{}}{{{_escape_latex(garnish.title())}}}")

    lines.append(r"\group{Glassware}")
    lines.append(rf"\ingredient{{}}{{{_escape_latex(glass)}}}")
    lines.append(r"\group{Preparation}")
    lines.append(rf"\ingredient{{}}{{{_escape_latex(method)}}}")
    lines.append(r"\end{ingredients}")
    return lines


def _render_steps(doc: dict[str, Any]) -> list[str]:
    lines = [r"\begin{process}"]
    raw_steps = doc.get("steps")
    if isinstance(raw_steps, list) and raw_steps:
        for step in raw_steps:
            step_text = _to_text(step)
            if step_text:
                lines.append(rf"\step{{{_escape_latex(step_text)}}}")
    else:
        lines.append(r"\step{Prepare according to the selected method.}")
    lines.append(r"\end{process}")
    return lines


def _close_list_environments(lines: list[str], list_stack: list[str], *, keep_depth: int) -> None:
    while len(list_stack) > keep_depth:
        list_type = list_stack.pop()
        lines.append(rf"\end{{{list_type}}}")


def _history_markdown_lines(doc: dict[str, Any]) -> list[str]:
    raw = _to_text(doc.get("history"))
    if not raw:
        return ["No historical notes provided."]

    lines: list[str] = []
    paragraph_lines: list[str] = []
    list_stack: list[str] = []

    heading_pattern = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
    unordered_list_pattern = re.compile(r"^(\s*)[-*+]\s+(.+?)\s*$")
    ordered_list_pattern = re.compile(r"^(\s*)\d+[.)]\s+(.+?)\s*$")

    def flush_paragraph() -> None:
        if not paragraph_lines:
            return
        text = " ".join(part.strip() for part in paragraph_lines if part.strip())
        paragraph_lines.clear()
        if text:
            lines.append(_escape_latex(text))
            lines.append(r"\par")

    for raw_line in raw.splitlines():
        line = raw_line.rstrip()

        heading_match = heading_pattern.match(line)
        if heading_match:
            flush_paragraph()
            _close_list_environments(lines, list_stack, keep_depth=0)
            heading_level = len(heading_match.group(1))
            # History block already lives under a "## History & Provenance" section,
            # so treat inline headings as relative levels (e.g. "#" behaves like "###").
            effective_level = min(6, heading_level + 2)
            heading_text = _escape_latex(heading_match.group(2).strip())
            if not heading_text:
                continue
            # Encourage a column/page break before the heading if too little room remains,
            # keeping title + first content line together when possible.
            lines.append(r"\par\filbreak")
            if effective_level <= 3:
                lines.append(
                    rf"\noindent{{\color{{recipeRed}}\textbf{{\scriptsize {heading_text}}}}}\par"
                )
            elif effective_level == 4:
                lines.append(
                    rf"\noindent{{\color{{recipeRed}}\textbf{{\tiny {heading_text}}}}}\par"
                )
            else:
                lines.append(
                    rf"\noindent{{\color{{recipeRed}}\textit{{\tiny {heading_text}}}}}\par"
                )
            continue

        unordered_list_match = unordered_list_pattern.match(line)
        ordered_list_match = ordered_list_pattern.match(line)
        list_match = unordered_list_match or ordered_list_match
        if list_match:
            flush_paragraph()
            list_type = "itemize" if unordered_list_match else "enumerate"
            indent_prefix = list_match.group(1).replace("\t", "  ")
            desired_depth = max(1, len(indent_prefix) // 2 + 1)
            if desired_depth > len(list_stack) + 1:
                desired_depth = len(list_stack) + 1

            _close_list_environments(lines, list_stack, keep_depth=desired_depth)
            if len(list_stack) == desired_depth and list_stack and list_stack[-1] != list_type:
                _close_list_environments(lines, list_stack, keep_depth=desired_depth - 1)
            while len(list_stack) < desired_depth:
                lines.append(rf"\begin{{{list_type}}}")
                lines.append(r"\setlength{\itemsep}{0pt}")
                lines.append(r"\setlength{\parskip}{0pt}")
                lines.append(r"\setlength{\topsep}{1pt}")
                list_stack.append(list_type)

            item_text = _escape_latex(list_match.group(2).strip())
            if item_text:
                lines.append(rf"\item {item_text}")
            else:
                lines.append(r"\item")
            continue

        if not line.strip():
            flush_paragraph()
            continue

        if list_stack:
            _close_list_environments(lines, list_stack, keep_depth=0)
        paragraph_lines.append(line.strip())

    flush_paragraph()
    _close_list_environments(lines, list_stack, keep_depth=0)

    while lines and lines[-1] == r"\par":
        lines.pop()

    if not lines:
        return ["No historical notes provided."]
    return lines


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    slug = normalized.strip("-")
    return slug or "untitled-cocktail"


def _recipe_site_url(doc: dict[str, Any]) -> str:
    name = _to_text(doc.get("cocktail") or doc.get("name") or "untitled-cocktail")
    slug = _slugify(name)
    return f"{RECIPES_SITE_BASE_URL}/cocktails/{slug}"


def _ingredient_sections(doc: dict[str, Any], *, glass: str, method: str) -> list[tuple[str, list[str]]]:
    ingredients_items: list[str] = []
    raw_ingredients = doc.get("ingredients")
    if isinstance(raw_ingredients, list):
        for ingredient in raw_ingredients:
            if isinstance(ingredient, dict):
                amount = _to_text(ingredient.get("amount"))
                unit = _to_text(ingredient.get("unit"))
                amount_label = " ".join(part for part in [amount, unit] if part).strip()
                name = _to_text(ingredient.get("name"))
            else:
                amount_label = ""
                name = _to_text(ingredient)
            if not name:
                continue
            ingredients_items.append(" ".join(part for part in [amount_label, name] if part).strip())

    sections: list[tuple[str, list[str]]] = [("Ingredients", ingredients_items)]
    garnish = _to_text(doc.get("garnish"))
    if garnish:
        sections.append(("Garnish", [garnish.title()]))
    sections.append(("Glassware", [glass]))
    sections.append(("Preparation", [method]))
    return sections


def _render_markdown_sections(sections: list[tuple[str, list[str]]]) -> list[str]:
    lines: list[str] = []
    for section_title, items in sections:
        if section_title != "Ingredients":
            lines.append(f"**{section_title}**")
        if items:
            for item in items:
                lines.append(f"- {item}")
        else:
            lines.append("- None")
        lines.append("")
    return lines


def _render_markdown_sections_html(sections: list[tuple[str, list[str]]]) -> list[str]:
    lines: list[str] = []
    for section_title, items in sections:
        if section_title != "Ingredients":
            lines.append(f"      <p><strong>{html.escape(section_title)}</strong></p>")
        lines.append("      <ul>")
        if items:
            for item in items:
                lines.append(f"        <li>{html.escape(item)}</li>")
        else:
            lines.append("        <li>None</li>")
        lines.append("      </ul>")
    return lines


def _render_markdown_recipe(doc: dict[str, Any]) -> str:
    title = _to_text(doc.get("cocktail") or doc.get("name") or "Untitled Cocktail")
    glass = _canonical_glass(doc)
    method = _canonical_method(doc)
    image = _to_text(doc.get("image"))
    notes = _to_text(doc.get("notes"))
    history = _to_text(doc.get("history"))

    sections = _ingredient_sections(doc, glass=glass, method=method)
    steps = doc.get("steps")
    process_steps: list[str] = []
    if isinstance(steps, list):
        process_steps = [_to_text(step) for step in steps if _to_text(step)]
    if not process_steps:
        process_steps = ["Prepare according to the selected method."]

    lines: list[str] = [f"# {title}", ""]
    if image:
        lines.extend(
            [
                "<table>",
                "  <tr>",
                '    <td valign="top" width="38%">',
                (
                    "      "
                    f'<img src="{html.escape(image, quote=True)}" '
                    f'alt="{html.escape(title, quote=True)}" />'
                ),
                "    </td>",
                '    <td valign="top" width="62%">',
            ]
        )
        lines.extend(_render_markdown_sections_html(sections))
        lines.extend(
            [
                "    </td>",
                "  </tr>",
                "</table>",
                "",
            ]
        )
    else:
        lines.extend(["## Ingredients", ""])
        lines.extend(_render_markdown_sections(sections))

    lines.extend(["## Process", ""])
    for index, step in enumerate(process_steps, start=1):
        lines.append(f"{index}. {step}")

    if notes:
        lines.extend(["", "## Notes", "", notes])
    if history:
        lines.extend(["", "## History & Provenance", "", history.strip()])
    lines.append("")
    return "\n".join(lines)


def _render_recipe(doc: dict[str, Any]) -> str:
    title = _to_text(doc.get("cocktail") or doc.get("name") or "Untitled Cocktail")
    title = _escape_latex(title)
    base_spirit = _canonical_base_spirit(doc)
    glass = _canonical_glass(doc)
    method = _canonical_method(doc)
    notes = _to_text(doc.get("notes"))
    history_lines = _history_markdown_lines(doc)
    url = _recipe_site_url(doc)

    lines: list[str] = [
        r"% --- FRONT SIDE ---",
        rf"\begin{{recipe}}{{{title}}}",
        rf"\setBaseSpirit{{{_escape_latex(base_spirit)}}}",
        r"\noindent\begin{minipage}{\textwidth}",
        r"\small\raggedright",
        rf"\cocktailGlassWithLabel{{{_escape_latex(glass)}}}\quad",
        rf"\cocktailMethodWithLabel{{{_escape_latex(method)}}}\quad",
        r"\end{minipage}\par\vspace{6pt}",
    ]
    lines.extend(_render_ingredients(doc, glass=glass, method=method))
    lines.extend(_render_steps(doc))
    if notes:
        lines.extend(
            [
                "",
                r"\vfill",
                r"\begin{recipeinfo}",
                f"    {_escape_latex(notes)}",
                r"\end{recipeinfo}",
            ]
        )

    lines.extend(
        [
            "",
            r"% --- BACK SIDE ---",
            r"\back",
            r"\drawBackMirrorSpiritBar",
            r"\begin{center}",
            r"    \footnotesize\textsc{\color{recipeRed} History \& Provenance}",
            r"    \vspace{-3pt}",
            r"    \rule{0.92\textwidth}{0.35pt}",
            r"\end{center}",
            r"\vspace{-5pt}",
            r"\begin{multicols*}{2}",
            r"\scriptsize",
            r"\setlength{\columnsep}{9pt}",
            *history_lines,
            r"\vspace{2pt}",
            r"\begin{flushright}",
            rf"\qrcode[height={BACK_PAGE_QR_HEIGHT}]{{{_escape_latex(url)}}}",
            r"\end{flushright}",
            r"\end{multicols*}",
        ]
    )
    lines.extend(["", r"\end{recipe}", ""])
    return "\n".join(lines)


def _render_document(cocktails: Iterable[dict[str, Any]]) -> str:
    blocks = [r"% arara: lualatex_git", r"\documentclass[4x6]{recipe-card}", "", r"\begin{document}", ""]
    for cocktail in cocktails:
        blocks.append(_render_recipe(cocktail))
    blocks.extend([r"\end{document}", ""])
    return "\n".join(blocks)


def _output_path_for(input_path: Path) -> Path:
    lowered_suffix = input_path.suffix.lower()
    if lowered_suffix in {".yaml", ".yml"}:
        return input_path.with_suffix(".tex")
    return Path(f"{input_path}.tex")


def _markdown_output_paths_for(input_path: Path, cocktails: list[dict[str, Any]]) -> list[Path]:
    seen: dict[str, int] = {}
    outputs: list[Path] = []
    for index, doc in enumerate(cocktails, start=1):
        title = _to_text(doc.get("cocktail") or doc.get("name") or f"cocktail-{index}")
        slug = _slugify(title)
        occurrence = seen.get(slug, 0) + 1
        seen[slug] = occurrence
        suffix = "" if occurrence == 1 else f"-{occurrence}"
        outputs.append(input_path.parent / f"{slug}{suffix}.md")
    return outputs


def _write_markdown_documents(input_path: Path, cocktails: list[dict[str, Any]]) -> list[Path]:
    output_paths = _markdown_output_paths_for(input_path, cocktails)
    for cocktail, output_path in zip(cocktails, output_paths):
        output_path.write_text(_render_markdown_recipe(cocktail), encoding="utf-8")
    return output_paths


def _load_cocktails(path: Path) -> list[dict[str, Any]]:
    content = path.read_text(encoding="utf-8")
    parsed = [doc for doc in yaml.safe_load_all(content) if doc is not None]
    cocktails: list[dict[str, Any]] = []
    for index, doc in enumerate(parsed, start=1):
        if not isinstance(doc, dict):
            raise ValueError(f"YAML document #{index} must be a mapping/object.")
        cocktails.append(_normalize_alias_fields(doc))
    if not cocktails:
        raise ValueError("Input YAML contained no cocktail documents.")
    schema_path = _resolve_schema_path()
    schema = _load_schema(schema_path)
    _validate_against_schema(cocktails, schema=schema)
    return cocktails


def main() -> None:
    args = _parse_args()
    input_path = args.yaml_path.expanduser()
    if not input_path.is_absolute():
        workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
        if workspace_dir:
            workspace_candidate = Path(workspace_dir) / input_path
            if workspace_candidate.exists():
                input_path = workspace_candidate
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")
    input_path = input_path.resolve()

    cocktails = _load_cocktails(input_path)
    if args.markdown:
        output_paths = _write_markdown_documents(input_path, cocktails)
        for output_path in output_paths:
            print(output_path)
        return

    output_path = _output_path_for(input_path)
    output_path.write_text(_render_document(cocktails), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
