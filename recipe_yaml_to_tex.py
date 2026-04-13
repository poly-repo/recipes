"""Generate recipe-card TeX from recipe YAML documents.

Usage:
    bazel run //people/mav/recipes:recipe_yaml_to_tex -- path/to/file.yaml

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


SCHEMA_FILE_NAME = "recipe.schema.yaml"
CATALOG_FILE_NAME = "recipes.yaml"
RECIPES_SITE_BASE_URL = "https://poly-repo.github.io/recipes"
BACK_PAGE_QR_HEIGHT = "0.72in"

KIND_COCKTAIL = "cocktail"
KIND_FOOD = "food"

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

RECIPE_TYPE_CANONICAL_MAP: dict[str, str] = {
    "bakery": "Bakery",
    "primi": "Primi",
    "secondi": "Secondi",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("yaml_path", type=Path, help="Input recipe YAML file.")
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Write one Markdown file per recipe document instead of TeX output.",
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


def _normalize_recipe_kind(value: Any) -> str | None:
    normalized = _normalize_key(value)
    if normalized in {KIND_COCKTAIL, KIND_FOOD}:
        return normalized
    return None


def _is_remote_reference(value: str) -> bool:
    return bool(re.match(r"^(https?:|data:|blob:)", value, flags=re.IGNORECASE))


def _resolve_repo_file_path(file_name: str) -> Path:
    candidate_paths = [Path(__file__).resolve().with_name(file_name)]
    workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace_dir:
        candidate_paths.append(Path(workspace_dir) / "people/mav/recipes" / file_name)
    for candidate in candidate_paths:
        if candidate.exists():
            return candidate
    searched = ", ".join(str(path) for path in candidate_paths)
    raise FileNotFoundError(
        f"Unable to locate {file_name}; searched: {searched}"
    )


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"YAML at {path} must be a mapping/object.")
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
    recipes: list[dict[str, Any]],
    *,
    schema: dict[str, Any],
) -> None:
    validator = Draft202012Validator(schema)
    for index, doc in enumerate(recipes, start=1):
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


def _canonical_recipe_type_value(value: Any) -> str | None:
    if not _to_text(value):
        return None
    return RECIPE_TYPE_CANONICAL_MAP.get(_normalize_recipe_card_key(value))


def _normalize_alias_fields(doc: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(doc)
    normalized_kind = _normalize_recipe_kind(normalized.get("kind"))
    if normalized_kind:
        normalized["kind"] = normalized_kind

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
    if "recipe_type" in normalized:
        mapped_recipe_type = _canonical_recipe_type_value(normalized["recipe_type"])
        if mapped_recipe_type:
            normalized["recipe_type"] = mapped_recipe_type
    return normalized


def _recipe_title(doc: dict[str, Any]) -> str:
    return _to_text(
        doc.get("cocktail")
        or doc.get("name")
        or doc.get("title")
        or "Untitled Recipe"
    )


def _effective_recipe_kind(doc: dict[str, Any]) -> str:
    explicit_kind = _normalize_recipe_kind(doc.get("kind"))
    if explicit_kind:
        return explicit_kind
    if _to_text(doc.get("recipe_type")):
        return KIND_FOOD
    return KIND_COCKTAIL


def _determine_file_kind(recipes: list[dict[str, Any]]) -> str:
    kinds = {_effective_recipe_kind(doc) for doc in recipes}
    if len(kinds) > 1:
        kinds_text = ", ".join(sorted(kinds))
        raise ValueError(
            "Input YAML contains mixed recipe kinds. "
            f"Expected exactly one kind per file, found: {kinds_text}"
        )
    return next(iter(kinds))


def _resolve_category_info_for_input(input_path: Path) -> tuple[str, str | None]:
    catalog_path = _resolve_repo_file_path(CATALOG_FILE_NAME)
    catalog = _load_yaml_mapping(catalog_path)
    categories = catalog.get("categories")
    if not isinstance(categories, list):
        raise ValueError(f"Catalog {catalog_path} must contain a 'categories' array.")

    input_resolved = input_path.resolve()
    for index, raw_category in enumerate(categories, start=1):
        if not isinstance(raw_category, dict):
            continue
        recipes_ref = _to_text(
            raw_category.get("recipes")
            or raw_category.get("source")
            or raw_category.get("file")
        )
        if not recipes_ref or _is_remote_reference(recipes_ref):
            continue

        recipes_path = Path(recipes_ref).expanduser()
        if not recipes_path.is_absolute():
            recipes_path = (catalog_path.parent / recipes_path)
        if recipes_path.resolve() != input_resolved:
            continue

        slug = _to_text(raw_category.get("slug"))
        if not slug:
            category_name = _to_text(raw_category.get("name")) or f"category-{index}"
            slug = _slugify(category_name)
        category_kind = _normalize_recipe_kind(
            raw_category.get("kind") or raw_category.get("type")
        )
        return slug, category_kind

    raise ValueError(
        "Input YAML is not referenced by recipes.yaml categories. "
        f"Cannot resolve category slug for QR links: {input_path}"
    )


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


def _canonical_recipe_type(doc: dict[str, Any]) -> str:
    raw = doc.get("recipe_type")
    mapped = _canonical_recipe_type_value(raw)
    if mapped:
        return mapped
    raw_text = _to_text(raw)
    return raw_text.title() if raw_text else "Bakery"


def _ingredient_items(doc: dict[str, Any]) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    raw_ingredients = doc.get("ingredients")
    if not isinstance(raw_ingredients, list):
        return items
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
            items.append((amount_label, name))
    return items


def _render_cocktail_ingredients(doc: dict[str, Any], *, glass: str, method: str) -> list[str]:
    lines = [r"\begin{ingredients}"]
    for amount_label, name in _ingredient_items(doc):
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


def _render_food_ingredients(doc: dict[str, Any]) -> list[str]:
    lines = [r"\begin{ingredients}"]
    for amount_label, name in _ingredient_items(doc):
        lines.append(
            rf"\ingredient{{{_escape_latex(amount_label)}}}{{{_escape_latex(name)}}}"
        )
    lines.append(r"\end{ingredients}")
    return lines


def _render_steps(doc: dict[str, Any], *, default_step: str) -> list[str]:
    lines = [r"\begin{process}"]
    raw_steps = doc.get("steps")
    if isinstance(raw_steps, list) and raw_steps:
        for step in raw_steps:
            step_text = _to_text(step)
            if step_text:
                lines.append(rf"\step{{{_escape_latex(step_text)}}}")
    else:
        lines.append(rf"\step{{{_escape_latex(default_step)}}}")
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
            effective_level = min(6, heading_level + 2)
            heading_text = _escape_latex(heading_match.group(2).strip())
            if not heading_text:
                continue
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
    return slug or "untitled-recipe"


def _recipe_site_url(doc: dict[str, Any], *, category_slug: str) -> str:
    slug = _slugify(_recipe_title(doc))
    return f"{RECIPES_SITE_BASE_URL}/{category_slug}/{slug}"


def _ingredient_sections_for_cocktail(
    doc: dict[str, Any],
    *,
    glass: str,
    method: str,
) -> list[tuple[str, list[str]]]:
    ingredients_items: list[str] = []
    for amount_label, name in _ingredient_items(doc):
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


def _render_markdown_cocktail_recipe(doc: dict[str, Any]) -> str:
    title = _recipe_title(doc) or "Untitled Cocktail"
    glass = _canonical_glass(doc)
    method = _canonical_method(doc)
    image = _to_text(doc.get("image"))
    notes = _to_text(doc.get("notes"))
    history = _to_text(doc.get("history"))

    sections = _ingredient_sections_for_cocktail(doc, glass=glass, method=method)
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


def _render_markdown_food_recipe(doc: dict[str, Any]) -> str:
    title = _recipe_title(doc) or "Untitled Recipe"
    image = _to_text(doc.get("image"))
    notes = _to_text(doc.get("notes"))
    history = _to_text(doc.get("history"))

    lines: list[str] = [f"# {title}", ""]
    if image:
        lines.extend([f"![{title}]({image})", ""])

    lines.extend(["## Ingredients", ""])
    ingredient_rows = _ingredient_items(doc)
    if ingredient_rows:
        for amount_label, name in ingredient_rows:
            item_text = " ".join(part for part in [amount_label, name] if part).strip()
            lines.append(f"- {item_text}")
    else:
        lines.append("- None")

    lines.extend(["", "## Process", ""])
    raw_steps = doc.get("steps")
    steps: list[str] = []
    if isinstance(raw_steps, list):
        steps = [_to_text(step) for step in raw_steps if _to_text(step)]
    if not steps:
        steps = ["Follow the preparation steps."]
    for index, step in enumerate(steps, start=1):
        lines.append(f"{index}. {step}")

    if notes:
        lines.extend(["", "## Notes", "", notes])
    if history:
        lines.extend(["", "## History & Provenance", "", history.strip()])
    lines.append("")
    return "\n".join(lines)


def _render_back_side(doc: dict[str, Any], *, category_slug: str) -> list[str]:
    history_lines = _history_markdown_lines(doc)
    url = _recipe_site_url(doc, category_slug=category_slug)
    return [
        "",
        r"% --- BACK SIDE ---",
        r"\back",
        r"\drawBackMirrorRecipeBar",
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


def _render_cocktail_recipe(doc: dict[str, Any], *, category_slug: str) -> str:
    title = _escape_latex(_recipe_title(doc) or "Untitled Cocktail")
    base_spirit = _canonical_base_spirit(doc)
    glass = _canonical_glass(doc)
    method = _canonical_method(doc)
    notes = _to_text(doc.get("notes"))

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
    lines.extend(_render_cocktail_ingredients(doc, glass=glass, method=method))
    lines.extend(_render_steps(doc, default_step="Prepare according to the selected method."))
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
    lines.extend(_render_back_side(doc, category_slug=category_slug))
    lines.extend(["", r"\end{recipe}", ""])
    return "\n".join(lines)


def _render_food_recipe(doc: dict[str, Any], *, category_slug: str) -> str:
    title = _escape_latex(_recipe_title(doc) or "Untitled Recipe")
    recipe_type = _canonical_recipe_type(doc)
    notes = _to_text(doc.get("notes"))

    lines: list[str] = [
        r"% --- FRONT SIDE ---",
        rf"\begin{{recipe}}{{{title}}}",
        rf"\setRecipeType{{{_escape_latex(recipe_type)}}}",
    ]
    lines.extend(_render_food_ingredients(doc))
    lines.extend(_render_steps(doc, default_step="Follow the preparation steps."))
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
    lines.extend(_render_back_side(doc, category_slug=category_slug))
    lines.extend(["", r"\end{recipe}", ""])
    return "\n".join(lines)


def _render_document(
    recipes: Iterable[dict[str, Any]],
    *,
    file_kind: str,
    category_slug: str,
) -> str:
    blocks = [
        r"% arara: lualatex_git",
        rf"\documentclass[4x6,{file_kind}]{{recipe-card}}",
        "",
        r"\begin{document}",
        "",
    ]
    for doc in recipes:
        if file_kind == KIND_FOOD:
            blocks.append(_render_food_recipe(doc, category_slug=category_slug))
        else:
            blocks.append(_render_cocktail_recipe(doc, category_slug=category_slug))
    blocks.extend([r"\end{document}", ""])
    return "\n".join(blocks)


def _output_path_for(input_path: Path) -> Path:
    lowered_suffix = input_path.suffix.lower()
    if lowered_suffix in {".yaml", ".yml"}:
        return input_path.with_suffix(".tex")
    return Path(f"{input_path}.tex")


def _markdown_output_paths_for(input_path: Path, recipes: list[dict[str, Any]]) -> list[Path]:
    seen: dict[str, int] = {}
    outputs: list[Path] = []
    for index, doc in enumerate(recipes, start=1):
        title = _recipe_title(doc) or f"recipe-{index}"
        slug = _slugify(title)
        occurrence = seen.get(slug, 0) + 1
        seen[slug] = occurrence
        suffix = "" if occurrence == 1 else f"-{occurrence}"
        outputs.append(input_path.parent / f"{slug}{suffix}.md")
    return outputs


def _write_markdown_documents(
    input_path: Path,
    recipes: list[dict[str, Any]],
    *,
    file_kind: str,
) -> list[Path]:
    output_paths = _markdown_output_paths_for(input_path, recipes)
    for doc, output_path in zip(recipes, output_paths):
        if file_kind == KIND_FOOD:
            rendered = _render_markdown_food_recipe(doc)
        else:
            rendered = _render_markdown_cocktail_recipe(doc)
        output_path.write_text(rendered, encoding="utf-8")
    return output_paths


def _load_recipes(path: Path) -> tuple[list[dict[str, Any]], str, str]:
    content = path.read_text(encoding="utf-8")
    parsed = [doc for doc in yaml.safe_load_all(content) if doc is not None]
    recipes: list[dict[str, Any]] = []
    for index, doc in enumerate(parsed, start=1):
        if not isinstance(doc, dict):
            raise ValueError(f"YAML document #{index} must be a mapping/object.")
        recipes.append(_normalize_alias_fields(doc))
    if not recipes:
        raise ValueError("Input YAML contained no recipe documents.")

    schema_path = _resolve_repo_file_path(SCHEMA_FILE_NAME)
    schema = _load_yaml_mapping(schema_path)
    _validate_against_schema(recipes, schema=schema)

    file_kind = _determine_file_kind(recipes)
    category_slug, category_kind = _resolve_category_info_for_input(path)
    if category_kind and category_kind != file_kind:
        raise ValueError(
            "Category kind mismatch for input YAML. "
            f"Category declares '{category_kind}' but recipe file resolves to '{file_kind}'."
        )

    return recipes, file_kind, category_slug


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

    recipes, file_kind, category_slug = _load_recipes(input_path)
    if args.markdown:
        output_paths = _write_markdown_documents(input_path, recipes, file_kind=file_kind)
        for output_path in output_paths:
            print(output_path)
        return

    output_path = _output_path_for(input_path)
    output_path.write_text(
        _render_document(recipes, file_kind=file_kind, category_slug=category_slug),
        encoding="utf-8",
    )
    print(output_path)


if __name__ == "__main__":
    main()
