import {validateFeatures, selectFeatures} from './model.mjs';

const status = document.querySelector('#status');
const query = document.querySelector('#query');
const clear = document.querySelector('#clear');
const results = document.querySelector('#results');
const message = document.querySelector('#message');
const labels = {planned: 'Planejada', development: 'Em desenvolvimento', production: 'Em produção · fictício'};
let features = [];

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

status.addEventListener('change', render);
query.addEventListener('input', render);
clear.addEventListener('click', () => { status.value = 'all'; query.value = ''; render(); });

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
