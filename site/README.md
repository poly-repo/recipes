# Recipes Site

Static React site for browsing YAML-backed recipes.

## Source of Truth

Canonical recipe files live one level up in `people/mav/recipes/`:

- `../recipes.yaml` (category catalog)
- category recipe YAMLs referenced by that catalog (for example `../cocktails.yaml`)
- image assets referenced from those YAML files

Before dev/build, the site syncs those files into `public/data/`.

## Local Development

```bash
cd people/mav/recipes/site
npm install
npm run dev
```

Open the URL printed by Vite.

## Build Static Output

```bash
cd people/mav/recipes/site
npm run build
```

The static files are written to `dist/` and can be published to GitHub Pages.

## Publish (Build with Fresh Synced Data)

```bash
cd people/mav/recipes/site
npm run publish
```

`publish` runs `build`, and `build` runs `sync:data` first.

## Data Source

- Runtime catalog source: `public/data/recipes.yaml` (generated from `../recipes.yaml`)
- Each catalog category points to a recipes YAML file (multi-document `---` supported).
- Recipe `image:` paths are resolved **relative to that recipes YAML file location**.
- Missing recipe image falls back to `public/unknown.png`.

To test another catalog path:

```text
http://localhost:5173/?catalog=data/recipes.yaml
```

## Notes

- Routing uses `HashRouter` for GitHub Pages compatibility.
- Home page shows category cards.
- Category summary pages support liquor and strength filtering, and strength sorting.
- Strength is estimated from weighted ABV using ingredient `abv` and `amount`.
