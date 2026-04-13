import { parseAllDocuments } from "yaml";

type JsonRecord = Record<string, unknown>;
export type RecipeKind = "cocktail" | "food";

export interface Ingredient {
  name: string;
  amountText: string;
  amountValue: number | null;
  unit: string;
  abv: number | null;
}

export interface Recipe {
  id: string;
  slug: string;
  kind: RecipeKind;
  recipeType: string | null;
  title: string;
  imageUrl: string;
  liquor: string | null;
  strength: 1 | 2 | 3 | null;
  method: string | null;
  glass: string | null;
  garnish: string | null;
  notes: string | null;
  history: string | null;
  ingredients: Ingredient[];
  steps: string[];
  sourcePath: string;
}

const KNOWN_LIQUORS: Array<[string, string]> = [
  ["gin", "Gin"],
  ["whiskey", "Whiskey"],
  ["whisky", "Whiskey"],
  ["rum", "Rum"],
  ["vodka", "Vodka"],
  ["tequila", "Tequila"],
];

function asRecord(value: unknown): JsonRecord | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as JsonRecord;
}

function toText(value: unknown): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return Number.isInteger(value) ? String(value) : String(value);
  }
  return null;
}

function slugify(value: string): string {
  const normalized = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return normalized || "untitled-recipe";
}

function toRecipeKind(value: unknown): RecipeKind | null {
  const text = toText(value)?.toLowerCase();
  if (text === "cocktail" || text === "food") {
    return text;
  }
  return null;
}

function parseFractionToken(token: string): number | null {
  const fractionMatch = token.match(/^(\d+)\s*\/\s*(\d+)$/);
  if (!fractionMatch) {
    return null;
  }
  const numerator = Number(fractionMatch[1]);
  const denominator = Number(fractionMatch[2]);
  if (denominator === 0) {
    return null;
  }
  return numerator / denominator;
}

function parseAmount(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  const text = toText(value);
  if (!text) {
    return null;
  }

  const normalized = text.replace(/,/g, ".").trim();
  const direct = Number(normalized);
  if (!Number.isNaN(direct)) {
    return direct;
  }

  const parts = normalized.split(/\s+/);
  if (parts.length === 2) {
    const whole = Number(parts[0]);
    const fraction = parseFractionToken(parts[1]);
    if (!Number.isNaN(whole) && fraction !== null) {
      return whole + fraction;
    }
  }

  return parseFractionToken(normalized);
}

function baseUnknownImageUrl(): string {
  return `${import.meta.env.BASE_URL}unknown.png`;
}

function resolveImagePath(yamlPath: string, imagePath: string | null): string {
  if (!imagePath) {
    return baseUnknownImageUrl();
  }

  if (/^(https?:|data:|blob:)/i.test(imagePath)) {
    return imagePath;
  }

  if (imagePath.startsWith("/")) {
    return imagePath;
  }

  const absoluteYamlUrl = new URL(yamlPath, window.location.href);
  return new URL(imagePath, absoluteYamlUrl).toString();
}

function inferLiquor(baseSpirit: string | null, ingredients: Ingredient[]): string | null {
  const normalizedBase = baseSpirit?.toLowerCase() ?? "";
  for (const [needle, canonical] of KNOWN_LIQUORS) {
    if (normalizedBase.includes(needle)) {
      return canonical;
    }
  }

  for (const ingredient of ingredients) {
    const ingredientName = ingredient.name.toLowerCase();
    for (const [needle, canonical] of KNOWN_LIQUORS) {
      if (ingredientName.includes(needle)) {
        return canonical;
      }
    }
  }

  return null;
}

function computeStrength(ingredients: Ingredient[]): 1 | 2 | 3 | null {
  let weightedAbv = 0;
  let totalAmount = 0;
  for (const ingredient of ingredients) {
    if (ingredient.abv === null || ingredient.amountValue === null) {
      continue;
    }
    if (ingredient.amountValue <= 0) {
      continue;
    }
    weightedAbv += ingredient.abv * ingredient.amountValue;
    totalAmount += ingredient.amountValue;
  }

  if (totalAmount <= 0) {
    return null;
  }

  const averageAbv = weightedAbv / totalAmount;
  if (averageAbv < 18) {
    return 1;
  }
  if (averageAbv < 28) {
    return 2;
  }
  return 3;
}

function parseIngredients(rawIngredients: unknown): Ingredient[] {
  if (!Array.isArray(rawIngredients)) {
    return [];
  }

  const ingredients: Ingredient[] = [];
  for (const entry of rawIngredients) {
    const entryRecord = asRecord(entry);
    if (!entryRecord) {
      const text = toText(entry);
      if (!text) {
        continue;
      }
      ingredients.push({
        name: text,
        amountText: "",
        amountValue: null,
        unit: "",
        abv: null,
      });
      continue;
    }

    const name = toText(entryRecord.name);
    if (!name) {
      continue;
    }
    const amountText = toText(entryRecord.amount) ?? "";
    const unit = toText(entryRecord.unit) ?? "";
    const abvRaw = entryRecord.abv;
    const abv = typeof abvRaw === "number" && Number.isFinite(abvRaw) ? abvRaw : null;

    ingredients.push({
      name,
      amountText,
      amountValue: parseAmount(entryRecord.amount),
      unit,
      abv,
    });
  }

  return ingredients;
}

