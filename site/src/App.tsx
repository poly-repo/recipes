import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import { HashRouter, Link, Navigate, Route, Routes, useParams } from "react-router-dom";

import { type RecipeCategory, loadCatalog } from "./lib/catalog";
import { type Recipe, loadRecipes, unknownImagePath } from "./lib/recipes";

type SortMode = "alpha" | "strength_desc" | "strength_asc";

const DEFAULT_CATALOG_PATH = `${import.meta.env.BASE_URL}data/recipes.yaml`;

function catalogPathFromUrl(): string {
  const params = new URLSearchParams(window.location.search);
  const value = params.get("catalog")?.trim();
  return value ? value : DEFAULT_CATALOG_PATH;
}

function formatStrength(strength: Recipe["strength"]): string {
  if (strength === null) {
    return "N/A";
  }
  return `${strength}/3`;
}

function compareTitle(a: Recipe, b: Recipe): number {
  return a.title.localeCompare(b.title, undefined, { sensitivity: "base" });
}

function sortRecipes(recipes: Recipe[], sortMode: SortMode): Recipe[] {
  const sorted = [...recipes];
  if (sortMode === "alpha") {
    return sorted.sort(compareTitle);
  }
  if (sortMode === "strength_desc") {
    return sorted.sort((a, b) => {
      const left = a.strength ?? -1;
      const right = b.strength ?? -1;
      if (right !== left) {
        return right - left;
      }
      return compareTitle(a, b);
    });
  }
  return sorted.sort((a, b) => {
    const left = a.strength ?? 99;
    const right = b.strength ?? 99;
    if (left !== right) {
      return left - right;
    }
    return compareTitle(a, b);
  });
}

function RecipeImage({
  src,
  alt,
  className,
}: {
  src: string;
  alt: string;
  className?: string;
}) {
  const fallback = unknownImagePath();
  const [currentSrc, setCurrentSrc] = useState(src || fallback);

  useEffect(() => {
    setCurrentSrc(src || fallback);
  }, [src, fallback]);

  return (
    <img
      className={className}
      src={currentSrc}
      alt={alt}
      loading="lazy"
      onError={() => {
        if (currentSrc !== fallback) {
          setCurrentSrc(fallback);
        }
      }}
    />
  );
}

function topNav(homeOnly = false) {
  return (
    <nav className="top-nav">
      <Link to="/">Home</Link>
      {!homeOnly ? <span>·</span> : null}
    </nav>
  );
}

function HomePage({
  categories,
  recipesByCategory,
}: {
  categories: RecipeCategory[];
  recipesByCategory: Record<string, Recipe[]>;
}) {
  return (
    <main className="page-shell">
      {topNav(true)}
      <header className="hero">
        <p className="eyebrow">Recipe Library</p>
        <h1>Browse by Category</h1>
        <p className="hero-subtitle">
          Each category points to a YAML recipe source. Start with cocktails and grow from there.
        </p>
      </header>

      <section className="card-grid">
        {categories.map((category) => {
          const count = recipesByCategory[category.slug]?.length ?? 0;
          return (
            <article key={category.id} className="recipe-card">
              <Link to={`/category/${category.slug}`} className="card-link">
                <RecipeImage className="recipe-thumb" src={category.imageUrl} alt={category.name} />
                <div className="card-content">
                  <h2>{category.name}</h2>
                  <div className="badge-row">
                    {category.kind ? <span className="badge">{category.kind}</span> : null}
                    <span className="badge">{count} recipes</span>
                  </div>
                  {category.description ? (
                    <p className="card-description">{category.description}</p>
                  ) : null}
                </div>
              </Link>
            </article>
          );
        })}
      </section>
    </main>
  );
}

