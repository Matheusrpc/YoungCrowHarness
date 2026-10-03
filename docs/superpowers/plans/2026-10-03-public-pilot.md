# Piloto público Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Execução preservada: o executor desta sessão implementa; um revisor independente examina a frente ao final.

**Goal:** Publicar um quadro de entregas que permita reproduzir adoção, desenvolvimento, memória, publicação e retorno com o YoungCrowHarness.

**Architecture:** Uma aplicação estática vive em `examples/delivery-board/`, com dados fictícios identificados e vault público próprio. Os consumidores de prova usam o instalador e o controlador de retorno existentes. O GitHub Pages recebe somente um pacote de arquivos permitidos, com manifesto de revisão e hashes.

**Tech Stack:** HTML, CSS, módulos JavaScript, Node 24 e seu runner nativo, Python e bibliotecas padrão já usadas pelo harness, GitHub Actions/Pages.

**Spec:** [Desenho aprovado](../specs/2026-10-03-public-pilot-design.md).

Estado em 2026-10-03: plano aprovado pelo mantenedor; execução inline iniciada. O registro de implementação do exemplo e o relatório do piloto distinguem resultados comprovados de etapas pendentes.

## Global Constraints

- “Node 24 executa testes pelo runner nativo; não se acrescenta dependência de Node ao instalador do harness.”
- “O gerador do pacote usa biblioteca padrão e uma lista explícita de arquivos permitidos.”
- “O quadro usa dados fictícios identificados como demonstração.”
- “README e guia devem acompanhar as entregas em PT/EN, preservando o design atual.”
- “Fontes ingeridas ficam locais até revisão.”
- “Texto dos dados é inserido como texto, sem interpretar HTML.”
- “Links externos aceitam apenas destinos HTTPS revisados; esquemas executáveis e caminhos privados são recusados na preparação do pacote.”
- “Controles precisam de rótulos, foco visível e navegação por teclado; o estado não depende só de cor.”
- “O repositório do mantenedor não é alvo de restauração.”
- “A restauração do diretório não reverte publicações, perfis globais ou dados de serviços externos.”
- “O resumo da feature será conciliado explicitamente com cada execução concluída.”
- “MCP externo não é requisito desse exemplo”; “Graphify é opcional, sobre seleção explícita; claude-mem segue fora deste piloto.”
- Clientes: “até uma sessão nova de cada cliente, 300 segundos e 24 ferramentas por sessão, sem API adicional.” Declarar o limite novamente imediatamente antes da primeira chamada; qualquer repetição precisa de novo limite explícito e preserva a tentativa anterior.
- “Revisão independente usa o mecanismo de subagente da sessão, com um único escritor no checkout.”
- Usar karpathy, ponytail e humanizer. Preservar o autor humano dos commits, arquivos alheios e proteções da main.

## Review Focus

1. Estado combinado com termo sem correspondência: mostrar vazio, manter filtros legíveis e permitir limpar. Teste da Task 1 e observação da Task 2.
2. Título com marcação ou link disfarçado: renderizar título literalmente e recusar destino fora da lista revisada. Teste da Task 1 e prova de navegador da Task 2.
3. Arquivo privado ao lado da aplicação ou destino de build já existente: nenhum arquivo extra entra no pacote; destino existente é recusado sem alteração. Teste da Task 3.
4. Adoção de Git com alterações preparadas e não preparadas e instruções próprias: preservar tudo antes e depois do retorno; a cópia recuperável contém a entrega do trial. Prova da Task 4.
5. Resumo antigo que contradiz a execução mais recente ou deploy sem observação externa: o registro mantém o estado comprovado e a pendência. Reconciliação da Task 5 e verificação da Task 6.

## Mapa de arquivos e sequência

Cada task inclui atualização de `README.md`, `docs/USAGE.md` e `examples/delivery-board/README.md` conforme o comportamento verificado. Links da demonstração ficam marcados como pendentes até a Task 6. Os assets e os diagramas existentes são preservados.

| Unidade | Arquivos | Responsabilidade |
|---|---|---|
| Dados e consulta | `examples/delivery-board/model.mjs`, `data.json`, `tests/model.test.mjs` | Validar os dados revisados e selecionar features |
| Página | `examples/delivery-board/index.html`, `style.css`, `app.mjs` | Controles, estados visuais, detalhes e links públicos |
| Pacote | `examples/delivery-board/package.mjs`, `tests/package.test.mjs` | Copiar lista permitida e gerar manifesto |
| Memória pública | `examples/delivery-board/vault/` | Perfil, entrevista, decisões, feature, integração, capacidades e operação |
| Adoção real | `tests/smoke_adoption.py`, `tests/smoke_public_pilot.py` | Reusar comparação/restauração já existentes com a aplicação real |
| Validação e deploy | `.github/workflows/test.yml`, `.github/workflows/pilot-pages.yml` | Checks em PR e publicação da revisão aprovada |
| Roteiro | `examples/delivery-board/README.md`, `README.md`, `docs/USAGE.md`, `docs/PROCESS.md` | Passo a passo PT/EN, limites e acesso às provas |
| Evidências | `docs/relatorios/2026-10-03-public-pilot.md`, `docs/medicoes/2026-10-03-public-pilot.json` | Resultados sanitizados e matriz P01 a P09 |

