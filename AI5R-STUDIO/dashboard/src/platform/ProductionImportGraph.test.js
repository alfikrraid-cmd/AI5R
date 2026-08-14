import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const __dirname = dirname(fileURLToPath(import.meta.url));
const dashboardRoot = resolve(__dirname, "../..");
const repoRoot = resolve(dashboardRoot, "../..");
const sourceRoot = resolve(dashboardRoot, "src");
const importPattern = /(?:import\s+(?:[^'"()]*?\s+from\s+)?|export\s+[^'"()]*?\s+from\s+|import\s*\(\s*)["']([^"']+)["']/g;
const fileExtensions = ["", ".js", ".jsx", ".json", ".css"];
const indexExtensions = ["/index.js", "/index.jsx"];

function repoRelative(path) {
  return relative(repoRoot, path).replaceAll("\\", "/");
}

function trackedFiles() {
  return new Set(
    execFileSync("git", ["ls-files", "--cached", "--", "AI5R-STUDIO/dashboard"], {
      cwd: repoRoot,
      encoding: "utf-8",
    })
      .trim()
      .split(/\r?\n/)
      .filter(Boolean)
  );
}

function localImports(source) {
  const imports = [];
  let match;
  while ((match = importPattern.exec(source))) {
    if (match[1].startsWith(".")) {
      imports.push(match[1]);
    }
  }
  return imports;
}

function candidatePaths(importer, specifier) {
  const base = resolve(dirname(importer), specifier);
  return [
    ...fileExtensions.map((extension) => `${base}${extension}`),
    ...indexExtensions.map((extension) => `${base}${extension}`),
  ];
}

function resolveTrackedImport(importer, specifier, tracked, trackedByLowercase) {
  const candidates = candidatePaths(importer, specifier);

  for (const candidate of candidates) {
    const relativePath = repoRelative(candidate);
    if (tracked.has(relativePath)) {
      return { ok: true, path: candidate };
    }
  }

  for (const candidate of candidates) {
    const relativePath = repoRelative(candidate);
    const caseInsensitiveMatch = trackedByLowercase.get(relativePath.toLowerCase());
    if (caseInsensitiveMatch) {
      return {
        ok: false,
        reason: "case mismatch",
        requested: relativePath,
        actual: caseInsensitiveMatch,
      };
    }
  }

  const existingUntracked = candidates.map(repoRelative).find((candidate) => existsSync(resolve(repoRoot, candidate)));
  return {
    ok: false,
    reason: existingUntracked ? "untracked local file" : "missing file",
    requested: repoRelative(candidates[0]),
    actual: existingUntracked ?? null,
  };
}

describe("production dashboard import graph", () => {
  it("resolves every local static import from src/main.jsx from tracked files", () => {
    const tracked = trackedFiles();
    const trackedByLowercase = new Map([...tracked].map((file) => [file.toLowerCase(), file]));
    const entry = resolve(sourceRoot, "main.jsx");
    const queue = [entry];
    const visited = new Set();
    const issues = [];

    while (queue.length) {
      const current = queue.pop();
      const currentRelative = repoRelative(current);
      if (visited.has(currentRelative)) {
        continue;
      }
      visited.add(currentRelative);

      const source = execFileSync("git", ["show", `:${currentRelative}`], {
        cwd: repoRoot,
        encoding: "utf-8",
      });
      for (const specifier of localImports(source)) {
        const resolved = resolveTrackedImport(current, specifier, tracked, trackedByLowercase);
        if (resolved.ok) {
          queue.push(resolved.path);
        } else {
          issues.push({ from: currentRelative, specifier, ...resolved });
        }
      }
    }

    expect(issues).toEqual([]);
  }, 30000);
});