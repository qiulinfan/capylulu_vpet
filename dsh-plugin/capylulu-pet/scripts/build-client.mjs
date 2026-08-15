// Builds lib/client.js from src/client.js by inlining the sprite atlas
// (data URL) and the frame manifest. Zero dependencies - plain Node.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const srcPath = join(root, "src", "client.js");
const atlasPath = join(root, "assets", "atlas.webp");
const manifestPath = join(root, "assets", "manifest.json");
const outPath = join(root, "lib", "client.js");

const atlas = readFileSync(atlasPath);
const dataUrl = "data:image/webp;base64," + atlas.toString("base64");
const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));

let source = readFileSync(srcPath, "utf8");
for (const token of ["__ATLAS_DATA_URL__", "__MANIFEST_JSON__"]) {
  if (!source.includes(token)) throw new Error("template placeholder missing: " + token);
}
source = source
  .replace("__ATLAS_DATA_URL__", dataUrl)
  .replace("__MANIFEST_JSON__", JSON.stringify(manifest));

mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, source);
console.log(
  "wrote " + outPath + " (" + (Buffer.byteLength(source) / 1024).toFixed(1) + " KiB)"
);