Os scripts de produção do harness e o manifesto do instalador não precisam mudar. As pequenas extensões de `smoke_adoption.py` ficam no ensaio, não no controlador de retorno. Não criar um segundo instalador, um orquestrador de agentes ou um framework de testes.

Antes da Task 1, ler spec e plano, confirmar checkout exclusivo, base e arquivos alheios. Reutilizar a cópia isolada atual. Registrar andamento privado em `.superpowers/sdd/2026-10-03-public-pilot/progress.md`; não criar outro checkout apenas por causa do nome da branch. Usar `using-git-worktrees` conforme `executing-plans` e respeitar essa reutilização.

### Task 1: dados, seleção e memória pública do exemplo

**Files:** criar `examples/delivery-board/model.mjs`, `data.json`, `tests/model.test.mjs`, `README.md` e o vault descrito abaixo; modificar os blocos de estado atual de `README.md`, o link do piloto em `docs/USAGE.md` e a regra privada em `.gitignore`.

**Interfaces:**

- `validateFeatures(raw: unknown): Feature[]`; rejeita entrada inválida com `Error('invalid_features')` e não altera a entrada.
- `selectFeatures(features: Feature[], status = 'all', query = ''): Feature[]`; preserva a ordem, combina estado e termo do título/resumo, ignora caixa e espaços nas bordas.
- `Feature = {id: string, title: string, summary: string, status: 'planned'|'development'|'production', acceptance: string[], evidence: string[]}`. O estado pertence ao cenário fictício.
- `EVIDENCE_URLS` é uma constante com as URLs HTTPS públicas exatas dos três destinos: `vault/features/delivery-board/index.md`, `vault/decisions/static-site.md` e `vault/operations/index.md`, sob `https://github.com/Matheusrpc/YoungCrowHarness/blob/main/examples/delivery-board/`.

- [x] Criar o teste abaixo antes do módulo. Acrescentar os casos de IDs repetidos, estado desconhecido, chave inesperada, array vazio válido e cada link inválido listado.

```javascript
import test from 'node:test';
import assert from 'node:assert/strict';
import {validateFeatures, selectFeatures, EVIDENCE_URLS} from '../model.mjs';

const sample = [
  {id:'list', title:'Listar entregas', summary:'Ver critérios', status:'production',
    acceptance:['Mostra critérios'], evidence:[EVIDENCE_URLS[0]]},
  {id:'filter', title:'Filtrar entregas', summary:'Escolher estado', status:'development',
    acceptance:['Limpar recupera a lista'], evidence:[EVIDENCE_URLS[1]]},
];
test('combina filtros, trata vazio e recupera lista sem mutação', () => {
  const before = structuredClone(sample);
  const features = validateFeatures(sample);
  assert.deepEqual(selectFeatures(features, 'development', ' FILTRAR '), [sample[1]]);
  assert.deepEqual(selectFeatures(features, 'production', 'Filtrar'), []);
  assert.deepEqual(selectFeatures(features), sample);
  assert.deepEqual(sample, before);
});
test('marcação permanece texto; destino precisa estar revisado', () => {
  const raw = structuredClone(sample);
  raw[0].title = '<img src=x onerror=alert(1)>';
  assert.equal(validateFeatures(raw)[0].title, raw[0].title);
  for (const value of ['javascript:alert(1)', 'file:///private', '/vault/local/note',
    'https://github.com.evil.invalid/note', EVIDENCE_URLS[0] + '?token=private']) {
    raw[0].evidence = [value];
    assert.throws(() => validateFeatures(raw), /invalid_features/);
  }
});
```

- [x] Rodar `node --test examples/delivery-board/tests/model.test.mjs`; confirmar que falha pela ausência do módulo. Guardar saída privada, sem registrar um número de testes ainda desconhecido.
- [x] Implementar validação pequena: array com até 100 features, chaves exatas do contrato, ID não vazio e único, textos não vazios de até 2.000 caracteres, listas de aceite/evidência com 1 a 20 entradas; cada evidência pertence a `EVIDENCE_URLS`. Usar o filtro abaixo após validar os dados na fronteira de carga.

```javascript
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
```

- [x] Gravar três itens fictícios em `data.json`: listar entregas (`production`), filtrar entregas (`development`) e exportar relatório (`planned`). Declarar que exportação é um dado do cenário, sem implementação ou botão que prometa essa função. O teste carrega também o JSON real e passa por `validateFeatures`.
- [x] Inicializar o vault do exemplo usando os helpers existentes, com o diretório do exemplo como `cwd`. Não instalar o harness dentro da pasta pública do exemplo.

