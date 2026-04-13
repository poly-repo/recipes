import { parseAllDocuments } from "yaml";

import { unknownImagePath } from "./recipes";

type JsonRecord = Record<string, unknown>;
export type RecipeCategoryKind = "cocktail" | "food";

export interface RecipeCategory {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  kind: RecipeCategoryKind | null;
  recipesPath: string;
  imageUrl: string;
}

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
  return normalized || "category";
}

function resolveRelativeAsset(basePath: string, relativeOrAbsolute: string): string {
  if (/^(https?:|data:|blob:)/i.test(relativeOrAbsolute)) {
    return relativeOrAbsolute;
  }
  if (relativeOrAbsolute.startsWith("/")) {
    return relativeOrAbsolute;
  }
  const absoluteBase = new URL(basePath, window.location.href);
  return new URL(relativeOrAbsolute, absoluteBase).toString();
}

function toCategoryKind(value: unknown): RecipeCategoryKind | null {
  const text = toText(value)?.toLowerCase();
  if (text === "cocktail" || text === "food") {
    return text;
  }
  return null;
}

function normalizeCategory(
  rawEntry: JsonRecord,
  options: {
    index: number;
    catalogPath: string;
    slugCounts: Map<string, number>;
  },
): RecipeCategory {
  const { index, catalogPath, slugCounts } = options;
  const name = toText(rawEntry.name) ?? `Category ${index + 1}`;
  const slugBase = slugify(toText(rawEntry.slug) ?? name);
  const seen = (slugCounts.get(slugBase) ?? 0) + 1;
  slugCounts.set(slugBase, seen);
  const slug = seen === 1 ? slugBase : `${slugBase}-${seen}`;

  const recipesPointer =
    toText(rawEntry.recipes) ?? toText(rawEntry.source) ?? toText(rawEntry.file);
  if (!recipesPointer) {
    throw new Error(`Category "${name}" is missing a recipes pointer.`);
  }

  const imagePointer = toText(rawEntry.image);
  const description = toText(rawEntry.description);
  const kind = toCategoryKind(rawEntry.kind) ?? toCategoryKind(rawEntry.type);

  return {
    id: `${slug}::${index}`,
    slug,
    name,
    description,
    kind,
    recipesPath: resolveRelativeAsset(catalogPath, recipesPointer),
    imageUrl: imagePointer
      ? resolveRelativeAsset(catalogPath, imagePointer)
      : unknownImagePath(),
  };
}

function extractCategoryEntries(parsedRoot: unknown): unknown[] {
  if (Array.isArray(parsedRoot)) {
    return parsedRoot;
  }
  const rootRecord = asRecord(parsedRoot);
  if (!rootRecord) {
    return [];
  }
  const maybeCategories = rootRecord.categories;
  if (Array.isArray(maybeCategories)) {
    return maybeCategories;
  }
  return [];
}

export async function loadCatalog(catalogPath: string): Promise<RecipeCategory[]> {
  const response = await fetch(catalogPath);
  if (!response.ok) {
    throw new Error(`Failed to load catalog YAML from ${catalogPath} (${response.status})`);
  }
  const content = await response.text();
  const documents = parseAllDocuments(content);
  const parseErrors = documents.flatMap((document) => document.errors);
  if (parseErrors.length > 0) {
    throw new Error(`Catalog YAML parse failed: ${parseErrors.map((e) => e.message).join("; ")}`);
  }

  const firstDocument = documents.find((document) => document.toJSON() !== null);
  if (!firstDocument) {
    return [];
  }

  const entries = extractCategoryEntries(firstDocument.toJSON());
  const slugCounts = new Map<string, number>();
  const categories: RecipeCategory[] = [];
  for (let index = 0; index < entries.length; index += 1) {
    const entry = asRecord(entries[index]);
    if (!entry) {
      continue;
    }
    categories.push(
      normalizeCategory(entry, {
        index,
        catalogPath,
        slugCounts,
      }),
    );
  }
  return categories;
}
