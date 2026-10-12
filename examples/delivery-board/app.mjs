import {validateFeatures, selectFeatures, filtersFromURL, filtersToURL} from './model.mjs';

const status = document.querySelector('#status');
const query = document.querySelector('#query');
const clear = document.querySelector('#clear');
const results = document.querySelector('#results');
const message = document.querySelector('#message');
const filterHelp = document.querySelector('#filter-help');
const shareHint = filterHelp.textContent;
const labels = {planned: 'Planejada', development: 'Em desenvolvimento', production: 'Em produção · fictício'};
let features = [];

function restoreFilters() {
  const saved = filtersFromURL(window.location.href);
  status.value = saved.status;
  query.value = saved.query;
  filterHelp.textContent = shareHint;
  if (!status.disabled) render();
}

restoreFilters();
window.addEventListener('popstate', restoreFilters);

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function render() {
  const selected = selectFeatures(features, status.value, query.value);
  results.replaceChildren();
  message.textContent = selected.length ? `${selected.length} de ${features.length} entregas no cenário.` :
    'Nenhuma entrega corresponde aos filtros.';
  for (const item of selected) {
    const card = element('li', undefined, 'delivery');
    card.append(element('span', labels[item.status], `status status-${item.status}`),
      element('h2', item.title), element('p', item.summary, 'description'));
    const details = element('details');
    const criteria = element('ul', undefined, 'criteria');
    for (const criterion of item.acceptance) criteria.append(element('li', criterion));
    details.append(element('summary', 'Critérios de aceite'), criteria);
    card.append(details);
    item.evidence.forEach((url, i) => {
      const link = element('a', item.evidence.length === 1 ? 'Evidência no vault ↗' : `Evidência ${i + 1} no vault ↗`, 'evidence');
      link.href = url;
      card.append(link);
    });
    results.append(card);
  }
}

function changeFilters() {
  render();
  try {
    const url = filtersToURL(window.location.href, status.value, query.value);
    if (url !== window.location.href) window.history.replaceState(window.history.state, '', url);
    filterHelp.textContent = shareHint;
  } catch {
    filterHelp.textContent = 'Filtros aplicados. Este navegador não permitiu atualizar o endereço.';
  }
}

status.addEventListener('change', changeFilters);
query.addEventListener('input', changeFilters);
clear.addEventListener('click', () => { status.value = 'all'; query.value = ''; changeFilters(); });

try {
  const response = await fetch('./data.json');
  if (!response.ok) throw new Error('load_failed');
  features = validateFeatures(await response.json());
  for (const control of [status, query, clear]) control.disabled = false;
  render();
} catch {
  results.replaceChildren();
  message.textContent = 'Não foi possível carregar as entregas. Recarregue a página.';
}

try {
  const response = await fetch('./manifest.json');
  if (!response.ok) throw new Error('manifest_unavailable');
  const manifest = await response.json();
  if (manifest.schema_version !== 1 || typeof manifest.revision !== 'string' ||
      !/^[a-f0-9]{40}$/.test(manifest.revision)) throw new Error('invalid_manifest');
  document.querySelector('#release').textContent = `Revisão publicada: ${manifest.revision.slice(0, 12)}`;
} catch {
  document.querySelector('#release').textContent = 'Prévia local; versão publicada não consultada.';
}