```powershell
Push-Location examples/delivery-board
try {
  python ../../scripts/personalize.py init --mode new --run public-pilot
  python ../../scripts/personalize.py feature --slug delivery-board --run implementation
  python ../../scripts/integrations.py init --provider github --service pages --run public-pilot
} finally { Pop-Location }
```

- [x] Preencher os registros gerados com o contexto aprovado e os resultados reais. Usar `integrations.note(project_id, path, kind, title, parent, body, now)` para notas manuais e UUID estável por caminho. Gerar uma identidade própria do exemplo, diferente da raiz do harness. Acrescentar `vault/decisions/static-site.md` e `vault/capabilities/index.md`; fazer cada índice apontar de volta às suas notas.

| Nota | Conteúdo obrigatório |
|---|---|
| `vault/product/profile.md` | Público, problema, Node apenas no exemplo, paleta, papéis, aceite, limites e comandos |
| `vault/product/interviews/public-pilot.md` | Respostas confirmadas pelo mantenedor, origem/data, decisão pelo quadro e hipóteses ainda abertas |
| `vault/product/adoption.md` | Exemplo no repo e ensaios externos são contextos diferentes; nenhuma captura retroativa |
| `vault/features/delivery-board/index.md` | P01 a P09, links às entregas, decisão, integração, execuções, DEV e produção observados |
| `vault/features/delivery-board/delivery.md` | Listagem, filtro, pacote, consumidores, retomada e publicação em entregas verificáveis |
| `vault/features/delivery-board/runs/implementation.md` | Revisão inicial, comandos/resultados reais, capacidades efetivas, próximo passo |
| `vault/decisions/static-site.md` | Decisão do quadro estático, alternativas já discutidas e limitações |
| `vault/integrations/github/pages/` | Contrato, origem oficial, implementação, operação, execução, fonte revisada e links de volta |
| `vault/capabilities/index.md` | Skills necessárias versus lidas/usadas; MCP sem requisito; Graphify opcional e sem prova presumida |
| `vault/operations/index.md` | Publicação desconhecida até observação externa; procedimento de retorno |

- [x] Na integração pública, registrar apenas a URL oficial e a decisão própria revisada. A extração Docling já existe no vault privado do harness; conservar sua relação com a frente, sem copiar sua transcrição, caminhos ou recibos para este vault público. Não ingerir novamente sem mudança da fonte ou necessidade demonstrada.
- [x] Acrescentar `/examples/delivery-board/vault/local/` ao `.gitignore` antes de qualquer uso local do vault do exemplo. Conferir `git check-ignore -v examples/delivery-board/vault/local/probe.md`; isso verifica a regra sem criar ou publicar uma nota privada. A regra existente `/vault/local/` protege apenas o vault da raiz.
- [x] Rodar o teste Node e, com `cwd=examples/delivery-board`, `python ../../scripts/vault.py check --json`. Esperar código 0 e `issues: []`; ler também a nota de feature e conferir seu estado com a execução.
- [x] Documentar que listagem/filtro de dados têm prova local e que a página/produção ainda estão pendentes. Revisar a prosa com humanizer. Fazer commit por caminhos explícitos: `feat: definir dados e memoria do piloto publico`.

### Task 2: página acessível e prova do percurso no navegador

**Files:** criar `examples/delivery-board/index.html`, `style.css`, `app.mjs`; atualizar os três READMEs/guias da sequência e o run da feature. Copiar apenas `assets/gema-cobalto.svg` para `examples/delivery-board/gema-cobalto.svg`, preservando sua origem.

**Interfaces:** `app.mjs` importa o contrato da Task 1; carrega `./data.json`; usa `selectFeatures` nos eventos dos controles. Não exportar um framework de componentes. IDs: `status`, `query`, `clear`, `results`, `message`, `release`.

- [x] Escrever no run o roteiro esperado antes de implementar. Conferir que a ausência da página impede o percurso: abrir, listar três itens, combinar filtros, obter vazio, limpar e abrir a evidência pública. Essa observação é o primeiro teste de UI; não criar um teste que só procure strings no HTML.
- [x] Implementar HTML semântico com título, aviso permanente “Dados fictícios para demonstrar o processo”, rótulos de estado e busca, botão Limpar, lista de resultados e detalhe de critérios. Usar `<details><summary>` para os detalhes, controles nativos e região `aria-live="polite"` para contagem/vazio. Marcar o documento `lang="pt-BR"`.

```html
<label for="status">Estado da entrega</label>
<select id="status">
  <option value="all">Todos</option><option value="planned">Planejada</option>
  <option value="development">Em desenvolvimento</option>
  <option value="production">Em produção no cenário fictício</option>
</select>
<label for="query">Buscar entrega</label><input id="query" type="search">
<button id="clear" type="button">Limpar filtros</button>
<p id="message" role="status" aria-live="polite"></p>
<ul id="results"></ul>
<p id="release">Revisão da demonstração ainda não consultada.</p>
```

