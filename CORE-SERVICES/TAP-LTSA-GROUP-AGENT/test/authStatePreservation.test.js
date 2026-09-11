import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

// MWO-LTSA-069 -- "never delete auth state automatically" is a
// requirement about what index.js must NOT do, on a path (an
// UNRECOVERABLE disconnect) that only a real, paired Baileys connection
// can actually reach. Exercising that live would mean touching a real
// WhatsApp session, which this MWO explicitly prohibits. Asserting it as
// a source-level invariant -- no filesystem-mutation call anywhere near
// AUTH_STATE_DIR -- is the honest, safe alternative: a regression that
// adds such a call fails this test without needing a live session.

const indexJsPath = fileURLToPath(new URL("../src/index.js", import.meta.url));

test("index.js never calls a filesystem-deletion API (rm/rmSync/unlink/rmdir/rimraf) anywhere in the file", async () => {
  const source = await readFile(indexJsPath, "utf8");
  const forbidden = /\b(fs\.)?(rmSync|rmdirSync|unlinkSync|rm|rmdir|unlink|rimraf)\s*\(/;
  const match = source.match(forbidden);
  assert.equal(match, null, `found a filesystem-deletion call: ${match?.[0]}`);
});

test("index.js's UNRECOVERABLE close path exits the process instead of clearing auth state", async () => {
  const source = await readFile(indexJsPath, "utf8");
  const unrecoverableBlock = source.slice(
    source.indexOf('decision.action === "EXIT_UNRECOVERABLE"'),
    source.indexOf('decision.action === "EXIT_ATTEMPTS_EXHAUSTED"')
  );
  assert.ok(unrecoverableBlock.includes("process.exit(1)"), "UNRECOVERABLE branch must exit the process");
  assert.ok(
    !/AUTH_STATE_DIR/.test(unrecoverableBlock),
    "UNRECOVERABLE branch must never reference AUTH_STATE_DIR (i.e. never touch the auth state files)"
  );
});
