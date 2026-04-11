import { promises as fs } from "node:fs";
import path from "node:path";
import process from "node:process";

import YAML from "yaml";

const SITE_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const SOURCE_ROOT = path.resolve(SITE_ROOT, "..");
const SOURCE_CATALOG = path.resolve(SOURCE_ROOT, "recipes.yaml");
const DEST_DATA_ROOT = path.resolve(SITE_ROOT, "public", "data");
const DEST_CATALOG = path.resolve(DEST_DATA_ROOT, "recipes.yaml");

function isRemoteReference(value) {
  return /^(https?:|data:|blob:)/i.test(value) || value.startsWith("/");
}

function normalizePath(filePath) {
  return filePath.replace(/^\/+([A-Za-z]:)/, "$1");
}

function categoryRecipesPointer(category) {
  if (!category || typeof category !== "object") {
    return null;
  }
  for (const key of ["recipes", "source", "file"]) {
    const value = category[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return null;
}

function categoriesFromCatalog(rawCatalog) {
  if (Array.isArray(rawCatalog)) {
    return rawCatalog;
  }
  if (!rawCatalog || typeof rawCatalog !== "object") {
    return [];
  }
  if (Array.isArray(rawCatalog.categories)) {
    return rawCatalog.categories;
  }
  return [];
}

function resolvedReference(baseFile, referenceValue) {
  return path.resolve(path.dirname(baseFile), referenceValue);
}

function assertInsideRoot(resolvedPath, rootPath, message) {
  const normalizedResolved = normalizePath(path.resolve(resolvedPath));
  const normalizedRoot = normalizePath(path.resolve(rootPath));
  const relative = path.relative(normalizedRoot, normalizedResolved);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(message);
  }
}

async function ensureParent(filePath) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
}

async function copyByReference(baseSourceFile, baseDestFile, referenceValue, copiedSet) {
  if (typeof referenceValue !== "string" || !referenceValue.trim()) {
    return;
  }
  if (isRemoteReference(referenceValue)) {
    return;
  }

  const sourceFile = resolvedReference(baseSourceFile, referenceValue);
  const destFile = resolvedReference(baseDestFile, referenceValue);

  assertInsideRoot(
    sourceFile,
    SOURCE_ROOT,
    `Ref '${referenceValue}' resolves outside source root: ${sourceFile}`,
  );
  assertInsideRoot(
    destFile,
    DEST_DATA_ROOT,
    `Ref '${referenceValue}' resolves outside site public/data root: ${destFile}`,
  );

  const normalizedDest = normalizePath(destFile);
  if (copiedSet.has(normalizedDest)) {
    return;
  }

  await ensureParent(destFile);
  await fs.copyFile(sourceFile, destFile);
  copiedSet.add(normalizedDest);
  console.log(`synced ${path.relative(SITE_ROOT, destFile)}`);
}

function parseYamlDocuments(fileContent, filePath) {
  const documents = YAML.parseAllDocuments(fileContent);
  const errors = documents.flatMap((document) => document.errors);
  if (errors.length > 0) {
    throw new Error(
      `YAML parse errors in ${filePath}: ${errors.map((error) => error.message).join("; ")}`,
    );
  }
  return documents.map((document) => document.toJSON()).filter((value) => value !== null);
}

async function syncCatalogAndRecipes() {
  const copiedFiles = new Set();

  await ensureParent(DEST_CATALOG);
  const catalogContent = await fs.readFile(SOURCE_CATALOG, "utf8");
  await fs.writeFile(DEST_CATALOG, catalogContent, "utf8");
  copiedFiles.add(normalizePath(DEST_CATALOG));
  console.log(`synced ${path.relative(SITE_ROOT, DEST_CATALOG)}`);

  const catalogDocs = parseYamlDocuments(catalogContent, SOURCE_CATALOG);
  const catalogRoot = catalogDocs[0] ?? {};
  const categories = categoriesFromCatalog(catalogRoot);

  for (const category of categories) {
    if (!category || typeof category !== "object") {
      continue;
    }
    const recipesRef = categoryRecipesPointer(category);
    if (!recipesRef) {
      continue;
    }
    if (isRemoteReference(recipesRef)) {
      continue;
    }

    const sourceRecipes = resolvedReference(SOURCE_CATALOG, recipesRef);
    const destRecipes = resolvedReference(DEST_CATALOG, recipesRef);
    assertInsideRoot(
      sourceRecipes,
      SOURCE_ROOT,
      `Recipes pointer '${recipesRef}' resolves outside source root`,
    );
    assertInsideRoot(
      destRecipes,
      DEST_DATA_ROOT,
      `Recipes pointer '${recipesRef}' resolves outside destination root`,
    );
    await ensureParent(destRecipes);
    await fs.copyFile(sourceRecipes, destRecipes);
    copiedFiles.add(normalizePath(destRecipes));
    console.log(`synced ${path.relative(SITE_ROOT, destRecipes)}`);

    const sourceRecipesContent = await fs.readFile(sourceRecipes, "utf8");
    const recipeDocs = parseYamlDocuments(sourceRecipesContent, sourceRecipes);
    for (const recipeDoc of recipeDocs) {
      if (!recipeDoc || typeof recipeDoc !== "object") {
        continue;
      }
      await copyByReference(sourceRecipes, destRecipes, recipeDoc.image, copiedFiles);
    }

    await copyByReference(SOURCE_CATALOG, DEST_CATALOG, category.image, copiedFiles);
  }
}

async function main() {
  try {
    await syncCatalogAndRecipes();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(message);
    process.exit(1);
  }
}

main();