- [x] Renderizar por `createElement`, `textContent` e `replaceChildren`. Criar links somente após `validateFeatures`; mantê-los na mesma aba. HTTP não-2xx, JSON inválido e falha de rede devem mostrar “Não foi possível carregar as entregas. Recarregue a página.” e limpar a lista. Vazio deve dizer “Nenhuma entrega corresponde aos filtros.”, preservando os controles. Manter falha no manifesto separada da carga de dados.

```javascript
const response = await fetch('./data.json');
if (!response.ok) throw new Error('load_failed');
const features = validateFeatures(await response.json());
// Dentro da renderização de cada item:
const title = document.createElement('h2');
title.textContent = item.title;
```

- [x] Aplicar fundo `#17130f`, texto `#F3E7C6`, gema local, títulos serifados, corpo legível, largura máxima de leitura, bordas discretas e foco contrastante. Usar grid/flex com quebra em tela estreita; evitar altura fixa e estado transmitido apenas por cor. Sem biblioteca de UI, fonte externa ou rastreamento.

```css
:root { color-scheme: dark; background: #17130f; color: #F3E7C6; }
body { max-width: 72rem; margin: auto; padding: clamp(1rem, 4vw, 3rem); font: 1rem/1.6 system-ui; }
h1, h2, summary { font-family: Georgia, serif; }
input, select, button { font: inherit; max-width: 100%; }
:focus-visible { outline: 3px solid #F3E7C6; outline-offset: 4px; }
#results { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr)); gap: 1rem; padding: 0; list-style: none; }
```
- [x] Servir localmente por `python -m http.server 8765 --bind 127.0.0.1 --directory examples/delivery-board`, anotando PID próprio. No navegador verificar 1280px e 360px, Tab/Shift+Tab/Enter/Espaço, foco, detalhe, filtros e limpeza. Usar dados de ensaio privados para testar título com HTML literal e a resposta de erro; restaurar os bytes revisados antes do commit. Capturas locais devem distinguir prova visual de teste automatizado.
- [x] Encerrar servidor e navegador próprios em `finally`, medir zero processos próprios remanescentes, rodar teste Node e validação do vault. Não abrir navegador durante chamadas nativas de modelo.
- [x] Atualizar estado e instruções locais PT/EN; gravar comando/viewport/resultado no run sem chamar produção de verificada. Commit: `feat: demonstrar entregas e filtros no piloto`.

### Task 3: pacote público verificável e CI

**Files:** criar `examples/delivery-board/package.mjs`, `tests/package.test.mjs`; modificar `.github/workflows/test.yml`, README e guia; atualizar execução no vault.

**Interfaces:** `build(source: string, destination: string, revision: string): Promise<Manifest>`, exportado por `package.mjs`; CLI `node examples/delivery-board/package.mjs DESTINATION REVISION`. `Manifest = {schema_version: 1, revision: string, files: Record<string,string>}` usa SHA-256 de cada arquivo público, sem incluir o próprio manifesto.

`PUBLIC_FILES = ['index.html','style.css','app.mjs','model.mjs','data.json','gema-cobalto.svg']`. O resultado contém exatamente esses arquivos e `manifest.json`. O vault público é consultado pelo GitHub e não é enviado ao site. O gerador não copia diretórios recursivamente.

- [x] Escrever teste com diretório temporário e `node:assert/strict`, antes do gerador. Copiar somente os seis arquivos conhecidos da aplicação para uma fixture, acrescentar `.env`, `vault/local/private.md` e `unexpected.txt` e executar:

```javascript
const manifest = await build(source, destination, 'a'.repeat(40));
assert.equal(manifest.revision, 'a'.repeat(40));
assert.deepEqual((await readdir(destination)).sort(), [...PUBLIC_FILES, 'manifest.json'].sort());
for (const name of PUBLIC_FILES) {
  assert.equal(manifest.files[name], createHash('sha256')
    .update(await readFile(join(destination, name))).digest('hex'));
}
await assert.rejects(build(source, destination, 'b'.repeat(40)), /destination_exists/);
assert.equal(JSON.parse(await readFile(join(destination, 'manifest.json'), 'utf8')).revision,
  'a'.repeat(40));
```

Importar `readdir/readFile` de `node:fs/promises`, `join` de `node:path` e `createHash` de `node:crypto`. O teste importa `build, PUBLIC_FILES` do módulo. Usar `mkdtemp` e limpar apenas a fixture conhecida em `finally`.

