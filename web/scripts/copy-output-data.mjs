import { cp, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const target = resolve(dirname(fileURLToPath(import.meta.url)), "../public/outputs");
await mkdir(target, { recursive: true });
await cp(resolve(root, "outputs"), target, { recursive: true });
