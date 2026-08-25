import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const ltsaRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const sampleNames = [
  "samplePMSchedules",
  "samplePumps",
  "sampleWorkOrders",
  "sampleCMReports",
  "sampleDocuments",
  "sampleDrawings",
  "sampleSeals",
];
const runtimeExtensions = new Set([".js", ".jsx"]);

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (["TESTS", "__snapshots__"].includes(entry.name)) return [];
      return walk(fullPath);
    }
    return [fullPath];
  });
}

function isRuntimeFile(file) {
  const basename = path.basename(file);
  return runtimeExtensions.has(path.extname(file)) && !basename.includes(".test.") && !basename.startsWith("sample");
}

describe("production runtime sample-data boundaries", () => {
  it("does not import scoped sample modules from runtime LTSA code", () => {
    const offenders = walk(ltsaRoot)
      .filter(isRuntimeFile)
      .filter((file) => {
        const content = fs.readFileSync(file, "utf8");
        return sampleNames.some((name) => new RegExp(`from\\s+["'][^"']*${name}["']`).test(content));
      })
      .map((file) => path.relative(ltsaRoot, file).replaceAll(path.sep, "/"));

    expect(offenders).toEqual([]);
  });
});