function CategorySummaryPage({
  categories,
  recipesByCategory,
}: {
  categories: RecipeCategory[];
  recipesByCategory: Record<string, Recipe[]>;
}) {
  const params = useParams();
  const category = categories.find((entry) => entry.slug === params.categorySlug);
  const recipes = category ? recipesByCategory[category.slug] ?? [] : [];

  const [liquorFilter, setLiquorFilter] = useState("all");
  const [strengthFilter, setStrengthFilter] = useState("all");
  const [sortMode, setSortMode] = useState<SortMode>("alpha");

  if (!category) {
    return (
      <main className="state-shell">
        {topNav(true)}
        <h1>Category not found</h1>
        <p>
          <Link to="/">Return home</Link>
        </p>
      </main>
    );
  }

  const liquorOptions = useMemo(() => {
    const allLiquors = recipes
      .map((recipe) => recipe.liquor)
      .filter((liquor): liquor is string => Boolean(liquor));
    return Array.from(new Set(allLiquors)).sort((a, b) => a.localeCompare(b));
  }, [recipes]);

  const visibleRecipes = useMemo(() => {
    const filtered = recipes.filter((recipe) => {
      const liquorMatches = liquorFilter === "all" || recipe.liquor === liquorFilter;
      const strengthMatches =
        strengthFilter === "all" || String(recipe.strength ?? "") === strengthFilter;
      return liquorMatches && strengthMatches;
    });
    return sortRecipes(filtered, sortMode);
  }, [recipes, liquorFilter, strengthFilter, sortMode]);

  return (
    <main className="page-shell">
      <nav className="top-nav">
        <Link to="/">Home</Link>
      </nav>
      <header className="hero">
        <p className="eyebrow">Category</p>
        <h1>{category.name}</h1>
        <p className="hero-subtitle">
          {category.description ?? "Select a recipe card to open the full details page."}
        </p>
      </header>

      <section className="filter-bar" aria-label="Recipe filters">
        <label>
          Liquor
          <select value={liquorFilter} onChange={(event) => setLiquorFilter(event.target.value)}>
            <option value="all">All</option>
            {liquorOptions.map((liquor) => (
              <option key={liquor} value={liquor}>
                {liquor}
              </option>
            ))}
          </select>
        </label>

        <label>
          Strength
          <select
            value={strengthFilter}
            onChange={(event) => setStrengthFilter(event.target.value)}
          >
            <option value="all">All</option>
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3">3</option>
          </select>
        </label>

        <label>
          Sort
          <select value={sortMode} onChange={(event) => setSortMode(event.target.value as SortMode)}>
            <option value="alpha">Alphabetical</option>
            <option value="strength_desc">Strength: High to Low</option>
            <option value="strength_asc">Strength: Low to High</option>
          </select>
        </label>
      </section>

      <section className="results-meta">
        Showing <strong>{visibleRecipes.length}</strong> of <strong>{recipes.length}</strong> recipes
      </section>

      <section className="card-grid">
        {visibleRecipes.map((recipe) => (
          <article key={recipe.id} className="recipe-card">
            <Link to={`/recipe/${category.slug}/${recipe.slug}`} className="card-link">
              <RecipeImage className="recipe-thumb" src={recipe.imageUrl} alt={recipe.title} />
              <div className="card-content">
                <h2>{recipe.title}</h2>
                <div className="badge-row">
                  <span className="badge">{recipe.liquor ?? "Other"}</span>
                  <span className="badge">Strength {formatStrength(recipe.strength)}</span>
                </div>
              </div>
            </Link>
          </article>
        ))}
      </section>
    </main>
  );
}

