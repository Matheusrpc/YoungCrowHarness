import {lstat, readFile, mkdir, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve, relative, isAbsolute, dirname, join, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {validateFeatures} from './model.mjs';

export const PUBLIC_FILES = ['index.html', 'style.css', 'app.mjs', 'model.mjs', 'data.json', 'gema-cobalto.svg'];

async function directories(path) {
  for (let current = path; ; current = dirname(current)) {
    const info = await lstat(current);
    if (!info.isDirectory() || info.isSymbolicLink()) throw new Error('unsafe_source');
    if (dirname(current) === current) return;
  }
}

export async function build(source, destination, revision) {
  if (typeof revision !== 'string' || !/^[a-f0-9]{40}$/.test(revision)) throw new Error('invalid_revision');
  source = resolve(source);
  destination = resolve(destination);
  const child = relative(source, destination);
  if (child === '' || (child !== '..' && !child.startsWith('..' + sep) && !isAbsolute(child))) {
    throw new Error('destination_inside_source');
  }
  await directories(source);
  await directories(dirname(destination));
  try {
    await lstat(destination);
    throw new Error('destination_exists');
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
  const preparedFiles = [];
  for (const name of PUBLIC_FILES) {
    const file = join(source, name);
    const info = await lstat(file);
    if (!info.isFile() || info.isSymbolicLink() || info.nlink !== 1) throw new Error('unsafe_source');
    const bytes = await readFile(file);
    if (name === 'data.json') validateFeatures(JSON.parse(bytes.toString('utf8')));
    preparedFiles.push([name, bytes]);
  }
  const manifest = {schema_version:1, revision, files:{}};
  for (const [name, bytes] of preparedFiles) manifest.files[name] = createHash('sha256').update(bytes).digest('hex');
  await mkdir(destination);
  for (const [name, bytes] of preparedFiles) await writeFile(join(destination, name), bytes, {flag:'wx'});
  await writeFile(join(destination, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n', {flag:'wx'});
  return manifest;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    if (process.argv.length !== 4) throw new Error('usage');
    const manifest = await build(fileURLToPath(new URL('.', import.meta.url)), process.argv[2], process.argv[3]);
    console.log(JSON.stringify(manifest));
  } catch {
    console.error('Package failed: use a new destination outside the source, a Git revision and reviewed regular files.');
    process.exitCode = 1;
  }
}
