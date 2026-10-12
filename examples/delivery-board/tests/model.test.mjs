import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {validateFeatures, selectFeatures, filtersFromURL, filtersToURL, EVIDENCE_URLS} from '../model.mjs';

const sample = [
  {id: 'list', title: 'Listar entregas', summary: 'Ver critérios', status: 'production',
    acceptance: ['Mostra critérios'], evidence: [EVIDENCE_URLS[0]]},
  {id: 'filter', title: 'Filtrar entregas', summary: 'Escolher estado', status: 'development',
    acceptance: ['Limpar recupera a lista'], evidence: [EVIDENCE_URLS[1]]},
];

test('combina estado e busca; limpar recupera a ordem original sem mutação', () => {
  const before = structuredClone(sample);
  const features = validateFeatures(sample);
  assert.deepEqual(selectFeatures(features, 'development', ' FILTRAR ').map(x => x.id), ['filter']);
  assert.deepEqual(selectFeatures(features, 'production', 'Filtrar'), []);
  assert.deepEqual(selectFeatures(features, 'all', 'critérios').map(x => x.id), ['list']);
  assert.deepEqual(selectFeatures(features).map(x => x.id), ['list', 'filter']);
  assert.deepEqual(sample, before);
});

test('recusa dados incompletos, duplicados e fora do contrato', () => {
  for (const raw of [null, {}, [null], [sample[0], sample[0]],
    [{...sample[0], id: ' '}], [{...sample[0], title: 'x'.repeat(2001)}],
    [{...sample[0], status: 'done'}], [{...sample[0], secret: 'not-public'}],
    [{...sample[0], acceptance: []}], [{...sample[0], evidence: []}],
    [{...sample[0], acceptance: [42]}], Array(101).fill(sample[0])]) {
    assert.throws(() => validateFeatures(raw), /invalid_features/);
  }
  assert.deepEqual(validateFeatures([]), []);
});

test('mantém marcação como texto e só aceita os destinos revisados', () => {
  const raw = structuredClone(sample);
  raw[0].title = '<img src=x onerror=alert(1)>';
  assert.equal(validateFeatures(raw)[0].title, raw[0].title);
  for (const value of ['javascript:alert(1)', 'file:///private', '/vault/local/note',
    'https://github.com.evil.invalid/note', EVIDENCE_URLS[0] + '?token=private',
    'https://user:password@github.com/Matheusrpc/YoungCrowHarness']) {
    raw[0].evidence = [value];
    assert.throws(() => validateFeatures(raw), /invalid_features/);
  }
});

test('os dados publicados têm as três entregas fictícias válidas', async () => {
  const data = JSON.parse(await readFile(new URL('../data.json', import.meta.url), 'utf8'));
  assert.deepEqual(validateFeatures(data).map(x => x.id), ['list', 'filter', 'export']);
});

test('reabre a consulta compartilhada com o mesmo estado, texto e resultado', () => {
  const {status, query} = filtersFromURL('https://example.test/board/?status=development&q=FILTRAR');
  assert.deepEqual({status, query}, {status: 'development', query: 'FILTRAR'});
  assert.deepEqual(selectFeatures(sample, status, query).map(x => x.id), ['filter']);
  assert.deepEqual(filtersFromURL('https://example.test/board/'), {status: 'all', query: ''});
});

test('estado desconhecido usa todos; parâmetros repetidos usam o primeiro valor', () => {
  assert.deepEqual(filtersFromURL('https://example.test/?status=unknown&q=critérios'),
    {status: 'all', query: 'critérios'});
  assert.deepEqual(filtersFromURL('https://example.test/?status=planned&status=production&q=primeiro&q=segundo'),
    {status: 'planned', query: 'primeiro'});
});

test('serializa texto literalmente; limpar remove só filtros e preserva o endereço original', () => {
  const original = new URL('https://example.test/board/?ref=a&ref=b&status=planned&status=production&q=antigo#quadro');
  const before = original.href;
  const query = ' critérios & [ação] + <script> ';
  const changed = new URL(filtersToURL(original, 'development', query));
  assert.deepEqual(filtersFromURL(changed), {status: 'development', query});
  assert.deepEqual(changed.searchParams.getAll('status'), ['development']);
  assert.deepEqual(changed.searchParams.getAll('ref'), ['a', 'b']);
  assert.equal(changed.pathname, '/board/');
  assert.equal(changed.hash, '#quadro');
  assert.equal(original.href, before);
  const cleared = new URL(filtersToURL(changed, 'all', ''));
  assert.equal(cleared.href, 'https://example.test/board/?ref=a&ref=b#quadro');
});