- [x] Acrescentar casos com evidência inválida em `data.json`, revisão que não é SHA de 40 caracteres, arquivo ausente e symlink/hardlink no lugar de um arquivo permitido. Devem falhar antes da publicação. Onde symlink exigir privilégio inexistente no Windows, registrar skip explícito; Linux deve exercitá-lo. Garantir que título não vira HTML na página pela prova da Task 2.
- [x] Rodar `node --test examples/delivery-board/tests/package.test.mjs` e observar falha pelo gerador ausente. Implementar usando `lstat`, `readFile`, `mkdir` exclusivo e escrita de bytes. Conferir `isFile`, `!isSymbolicLink`, `nlink === 1` nos seis arquivos; ler/validar tudo antes de criar destino. Validar também a raiz de origem e recusar diretórios/arquivos ligados. Recusar destino dentro da origem e destino existente; não apagar diretório para repetir build.

```javascript
const manifest = {schema_version: 1, revision, files: {}};
for (const [name, bytes] of preparedFiles) {
  manifest.files[name] = createHash('sha256').update(bytes).digest('hex');
}
await mkdir(destination); // sem recursive: colisão não sobrescreve
for (const [name, bytes] of preparedFiles) await writeFile(join(destination, name), bytes, {flag:'wx'});
await writeFile(join(destination, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n', {flag:'wx'});
```

`preparedFiles` é o array local `[nome, Buffer][]` resultante da leitura validada. O CLI só chama `build` quando executado diretamente; importar em teste não escreve arquivos. Emitir erro curto, não conteúdos de dados privados. Falha de escrita pode deixar staging incompleto, mas deve retornar código não zero, impedindo upload.

- [x] Completar a leitura de `./manifest.json` na página. Mostrar a revisão como informação separada dos estados fictícios. Quando não existir no servidor de fontes, mostrar “Prévia local; versão publicada não consultada.”; não alterar os resultados dos filtros.
- [x] Acrescentar job `public-pilot` ao workflow de teste existente, com Node 24 e ações fixadas. Ele roda testes Node, valida o vault com `cwd` do exemplo e prepara um pacote sob `$RUNNER_TEMP/public-pilot`. Não instalar Node no job/instalador dos consumidores que não o exigem.

```yaml
  public-pilot:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262
      - uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020
        with:
          node-version: '24'
      - run: node --test examples/delivery-board/tests/*.test.mjs
      - run: python3 ../../scripts/vault.py check --json
        working-directory: examples/delivery-board
      - run: node examples/delivery-board/package.mjs "$RUNNER_TEMP/public-pilot" "$GITHUB_SHA"
```

- [x] Conferir os testes Node, o pacote real e a validação do vault. Atualizar o guia com build e limitação do manifesto: atesta conteúdo/revisão, não aprovação ou autenticação. Commit: `feat: validar pacote publico do piloto`.

### Task 4: projeto novo, migração e retorno usando a aplicação

**Files:** modificar `tests/smoke_adoption.py`; criar `tests/smoke_public_pilot.py`; atualizar exemplo/README/guia e a execução no vault. Acrescentar a prova ao job `public-pilot` e ao job Windows depois de verificar dependências.

**Interfaces:** preservar `smoke(root, client)` e a saída atual para todos os chamadores. Acrescentar apenas parâmetros opcionais de teste:

```python
def smoke(root, client, *, prepare_existing=None, exercise=None,
          cases=('absent', 'dirty-git', 'interrupted')):
    # Fluxo existente: ambiente isolado, fixtures e controlador real.
    # prepare_existing(project, case, env): depois de git init, antes do commit inicial.
    # exercise(project, case, env): depois do setup confirmado, antes da captura trial.
    # Restante: mesmas verificações de retorno e perfil global já existentes.
```

O comentário acima indica os dois pontos de extensão, sem reescrever o restante do smoke. Ambos retornam `None` ou lançam exceção; não recebem nem alteram a base privada. O novo CLI usa `cases=('absent','dirty-git')`. Smoke original conserva a prova de interrupção.

- [x] Escrever `tests/smoke_public_pilot.py` para chamar esses parâmetros ainda inexistentes e rodar numa raiz nova; confirmar falha de interface antes de modificar o smoke. Importar `smoke`, `run` e `write` de `smoke_adoption`; importar `fs` já usado pelo ensaio. Recusar raiz existente pelo mecanismo original.
- [x] Implementar os dois pontos de chamada antes das capturas correspondentes. Em `prepare_existing`, criar uma versão inicial pequena da aplicação que só lista os dados, README próprio e teste Node. Usar o módulo de dados da Task 1 e HTML/JS de listagem com `textContent`; preparar somente esses arquivos para o commit inicial do smoke, que continua criando suas mudanças preparadas/não preparadas depois desse commit. Manter `CLAUDE.md`, `.codex/config.toml`, `.env` sintético e diretório vazio já criados pelo smoke.

