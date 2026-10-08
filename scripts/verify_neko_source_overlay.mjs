import { createHash } from 'node:crypto';
import { readdir, readFile, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const overlay = path.join(repo, 'patches/neko-study-2026-10-09-v02-overlay');
const manifest = JSON.parse((await readFile(path.join(overlay, 'manifest.json'), 'utf8')).replace(/^\uFEFF/, ''));

if (manifest.format !== 'livetutor-source-overlay-v1' || !Array.isArray(manifest.files)) {
  throw new Error('Unsupported or malformed source-overlay manifest');
}

const payloadRoot = path.join(overlay, 'payload');
const expectedPayloads = new Set(manifest.files.map((entry) => entry.payload.replaceAll('\\', '/')));
if (expectedPayloads.size !== manifest.files.length) throw new Error('Duplicate payload path in manifest');
const expectedSources = new Set(manifest.files.map((entry) => entry.source.replaceAll('\\', '/')));
if (expectedSources.size !== manifest.files.length) throw new Error('Duplicate source path in manifest');

async function collectPayloadFiles(directory, prefix = '') {
  const result = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const relative = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isDirectory()) result.push(...await collectPayloadFiles(path.join(directory, entry.name), relative));
    else if (entry.isFile()) result.push(relative);
    else throw new Error(`Unsupported filesystem entry in payload: ${relative}`);
  }
  return result;
}

const actualPayloads = (await collectPayloadFiles(payloadRoot)).map((entry) => `payload/${entry}`);
const actualSet = new Set(actualPayloads);
const missingPayloads = [...expectedPayloads].filter((entry) => !actualSet.has(entry));
const undeclaredPayloads = actualPayloads.filter((entry) => !expectedPayloads.has(entry));
if (missingPayloads.length || undeclaredPayloads.length) {
  throw new Error(`Payload closed-set mismatch: missing=${missingPayloads.join(',')} undeclared=${undeclaredPayloads.join(',')}`);
}

function safePath(base, relative) {
  const resolved = path.resolve(base, relative.replaceAll('\\', '/'));
  const relativeToBase = path.relative(base, resolved);
  if (!relativeToBase || relativeToBase === '..' || relativeToBase.startsWith(`..${path.sep}`) || path.isAbsolute(relativeToBase)) {
    throw new Error(`Path escapes its base: ${relative}`);
  }
  return resolved;
}

async function verify(relative, expectedHash, expectedBytes) {
  const absolute = safePath(repo, relative);
  const [contents, metadata] = await Promise.all([readFile(absolute), stat(absolute)]);
  const actualHash = createHash('sha256').update(contents).digest('hex');
  if (actualHash !== expectedHash || metadata.size !== expectedBytes) {
    throw new Error(`Mismatch: ${relative}`);
  }
  return metadata.size;
}

let bytes = 0;
for (const entry of manifest.files) {
  bytes += await verify(`patches/neko-study-2026-10-09-v02-overlay/${entry.payload}`, entry.sha256, entry.bytes);
  bytes += await verify(entry.source, entry.sha256, entry.bytes);
}

for (const alias of manifest.redundant_payloads ?? []) {
  bytes += await verify(`patches/neko-study-2026-10-09-v02-overlay/${alias.payload}`, alias.sha256, alias.bytes);
  const canonical = manifest.files.find((entry) => entry.payload === alias.canonical_payload);
  if (!canonical || canonical.sha256 !== alias.sha256 || canonical.bytes !== alias.bytes) {
    throw new Error(`Invalid duplicate payload alias: ${alias.payload}`);
  }
}

console.log(`PASS: closed payload set of ${actualPayloads.length} files; ${manifest.files.length} source entries; ${bytes} verified bytes.`);