function RecipeDetailPage({
  categories,
  recipesByCategory,
}: {
  categories: RecipeCategory[];
  recipesByCategory: Record<string, Recipe[]>;
}) {
  const params = useParams();
  const category = categories.find((entry) => entry.slug === params.categorySlug);
  const recipe = category
    ? (recipesByCategory[category.slug] ?? []).find((entry) => entry.slug === params.recipeSlug)
    : null;

  if (!category || !recipe) {
    return (
      <main className="state-shell">
        {topNav(true)}
        <h1>Recipe not found</h1>
        <p>
          <Link to="/">Return home</Link>
        </p>
      </main>
    );
  }

  return (
    <main className="detail-shell">
      <nav className="top-nav">
        <Link to="/">Home</Link>
        <span>·</span>
        <Link to={`/category/${category.slug}`}>{category.name}</Link>
      </nav>

      <p>
        <Link to={`/category/${category.slug}`} className="back-link">
          ← Back to {category.name}
        </Link>
      </p>

      <header className="detail-header">
        <RecipeImage className="detail-image" src={recipe.imageUrl} alt={recipe.title} />
        <div className="detail-heading">
          <h1>{recipe.title}</h1>
          <div className="badge-row">
            <span className="badge">{recipe.liquor ?? "Other"}</span>
            <span className="badge">Strength {formatStrength(recipe.strength)}</span>
            {recipe.glass ? <span className="badge">{recipe.glass}</span> : null}
            {recipe.method ? <span className="badge">{recipe.method}</span> : null}
            {recipe.garnish ? <span className="badge">Garnish: {recipe.garnish}</span> : null}
          </div>
        </div>
      </header>

      <section className="detail-grid">
        <section className="detail-panel">
          <h2>Ingredients</h2>
          <ul className="ingredient-list">
            {recipe.ingredients.map((ingredient, index) => {
              const amountParts = [ingredient.amountText, ingredient.unit]
                .map((part) => part.trim())
                .filter((part) => part.length > 0);
              return (
                <li key={`${ingredient.name}-${index}`}>
                  <span className="ingredient-amount">{amountParts.join(" ")}</span>
                  <span className="ingredient-name">{ingredient.name}</span>
                </li>
              );
            })}
          </ul>
        </section>

        <section className="detail-panel">
          <h2>Process</h2>
          <ol className="process-list">
            {recipe.steps.length > 0 ? (
              recipe.steps.map((step, index) => <li key={`${step}-${index}`}>{step}</li>)
            ) : (
              <li>Process details were not provided.</li>
            )}
          </ol>
        </section>
      </section>

      {recipe.notes ? (
        <section className="detail-panel prose-block">
          <h2>Notes</h2>
          <ReactMarkdown>{recipe.notes}</ReactMarkdown>
        </section>
      ) : null}

      {recipe.history ? (
        <section className="detail-panel prose-block">
          <h2>History &amp; Provenance</h2>
          <ReactMarkdown>{recipe.history}</ReactMarkdown>
        </section>
      ) : null}
    </main>
  );
}

function SiteRouter({
  categories,
  recipesByCategory,
}: {
  categories: RecipeCategory[];
  recipesByCategory: Record<string, Recipe[]>;
}) {
  return (
    <HashRouter>
      <Routes>
        <Route
          path="/"
          element={<HomePage categories={categories} recipesByCategory={recipesByCategory} />}
        />
        <Route
          path="/category/:categorySlug"
          element={
            <CategorySummaryPage categories={categories} recipesByCategory={recipesByCategory} />
          }
        />
        <Route
          path="/recipe/:categorySlug/:recipeSlug"
          element={<RecipeDetailPage categories={categories} recipesByCategory={recipesByCategory} />}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </HashRouter>
  );
}

export default function App() {
  const [categories, setCategories] = useState<RecipeCategory[]>([]);
  const [recipesByCategory, setRecipesByCategory] = useState<Record<string, Recipe[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const catalogPath = useMemo(catalogPathFromUrl, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    loadCatalog(catalogPath)
      .then(async (loadedCategories) => {
        if (!active) {
          return;
        }
        setCategories(loadedCategories);
        const entries = await Promise.all(
          loadedCategories.map(async (category) => {
            const recipes = await loadRecipes(category.recipesPath);
            return [category.slug, recipes] as const;
          }),
        );
        if (!active) {
          return;
        }
        setRecipesByCategory(Object.fromEntries(entries));
      })
      .catch((caught) => {
        if (!active) {
          return;
        }
        setError(caught instanceof Error ? caught.message : String(caught));
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [catalogPath]);

  if (loading) {
    return (
      <main className="state-shell">
        <h1>Loading recipe catalog…</h1>
      </main>
    );
  }

  if (error) {
    return (
      <main className="state-shell">
        <h1>Unable to load catalog</h1>
        <p>{error}</p>
        <p>
          Catalog path: <code>{catalogPath}</code>
        </p>
      </main>
    );
  }

  return <SiteRouter categories={categories} recipesByCategory={recipesByCategory} />;
}