```python
# Inserir no ramo existente de smoke, depois de escrever .gitignore e antes de git add/commit:
if prepare_existing is not None:
    prepare_existing(project, case, env)
# Inserir depois de conferir receipt['state'] == 'installed', antes de escrever feature.txt:
if exercise is not None:
    exercise(project, case, env)
```
- [x] Em `exercise`, primeiro executar o personalizer instalado; depois copiar somente arquivos públicos e testes do exemplo para o consumidor. No caso existente, isso acrescenta o filtro à aplicação inicial. O consumidor novo recebe a primeira entrega. Registrar uma execução específica por modo, preservando UUIDs do consumidor e não copiando a identidade do vault público.

```python
mode = 'new' if case == 'absent' else 'existing'
run([sys.executable, '-B', str(project / 'scripts/personalize.py'),
     'init', '--mode', mode, '--run', 'public-pilot'], env=env, cwd=project)
run([sys.executable, '-B', str(project / 'scripts/personalize.py'),
     'feature', '--slug', 'delivery-board', '--run', 'first-delivery'], env=env, cwd=project)
# Após os arquivos do exemplo serem copiados e as notas preenchidas:
run([node, '--test', 'tests/model.test.mjs'], env=env, cwd=project)
run([sys.executable, '-B', 'scripts/vault.py', 'check', '--json'], env=env, cwd=project)
```

Resolver `node = shutil.which('node')` antes de chamar smoke e falhar claramente se ausente. Não copiar o gerador com caminhos de origem do repo para fingir que o consumidor executou o pacote. Conservar comandos reais e resultados no README e no run do consumidor. No modo existente, auditar os arquivos iniciais, acrescentar referências de personalização às instruções sem apagar o texto anterior e conferir sua preservação.

- [x] Medir o estado antes/depois pelo smoke: `fs.inspect_tree`, HEAD, symbolic-ref, diff preparado/não preparado, status Git e perfil global. A cópia de recuperação deve ser idêntica à captura do trial, incluindo aplicação e notas. No consumidor ausente, a raiz deve voltar a não existir. Comparação falha encerra a prova como pendente, conservando cópias para análise.
- [x] Escrever roteiro humano do exemplo com dois percursos PT/EN: selecionar pasta/backup privados, setup trial, conferir recibo, personalizer, inventário em migração, entrega, teste, memória, prévia de saída e confirmação do digest. Não orientar clonagem dentro da raiz nova antes da captura. Guardar runner fora do consumidor. O script automatiza confirmação somente nas fixtures criadas por ele.
- [x] Rodar em Linux no job do exemplo e em Windows pelo wrapper já existente. Na máquina atual usar pai privado permitido, caminho curto, mesmo volume e fora de qualquer Git. Exemplo da forma do comando no Windows:

```powershell
python -B tests/windows_fixture_runner.py tests/smoke_public_pilot.py --root "$env:TEMP/yc-pilot-new-run" --client both
```

`yc-pilot-new-run` precisa estar ausente; escolher nome novo em repetição, sem apagar evidência anterior. No CI usar `$RUNNER_TEMP/public-pilot-adoption` e, no Windows, `$env:RUNNER_TEMP/public-pilot-adoption`. Acrescentar `actions/setup-node` com o mesmo SHA/Node 24 ao job Windows. Manter os smokes de `claude`, `codex` e `both` existentes e executar o novo em `both`.
- [x] Gravar JSON sanitizado: modo, cliente, revisão do harness, checks, retorno, preservação do trial/perfil e `model_calls: 0`. Não publicar caminhos privados, conteúdo de backup ou presumir conversa nativa pelo setup. Commit: `test: comprovar piloto em adocao nova e existente`.

### Task 5: retomada real nos dois clientes e revisão independente

**Files:** atualizar vault público e `docs/relatorios/2026-10-03-public-pilot.md`, `docs/medicoes/2026-10-03-public-pilot.json`, README/guia. Evidências brutas e runners privados ficam em `.runtime/public-pilot-20261003/` e nunca entram no pacote.

**Interfaces:** respostas nativas em JSON com `project_id`, `feature_id`, `decision`, `development`, `production`, `evidence`, `next_action`, `capabilities_used`, `warnings`; cada item de `evidence` tem `path`, `note_id`, `sha256`. A saída é comparada com arquivos reais; autoafirmação de skill usada não basta.

