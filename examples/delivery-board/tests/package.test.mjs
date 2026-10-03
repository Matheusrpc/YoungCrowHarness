import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, mkdir, copyFile, writeFile, readFile, readdir, rm, link, symlink, stat} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join, resolve, dirname, basename} from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {build} from '../package.mjs';

const files = ['index.html', 'style.css', 'app.mjs', 'model.mjs', 'data.json', 'gema-cobalto.svg'];
const original = fileURLToPath(new URL('../', import.meta.url));
async function fixture(t) {
  const base = await mkdtemp(join(tmpdir(), 'yc-package-'));
  t.after(async () => {
    assert.equal(dirname(resolve(base)), resolve(tmpdir()));
    assert.ok(basename(base).startsWith('yc-package-'));
    await rm(base, {recursive:true, force:true});
  });
  const source = join(base, 'source'), destination = join(base, 'site');
  await mkdir(source);
  for (const name of files) await copyFile(join(original, name), join(source, name));
  return {base, source, destination};
}

test('publica apenas os seis arquivos e hashes reais; preserva destino existente', async t => {
  const {source, destination} = await fixture(t);
  await mkdir(join(source,'vault','local'), {recursive:true});
  await writeFile(join(source,'vault','local','private.md'), 'PRIVATE SENTINEL');
  await writeFile(join(source,'.env'), 'PRIVATE SENTINEL');
  await writeFile(join(source,'unexpected.txt'), 'PRIVATE SENTINEL');
  const manifest = await build(source, destination, 'a'.repeat(40));
  assert.equal(manifest.revision, 'a'.repeat(40));
  assert.equal(manifest.schema_version, 1);
  assert.deepEqual((await readdir(destination)).sort(),
    ['app.mjs','data.json','gema-cobalto.svg','index.html','manifest.json','model.mjs','style.css']);
  for (const name of files) {
    const bytes = await readFile(join(destination,name));
    assert.equal(manifest.files[name], createHash('sha256').update(bytes).digest('hex'));
    assert.deepEqual(bytes, await readFile(join(source,name)));
  }
  await assert.rejects(build(source,destination,'b'.repeat(40)), /destination_exists/);
  assert.equal(JSON.parse(await readFile(join(destination,'manifest.json'),'utf8')).revision, 'a'.repeat(40));
});

test('falha antes de criar staging para dados, revisão ou arquivo inválido', async t => {
  const {source, destination} = await fixture(t);
  await assert.rejects(build(source,destination,'not-a-revision'), /invalid_revision/);
  await assert.rejects(build(source,join(source,'site'),'a'.repeat(40)), /destination_inside_source/);
  const data = JSON.parse(await readFile(join(source,'data.json'),'utf8'));
  data[0].evidence = ['file:///private'];
  await writeFile(join(source,'data.json'),JSON.stringify(data));
  await assert.rejects(build(source,destination,'a'.repeat(40)), /invalid_features/);
  await copyFile(join(original,'data.json'),join(source,'data.json'));
  await rm(join(source,'style.css'));
  await assert.rejects(build(source,destination,'a'.repeat(40)));
  await assert.rejects(stat(destination), {code:'ENOENT'});
});

test('recusa hardlink em arquivo publicável', async t => {
  const {source, destination, base} = await fixture(t);
  await link(join(source,'data.json'),join(base,'linked.json'));
  await assert.rejects(build(source,destination,'a'.repeat(40)), /unsafe_source/);
  await assert.rejects(stat(destination), {code:'ENOENT'});
});

test('recusa symlink em arquivo e na raiz de origem', async t => {
  const {source, destination, base} = await fixture(t);
  await rm(join(source,'data.json'));
  try { await symlink(join(original,'data.json'),join(source,'data.json')); }
  catch (error) {
    if (process.platform === 'win32' && ['EPERM','EACCES'].includes(error.code)) {
      t.skip('Windows não concedeu criação de symlink de arquivo; caso obrigatório no Linux'); return;
    }
    throw error;
  }
  await assert.rejects(build(source,destination,'a'.repeat(40)), /unsafe_source/);
  const linkedRoot = join(base,'linked-root');
  await symlink(source,linkedRoot,process.platform === 'win32' ? 'junction' : 'dir');
  await assert.rejects(build(linkedRoot,destination,'a'.repeat(40)), /unsafe_source/);
});
