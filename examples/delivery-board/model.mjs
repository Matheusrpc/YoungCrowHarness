const BASE = 'https://github.com/Matheusrpc/YoungCrowHarness/blob/main/examples/delivery-board/';
export const EVIDENCE_URLS = [
  'vault/features/delivery-board/index.md', 'vault/decisions/static-site.md',
  'vault/operations/index.md',
].map(path => BASE + path);
const KEYS = ['id', 'title', 'summary', 'status', 'acceptance', 'evidence'];
const text = value => typeof value === 'string' && value.trim().length > 0 && value.length <= 2000;
const list = value => Array.isArray(value) && value.length >= 1 && value.length <= 20;

export function validateFeatures(raw) {
  const seen = new Set();
  if (!Array.isArray(raw) || raw.length > 100) throw new Error('invalid_features');
  for (const item of raw) {
    if (!item || typeof item !== 'object' || Array.isArray(item) ||
        Object.keys(item).length !== KEYS.length || KEYS.some(key => !Object.hasOwn(item, key)) ||
        !text(item.id) || seen.has(item.id) || !text(item.title) || !text(item.summary) ||
        !['planned', 'development', 'production'].includes(item.status) ||
        !list(item.acceptance) || !item.acceptance.every(text) ||
        !list(item.evidence) || !item.evidence.every(url => EVIDENCE_URLS.includes(url))) {
      throw new Error('invalid_features');
    }
    seen.add(item.id);
  }
  return raw;
}

export function selectFeatures(features, status = 'all', query = '') {
  const needle = query.trim().toLocaleLowerCase('pt-BR');
  return features.filter(item =>
    (status === 'all' || item.status === status) &&
    `${item.title} ${item.summary}`.toLocaleLowerCase('pt-BR').includes(needle));
}