- [ ] Conciliar o resumo da feature com as Tasks 1 a 4, incluindo a publicação ainda não observada. Conferir links de volta, IDs e datas. Rodar o validador do vault do exemplo e do harness. Ler decisão, última execução e operação e resolver contradições antes de chamar modelos.
- [ ] Preparar consumidores privados para leitura a partir do ensaio e copiar apenas o vault público revisado para um contexto de prova próprio, sem copiar `vault/local` do mantenedor. Manter explícito que esse contexto recupera a identidade do exemplo. Instalar/adaptar instruções e skills de leitura pelos mecanismos existentes; preservar os perfis globais. Confirmar versões e autenticação sem imprimir tokens. Não reutilizar as sessões ou orçamentos de provas anteriores.
- [ ] Registrar orçamento antes das chamadas: uma sessão Claude e uma Codex, cada uma até 300 segundos e 24 chamadas de ferramentas, assinatura atual e zero API adicional. Reusar o padrão de runner privado já comprovado, com marcador durável por cliente antes de disparar, captura de eventos, término de processos próprios e limpeza apenas de credenciais temporárias próprias em `finally`. Confirmar flags na ajuda local dos clientes; não inventar flags de limites. O supervisor interrompe ao atingir o limite e conserva tentativa parcial. Não retomar automaticamente uma sessão falha.
- [ ] Usar o mesmo pedido sem respostas fornecidas, em sessões novas e somente leitura:

```text
Recupere o piloto do quadro de entregas pelos índices do vault deste projeto.
Leia a skill retrieve-memory e siga os microíndices relevantes. Encontre a feature,
a decisão vigente, a execução mais recente, as evidências, o estado de desenvolvimento,
o estado comprovado de produção e a próxima ação. Confira UUIDs e hashes das notas
que sustentam a resposta. Não use esta conversa anterior, não ingira fontes, não
altere arquivos nem publique. Retorne JSON com project_id, feature_id, decision,
development, production, evidence (path, note_id, sha256), next_action,
capabilities_used e warnings. Conte apenas capacidades realmente usadas nesta sessão.
```

- [ ] Comparar resposta com notas e SHA-256, conferir nos eventos as leituras efetivas, e comparar snapshots do consumidor antes/depois. Hooks podem gerar recibos privados: registrar essa diferença autorizada separadamente; notas públicas e código devem ficar iguais. Esperar que o cliente declare produção pendente quando essa é a evidência disponível. Zero MCP externo é resultado válido; não declarar Graphify ou claude-mem usados.
- [ ] Registrar resultado por cliente, versões, duração, contagem de ferramentas, IDs/revisões recuperados, avisos e limitações. Não publicar eventos brutos. Um cliente que não recuperou a evidência deixa P06 pendente; não trocar a prova nativa por um mock.
- [ ] Pedir a um subagente independente somente leitura a revisão do diff completo e do aceite. Usar `requesting-code-review` e o modelo mais capaz exigido por `executing-plans`; fornecer base/revisão, spec, plano, saídas e limites. O revisor não corrige arquivos. O escritor resolve achados pertinentes e repete apenas checks afetados, preservando a identidade das provas nativas se as notas mudarem depois.
- [ ] Rodar suíte Python pertinente/completa antes do PR, testes Node e checagens de vault; preparar relatório com P01 a P07 e P09 no estado observado, P08 pendente. Commit: `docs: registrar provas e revisao do piloto publico`.

### Task 6: publicar a revisão aprovada e fechar a documentação

**Files:** criar `.github/workflows/pilot-pages.yml`; atualizar `README.md`, `docs/USAGE.md`, `docs/PROCESS.md`, README/vault do exemplo e relatórios/medição da Task 5.

**Interfaces:** workflow publica somente main; `manifest.json` identifica a revisão efetivamente empacotada. A observação externa compara hashes dos seis arquivos, revisão e resposta da página, além de exercitar o filtro no navegador. O estado de produção contém data UTC, URL efetiva retornada, revisão, run e observação.

- [ ] Revalidar a documentação oficial registrada na integração antes de habilitar Pages. Em 2026-10-03 foram conferidos por API os commits das ações: configure-pages v5 `983d7736d9b0ae728b81ab479565c72886d7745b`, upload-pages-artifact v4 `7b1f4a764d45c48632c6b24a0339c27f5614fb0b`, deploy-pages v4 `d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e`. A raiz já usa checkout `11d5960a326750d5838078e36cf38b85af677262`; não atualizar outras ações sem motivo.
- [ ] Criar workflow separado com `contents: read` por padrão; `build` faz testes, valida vault e empacota, e só envia o staging. `deploy` depende de `build`, usa environment `github-pages`, permissões `pages: write` e `id-token: write`. Não usar `pull_request_target`, permissões de deploy no workflow de PR ou upload da raiz.

```yaml
name: Public pilot Pages
on:
  workflow_dispatch:
  push:
    branches: [main]
    paths:
      - 'examples/delivery-board/index.html'
      - 'examples/delivery-board/style.css'
      - 'examples/delivery-board/app.mjs'
      - 'examples/delivery-board/model.mjs'
      - 'examples/delivery-board/data.json'
      - 'examples/delivery-board/gema-cobalto.svg'
      - 'examples/delivery-board/package.mjs'
      - '.github/workflows/pilot-pages.yml'
permissions:
  contents: read
concurrency:
  group: public-pilot-pages
  cancel-in-progress: false
jobs:
  build:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262
      - uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020
        with:
          node-version: '24'
      - run: node --test examples/delivery-board/tests/*.test.mjs
      - run: python3 ../../scripts/vault.py check --json
        working-directory: examples/delivery-board
      - uses: actions/configure-pages@983d7736d9b0ae728b81ab479565c72886d7745b
      - run: node examples/delivery-board/package.mjs "$RUNNER_TEMP/public-pilot" "$GITHUB_SHA"
      - uses: actions/upload-pages-artifact@7b1f4a764d45c48632c6b24a0339c27f5614fb0b
        with:
          path: ${{ runner.temp }}/public-pilot
  deploy:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e
```

