import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const manifestPath = resolve(root, "assets/binary/manifest.json");
const manifest = JSON.parse(await readFile(manifestPath, "utf8"));

for (const asset of manifest.files) {
  const encoded = await readFile(resolve(root, asset.source), "utf8");
  const contents = Buffer.from(encoded.replace(/\s/g, ""), "base64");
  const digest = createHash("sha256").update(contents).digest("hex");
  if (digest !== asset.sha256 || contents.length !== asset.bytes) {
    throw new Error(`El asset codificado no coincide con el manifiesto: ${asset.source}`);
  }
  const destination = resolve(root, asset.path);
  await mkdir(dirname(destination), { recursive: true });
  await writeFile(destination, contents);
}

console.log(`Restaurados ${manifest.files.length} assets binarios.`);
