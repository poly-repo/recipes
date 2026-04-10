"""Generate recipe-card TeX from cocktail YAML documents.

Usage:
    bazel run //people/mav/recipes:cocktail_yaml_to_tex -- path/to/file.yaml

The output path is derived from the input path by replacing `.yaml`/`.yml`
with `.tex`.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator
import yaml


SCHEMA_FILE_NAME = "cocktail.schema.yaml"

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


def _history_text(doc: dict[str, Any]) -> str:
    raw = _to_text(doc.get("history"))
    if not raw:
        return "No historical notes provided."
    paragraphs: list[str] = []
    for paragraph in raw.split("\n\n"):
        normalized = " ".join(part.strip() for part in paragraph.splitlines() if part.strip())
        if normalized:
            paragraphs.append(_escape_latex(normalized))
    if not paragraphs:
        return "No historical notes provided."
    return "\n\n  ".join(paragraphs)


def _source_url(doc: dict[str, Any]) -> str:
    for key in ("url", "source_url", "reference_url", "link"):
        value = _to_text(doc.get(key))
        if value:
            return value
    source = doc.get("source")
    if isinstance(source, dict):
        for key in ("url", "link"):
            value = _to_text(source.get(key))
            if value:
                return value
    return ""


def _render_recipe(doc: dict[str, Any]) -> str:
    title = _to_text(doc.get("cocktail") or doc.get("name") or "Untitled Cocktail")
    title = _escape_latex(title)
    base_spirit = _canonical_base_spirit(doc)
    glass = _canonical_glass(doc)
    method = _canonical_method(doc)
    notes = _to_text(doc.get("notes"))
    history = _history_text(doc)
    url = _source_url(doc)

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
            r"\begin{center}",
            r"    \small\textsc{\color{recipeRed} History \& Provenance}",
            r"    \rule{\textwidth}{0.4pt}",
            r"\end{center}",
            r"\begin{multicols}{2}",
            f"  \\footnotesize {history}",
            r"\end{multicols}",
            "",
            r"\vfill",
            r"\drawBackMirrorSpiritBar",
        ]
    )
    if url:
        lines.append(rf"\noindent\hfill\qrcode[height=0.84in]{{{_escape_latex(url)}}}")
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
    output_path = _output_path_for(input_path)
    output_path.write_text(_render_document(cocktails), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