- [ ] Incluir o workflow no diff da revisão independente antes de qualquer publicação; se criado depois da Task 5, pedir continuação ao mesmo revisor para esse diff. Criar PR com problema/resultado, aceite e testes reais, corpo por arquivo e autoria humana. Anexar o PR ao chat. Aguardar checks obrigatórios e `public-pilot`; não reduzir proteção para publicar.
- [ ] Conferir configuração atual de Pages e environment. Sob a autorização de publicação deste piloto, habilitar fonte GitHub Actions no repo existente se ainda ausente, seguindo a interface/API oficial verificada. Limitar environment à main e conferir HTTPS. Divergência, custo inesperado ou necessidade de privilégio novo deixa apenas publicação pendente; não contratar serviço. Não anunciar URL como disponível antes do deploy.
- [ ] Integrar normalmente pela main protegida; acompanhar run de deploy com intervalos, sem consulta incessante. Capturar `page_url` real. Na URL pública, solicitar manifesto e cada arquivo com timeout e conferir SHA/revisão contra o artefato aprovado. Exercitar filtros, vazio, limpeza, teclado e viewport estreita na página publicada. Encerrar todos os processos próprios do ensaio. Falha mantém P08 pendente.
- [ ] Retorno: quando existir release anterior comprovada, repetir o run de publicação daquela revisão aprovada, reconstruindo a partir do mesmo SHA, e observar novamente URL/manifesto; não fazer force push. No primeiro deploy, se não houver versão anterior e a falha exigir retirar a demonstração, despublicar pelo mecanismo oficial do Pages e registrar o resultado. Distinguir esse retorno de publicação do retorno do consumidor da Task 4.
- [ ] Atualizar relatório, JSON e operação com resultados observados; conciliar feature e integração. Acrescentar ao README e ao guia PT/EN URL da demo, roteiro novo/migração/saída, requisitos e limitações. Em `docs/PROCESS.md`, ligar a etapa de piloto ao roteiro e aos fluxos já existentes, preservando as caixas de processo e os assets. Usar humanizer.
- [ ] Publicar as notas finais em um PR de documentação, se já estiverem após o merge da aplicação. Os filtros de caminhos do deploy evitam publicar de novo por mudar apenas relato/vault; a revisão publicada continua sendo um ancestral aprovado da main. Revalidar links e checks pertinentes, integrar normalmente e conferir main remota. O manifesto do site deve corresponder à revisão aprovada que gerou seus arquivos, não necessariamente a um commit posterior que só relata a prova.
- [ ] Encerrar somente com a tabela abaixo preenchida por resultados reais. Relatar o placar `ATRASO: main N | Pages N`; Pages compara os arquivos publicáveis da main aos hashes observados, para que uma edição de relato não vire falso atraso de aplicação.

## Cobertura e autocheck do plano

| Aceite | Entrega responsável | Evidência de saída |
|---|---|---|
| P01 | 1 e 2 | Teste de dados, combinação/vazio/limpeza, carga inválida e percurso real |
| P02 | 2 e 6 | Teclado, tela estreita, capturas e zero processos próprios remanescentes |
| P03 | 4 | Setup real, personalização nova e auditoria/preservação no existente |
| P04 | 4 | Árvore inicial, estado Git e trial recuperável comparados |
| P05 | 1, 5 e 6 | Vault com identidade própria, validador, resumo conciliado e estado observado |
| P06 | 5 | Uma sessão independente de cada cliente, notas/IDs/hashes recuperados e eventos conferidos |
| P07 | 3 e 6 | Testes de pacote, staging permitido e CI sem permissão de publicação em PR |
| P08 | 6 | Run, revisão aprovada, URL externa e hashes observados |
| P09 | Todas; conclusão em 6 | README/guia PT/EN, processos preservados, demo e receita ligados |

Autocheck antes de entregar o plano: comparar todos os requisitos com esta tabela; conferir contratos `Feature`, `Manifest` e callbacks; procurar instruções indefinidas; confirmar os cinco casos de Review Focus nos testes/provas correspondentes. Nenhum item marcado acima representa execução nesta etapa de planejamento.

Próxima entrega após este piloto: consolidar a primeira release, seus requisitos e o roteiro de adoção. Memória adicional e coordenação autônoma permanecem fora deste plano.