function parseSteps(rawSteps: unknown): string[] {
  if (!Array.isArray(rawSteps)) {
    return [];
  }
  return rawSteps
    .map((step) => toText(step))
    .filter((step): step is string => Boolean(step));
}

function inferRecipeKind(
  rawDoc: JsonRecord,
  categoryKindHint: RecipeKind | null,
): RecipeKind {
  const explicitKind = toRecipeKind(rawDoc.kind);
  if (explicitKind) {
    return explicitKind;
  }
  if (toText(rawDoc.recipe_type)) {
    return "food";
  }
  if (categoryKindHint) {
    return categoryKindHint;
  }
  return "cocktail";
}

function normalizeRecipe(
  rawDoc: JsonRecord,
  options: {
    index: number;
    kind: RecipeKind;
    yamlPath: string;
    existingSlugs: Map<string, number>;
  },
): Recipe {
  const { index, kind, yamlPath, existingSlugs } = options;
  const title =
    toText(rawDoc.cocktail) ??
    toText(rawDoc.name) ??
    toText(rawDoc.title) ??
    `Recipe ${index + 1}`;

  const baseSlug = slugify(title);
  const count = (existingSlugs.get(baseSlug) ?? 0) + 1;
  existingSlugs.set(baseSlug, count);
  const slug = count === 1 ? baseSlug : `${baseSlug}-${count}`;

  const ingredients = parseIngredients(rawDoc.ingredients);
  const steps = parseSteps(rawDoc.steps);
  const imagePath = toText(rawDoc.image);
  const method = kind === "cocktail" ? toText(rawDoc.method) ?? toText(rawDoc.process) : null;
  const glass = kind === "cocktail" ? toText(rawDoc.glass) : null;
  const garnish = kind === "cocktail" ? toText(rawDoc.garnish) : null;
  const notes = toText(rawDoc.notes) ?? toText(rawDoc.description);
  const history = toText(rawDoc.history) ?? toText(rawDoc.background);
  const recipeType = kind === "food" ? toText(rawDoc.recipe_type) ?? toText(rawDoc.type) : null;
  const baseSpirit =
    kind === "cocktail" ? toText(rawDoc.base) ?? toText(rawDoc.base_spirit) : null;
  const liquor = kind === "cocktail" ? inferLiquor(baseSpirit, ingredients) : null;
  const strength = kind === "cocktail" ? computeStrength(ingredients) : null;

  return {
    id: `${slug}::${index}`,
    slug,
    kind,
    recipeType,
    title,
    imageUrl: resolveImagePath(yamlPath, imagePath),
    liquor,
    strength,
    method,
    glass,
    garnish,
    notes,
    history,
    ingredients,
    steps,
    sourcePath: yamlPath,
  };
}

export async function loadRecipes(
  yamlPath: string,
  categoryKindHint: string | null = null,
): Promise<Recipe[]> {
  const response = await fetch(yamlPath);
  if (!response.ok) {
    throw new Error(`Failed to load recipes YAML from ${yamlPath} (${response.status})`);
  }
  const content = await response.text();

  const documents = parseAllDocuments(content);
  const parseErrors = documents.flatMap((doc) => doc.errors);
  if (parseErrors.length > 0) {
    throw new Error(`YAML parse failed: ${parseErrors.map((error) => error.message).join("; ")}`);
  }

  const slugs = new Map<string, number>();
  const recipes: Recipe[] = [];
  const normalizedCategoryKind = toRecipeKind(categoryKindHint);
  let fileKind: RecipeKind | null = null;
  for (let index = 0; index < documents.length; index += 1) {
    const docValue = documents[index].toJSON();
    if (docValue === null || docValue === undefined) {
      continue;
    }
    const docRecord = asRecord(docValue);
    if (!docRecord) {
      continue;
    }
    const recipeKind = inferRecipeKind(docRecord, normalizedCategoryKind);
    if (normalizedCategoryKind && recipeKind !== normalizedCategoryKind) {
      throw new Error(
        `Kind mismatch in ${yamlPath}: category kind is "${normalizedCategoryKind}" but document #${index + 1} resolves to "${recipeKind}".`,
      );
    }
    if (fileKind && fileKind !== recipeKind) {
      throw new Error(
        `Mixed recipe kinds in ${yamlPath}: expected one kind per file but found "${fileKind}" and "${recipeKind}".`,
      );
    }
    fileKind = recipeKind;
    recipes.push(
      normalizeRecipe(docRecord, {
        index,
        kind: recipeKind,
        yamlPath,
        existingSlugs: slugs,
      }),
    );
  }

  return recipes;
}

export function unknownImagePath(): string {
  return baseUnknownImageUrl();
}
