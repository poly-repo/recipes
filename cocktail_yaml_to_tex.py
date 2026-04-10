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

import yaml


BASE_SPIRIT_MAP: dict[str, str] = {
    "gin": "Gin",
    "whiskey": "Whiskey",
    "whisky": "Whiskey",
    "rum": "Rum",
    "vodka": "Vodka",
    "tequila": "Tequila",
}

GLASS_MAP: dict[str, str] = {
    "rock": "Rocks",
    "rocks": "Rocks",
    "rock glass": "Rock Glass",
    "old fashioned": "Old Fashioned",
    "old-fashioned": "Old Fashioned",
    "collins": "Collins",
    "highball": "Highball",
    "martini": "Martini",
    "coupe": "Coupe",
    "nick and nora": "Nick and Nora",
    "nick & nora": "Nick and Nora",
    "champagne flute": "Champagne Flute",
    "hurricane": "Hurricane",
    "wine glass": "Wine Glass",
    "tiki mug": "Tiki Mug",
}

METHOD_MAP: dict[str, str] = {
    "stir": "Stirred",
    "stirred": "Stirred",
    "stirring": "Stirred",
    "shake": "Shake",
    "shaken": "Shaken",
    "shaking": "Shake",
    "build": "Build",
    "built": "Built",
    "building": "Build",
    "muddle": "Muddled",
    "muddled": "Muddled",
    "muddling": "Muddled",
    "blend": "Blend",
    "blended": "Blended",
    "blending": "Blend",
    "layer": "Layered",
    "layered": "Layered",
    "layering": "Layered",
    "float": "Floated",
    "floated": "Floated",
    "floating": "Floated",
    "flame": "Flamed",
    "flamed": "Flamed",
    "flaming": "Flamed",
    "reverse dry shake": "Reverse Dry Shake",
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


def _canonical_base_spirit(doc: dict[str, Any]) -> str:
    base = doc.get("base") or doc.get("base_spirit")
    if base:
        mapped = BASE_SPIRIT_MAP.get(_normalize_key(base))
        if mapped:
            return mapped
    ingredients = doc.get("ingredients")
    if isinstance(ingredients, list):
        for entry in ingredients:
            if isinstance(entry, dict):
                ingredient_name = entry.get("name")
            else:
                ingredient_name = entry
            mapped = BASE_SPIRIT_MAP.get(_normalize_key(ingredient_name))
            if mapped:
                return mapped
    return "Gin"


def _canonical_glass(doc: dict[str, Any]) -> str:
    raw = doc.get("glass")
    if raw is None:
        return "Rocks"
    key = _normalize_key(raw)
    return GLASS_MAP.get(key, _to_text(raw).title())


def _canonical_method(doc: dict[str, Any]) -> str:
    raw = doc.get("method") or doc.get("process")
    if raw is None:
        return "Stirred"
    key = _normalize_key(raw)
    return METHOD_MAP.get(key, _to_text(raw).title())


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
        cocktails.append(doc)
    if not cocktails:
        raise ValueError("Input YAML contained no cocktail documents.")
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
