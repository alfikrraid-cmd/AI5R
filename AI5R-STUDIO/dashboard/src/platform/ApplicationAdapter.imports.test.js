import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const __dirname = dirname(fileURLToPath(import.meta.url));
const dashboardRoot = resolve(__dirname, "../..");
const repoRoot = resolve(dashboardRoot, "../..");

function gitTracked(path) {
  const relativePath = relative(repoRoot, path).replaceAll("\\", "/");
  const output = execFileSync("git", ["ls-files", "--", relativePath], {
    cwd: repoRoot,
    encoding: "utf-8",
  }).trim();
  return output === relativePath;
}

function resolveSourceImport(specifier) {
  const basePath = resolve(__dirname, specifier);
  for (const candidate of [basePath, `${basePath}.jsx`, `${basePath}.js`]) {
    if (existsSync(candidate)) {
      return candidate;
    }
  }
  return basePath;
}

describe("ApplicationAdapter production imports", () => {
  it("routes only to source modules that exist in a clean tracked checkout", async () => {
    const module = await import("./ApplicationAdapter.jsx");
    expect(module.PM_WORKSPACE_ROUTE).toBe("/ltsa/pm-workspace");

    for (const specifier of [
      "../modules/ltsa/pages/LTSAWorkspace",
      "../modules/od/pages/ODWorkspace",
      "./Landing",
    ]) {
      const resolved = resolveSourceImport(specifier);
      expect(existsSync(resolved), `${specifier} should exist`).toBe(true);
      expect(gitTracked(resolved), `${specifier} should be tracked by git`).toBe(true);
    }
  });
});