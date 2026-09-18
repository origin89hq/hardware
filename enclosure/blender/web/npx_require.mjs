// Load a CommonJS package that `npx --package name@version` installed for this run.
//
// This repository has no Node workspace, so an ESM import cannot find those packages.
// npx puts the install's node_modules/.bin on PATH; resolve from beside it first, then
// from this file, which also honours NODE_PATH.
import { createRequire } from "node:module";
import { delimiter, join } from "node:path";

export function npxRequire(name, pinned) {
  const bases = (process.env.PATH ?? "")
    .split(delimiter)
    .filter((dir) => dir.endsWith(join("node_modules", ".bin")))
    .map((dir) => join(dir, "..", "resolve.js"));
  for (const base of [...bases, import.meta.filename]) {
    try {
      return createRequire(base)(name);
    } catch (error) {
      if (error.code !== "MODULE_NOT_FOUND") throw error;
    }
  }
  throw new Error(`${name} not found; run through npx --package ${pinned}`);
}
