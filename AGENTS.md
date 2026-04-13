# Recipes Work Context

This document captures architecture and implementation decisions for the `people/mav/recipes` area so future work stays consistent.

## Scope

This directory currently has two product surfaces:

- LaTeX recipe card generation (`cocktail_yaml_to_tex.py` + `recipe-card.cls` integration)
- Static React website (`site/`) deployed to GitHub Pages style hosting

The current data model is cocktail-first but intentionally extensible to other categories.

## Copybara Export Model

Parts of this monorepo are published to a public repository (`poly-repo/recipes`) via Copybara.

Current workflow:

```python
copybara_workflow(
    name = "recipes",
    excludes = [
    ],
    includes = [
        "arararc.yaml",
        "common/arara/**",
        "common/latex/**",
        "people/mav/recipes/**",
    ],
    moves = {
        "people/mav/recipes": "",
        "EXTERNAL_LICENSE": "LICENSE",
    },
)
```

Meaning:

- Everything under `people/mav/recipes` becomes top-level in the public repo.
- `common/latex/**` is also exported and remains at `common/latex/**`.
- `common/arara/**` and `arararc.yaml` are exported for LaTeX tooling support.

Path implications:

- In omega monorepo, site lives at `people/mav/recipes/site`.
- In public repo, site lives at `site`.
- In both layouts, source-of-truth catalog is one directory above site:
- monorepo: `people/mav/recipes/site -> ../recipes.yaml`
- public repo: `site -> ../recipes.yaml`
- Therefore the current `sync:data` parent-relative design is intentionally compatible with both repos.

## Source of Truth Rules

Canonical editable data lives in `people/mav/recipes/` (not `site/public/data/`):

- `recipes.yaml`: category catalog
- Category YAML files referenced by catalog, for example `cocktails/cocktails.yaml`
- Images referenced by those YAMLs, for example `cocktails/assets/images/*.jpg`

`site/public/data/*` is generated/synced runtime data for the static frontend.

Do not treat `site/public/data/*` as authoritative content.

## Schemas

- `cocktail.schema.yaml`: schema for recipe docs (one YAML file may contain multiple docs separated by `---`)
- `recipes.schema.yaml`: schema for category catalog

Current catalog shape (`recipes.yaml`) is:

- top-level object with `categories`
- each category includes:
- `name`
- `recipes` (path/URL to recipe YAML)
- optional `slug`
- optional `kind`
- optional `image`
- optional `description`

## LaTeX Pipeline Decisions

Primary generator: `cocktail_yaml_to_tex.py`

Key behavior:

- Validates each YAML doc against `cocktail.schema.yaml` using JSON Schema draft 2020-12
- Normalizes glass/method aliases to canonical values used by `recipe-card.cls`
- Supports two output modes:
- default mode writes one `.tex` document
- `--markdown` mode writes one `.md` file per recipe document
- Back page history parsing treats `history` as lightweight markdown-like text:
- headings (`#`, `##`, …), lists, paragraphs
- heading levels are relative to existing back-page “History & Provenance” context
- QR code target on back page is generated as:
- `https://poly-repo.github.io/recipes/cocktails/<slug>`
- Back page color bar stability invariant:
- emit `\drawBackMirrorSpiritBar` immediately after `\back`
- avoid overlay-based QR placement that interferes with shipout-layer rendering

Important practical note:

- `image` is optional in schema; if omitted, downstream site fallback image is used

## React Site Decisions (`site/`)

Framework/tooling:

- Vite + React + TypeScript
- Router: `HashRouter` for GitHub Pages compatibility
- Vite `base` is `./` for static-relative asset resolution

Routing model:

- `/` (hash root): global category summary
- `/category/:categorySlug`: summary page for a category
- `/recipe/:categorySlug/:recipeSlug`: full detail page for one recipe

Current UX behavior:

- Category cards use category `image` + `name`
- Recipe cards use recipe `image` + title
- Fallback image: `public/unknown.png`
- Recipe summary filters:
- liquor filter
- strength filter (`1`, `2`, `3`)
- sort by alphabetic or strength
- Recipe detail page includes:
- Home link
- category link
- explicit back link to category summary

Data loading:

- Catalog is loaded from `public/data/recipes.yaml` by default
- Override catalog path via query param:
- `?catalog=<path>`
- Recipe and image paths are resolved relative to the YAML file that declares them

Strength computation:

- Weighted average ABV from ingredients with both `abv` and numeric `amount`
- Bucket:
- `<18 => 1`
- `<28 => 2`
- otherwise `3`

## Sync/Publish Workflow

Use frontend scripts in `site/package.json`:

- `npm run sync:data`: copy source-of-truth YAML/images into `site/public/data`
- `npm run dev`: runs `sync:data` first, then starts dev server
- `npm run build`: runs `sync:data` first, then builds static assets
- `npm run publish`: alias for build-with-sync intended for deploy pipeline usage

Sync implementation:

- `site/scripts/sync-data.mjs`
- Copies:
- `../recipes.yaml -> public/data/recipes.yaml`
- each referenced category recipe YAML to matching `public/data/...` path
- category image and per-recipe `image` assets if local relative paths
- Enforces path safety (prevents escape outside roots)

## Common Pitfalls

- Editing `site/public/data/*` directly can be overwritten by next `sync:data`
- If a recipe image “disappears”, check that recipe YAML has explicit `image:` key
- Browser may cache images with same filename; hard refresh after image replacement
- For GitHub Pages-style hosting, keep `HashRouter`; switching to browser history mode will break deep links without server rewrites

## How to Add New Category

1. Add category entry to `recipes.yaml` with `name` and `recipes`.
2. Create the referenced recipes YAML file.
3. Add image paths in category/recipe YAMLs (optional but recommended).
4. Run `cd people/mav/recipes/site && npm run sync:data`.
5. Run `npm run dev` or `npm run publish`.

## Build/Test Commands

LaTeX/YAML generator:

- `bazel build //people/mav/recipes:cocktail_yaml_to_tex`
- `bazel run //people/mav/recipes:cocktail_yaml_to_tex -- people/mav/recipes/cocktails/cocktails.yaml`
- `python3 people/mav/recipes/cocktail_yaml_to_tex.py --markdown people/mav/recipes/cocktails/cocktails.yaml`

Site:

- `cd people/mav/recipes/site`
- `npm install`
- `npm run dev`
- `npm run publish`

## File Map (High Value)

- `cocktail_yaml_to_tex.py`: generator + markdown mode + schema validation
- `cocktail.schema.yaml`: recipe schema
- `recipes.schema.yaml`: catalog schema
- `recipes.yaml`: category catalog source-of-truth
- `cocktails/cocktails.yaml`: cocktail source-of-truth
- `site/src/App.tsx`: app routes and screens
- `site/src/lib/catalog.ts`: catalog loader/normalizer
- `site/src/lib/recipes.ts`: recipe loader/normalizer/strength logic
- `site/scripts/sync-data.mjs`: source-of-truth sync pipeline
