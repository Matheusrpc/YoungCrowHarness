# Docling ingestion implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Converter fontes acessíveis em Markdown local, preservar sua origem e revisão e relacioná-las ao trabalho registrado no vault em Claude Code e Codex.

**Architecture:** Um comando local coordena armazenamento, aquisição e conversão. Docling roda em ambiente isolado; o núcleo do harness continua funcionando sem ele. Markdown é a fonte durável, com índices separados para conteúdo local e compartilhado; publicação exige revisão da cópia exata.

**Tech Stack:** Python 3.11+ no harness, biblioteca padrão e unittest; Docling 2.132.0 como versão candidata fixada para a prova de compatibilidade; FFmpeg no perfil de mídia; Bash, Markdown e entradas nativas dos clientes.

**Spec:** [Desenho aprovado de ingestão](../specs/2026-10-02-docling-ingestion-design.md). Ler também `AGENTS.md`, `CLAUDE.md` e os helpers existentes antes de executar.

Estado: plano aprovado pelo mantenedor para execução nativa em 2026-10-02 (UTC). Tarefas 1–6 verificadas; tarefa 7 implementada, com prova real do Codex e prova real do Claude ainda pendente de autenticação. A conclusão de cada tarefa exige evidência. Recomendação de execução: nativa nesta sessão, sequencial, com uma revisão independente ao final de cada entrega publicável.

## Global Constraints

- “O material deve permanecer local e só entrar no Git após revisão.”
- “Notas versionadas não recebem links para arquivos privados.”
- “O comando não executa `git add`, commit ou push.”
- “Links dentro de documentos ficam como referências; não iniciam uma coleta recursiva.”
- “100 MiB para documentos, 500 páginas, 500 MiB e 60 minutos para mídia, até 30 minutos por conversão e 200 quadros por vídeo.”
- “Não haverá envio automático a serviços remotos, instalação global, coleta de outros chats ou serviço permanente nesta entrega.”
- “Stubs não contam como prova da conversão nem da captura nos clientes.”
- Um escritor por checkout. Preservar guias e notas existentes, manter README e guia PT/EN atualizados em cada entrega e preservar os diagramas atuais. Autoria Git humana.
- Graphify, claude-mem, fontes autenticadas de plataformas de vídeo e chamadas ao vivo ficam fora da implementação deste plano.

## Review Focus

1. Projeto dentro de outro repositório Git ou regra de ignore negada: comprovar proteção efetiva antes de copiar conteúdo (tarefa 1).
2. Dois documentos com os mesmos bytes, mas contextos diferentes: reutilizar extração sem fundir identidade ou relações (tarefa 3).
3. Documento alterado entre leitura, revisão e publicação: conferir a revisão dos bytes processados e invalidar aprovação obsoleta (tarefas 3 e 4).
4. URL pública que redireciona ou resolve para endereço privado: validar cada conexão e redirecionamento, incluindo IPv6 (tarefa 5).
5. Cliente expõe o prompt, mas não o anexo: registrar a limitação sem sucesso fictício nem loop de hooks (tarefa 7).

## Arquivos e interfaces

| Arquivo | Responsabilidade |
|---|---|
| `scripts/documents.py` | Interface de linha de comando, seleção do ambiente Docling, coordenação e saídas sanitizadas |
| `scripts/document_store.py` | Proteção do armazenamento, identidade, revisões, índices, relações e cópias para revisão |
| `scripts/docling_worker.py` | Executar o SDK do fornecedor em processo isolado e produzir Markdown, JSON e ativos |
| `scripts/source_fetch.py` | Obter somente a URL solicitada com limites e validação de destino |
| `scripts/source_prompt.py` | Entrada curta dos hooks; guardar apenas referências e orientar a skill |
| `requirements/docling.txt`, `requirements/docling-media.txt` | Dependências diretas fixadas, separadas por perfil |
| `skills/ingest-source/SKILL.md` e entradas dos clientes | Procedimento compartilhado de ingestão, ligação das fontes e retomada |
| `tests/test_documents.py`, `tests/test_source_fetch.py`, `tests/test_source_prompt.py` | Regressões sem chamadas de modelo ou dependência de rede externa |
| `tests/smoke_docling.py` | Prova opt-in com o conversor real e material controlado |

Reutilizar `integrations.check_path`, `integrations.project_identity` e a serialização simples do frontmatter. Não alterar a origem das notas de integrações ao reutilizar o formato; as novas fontes usam `origin: youngcrow/docling`. O recibo operacional é JSON, enquanto notas e índices são Markdown. Não acrescentar banco, framework de filas ou dependência de vetores.

Contrato do recibo, versão 1: `project_id`, `source_id`, `revision`, `attempt_id`, `state`, `note_path`, `converter`, `coverage`, `warnings` e `next_action`. `converter` registra pacote, versão, perfil, modelos e opções. Estados: `pending`, `running`, `ready`, `partial`, `failed`, `unsupported`. `note_path` é nulo antes de existir uma extração. `coverage` só contém página/tempo realmente observado. Logs públicos recebem códigos e contagens, nunca conteúdo, URLs de acesso ou títulos privados.

O armazenamento gera UUIDs de projeto/fonte; a revisão de uma extração usa os bytes copiados, versão do conversor e opções normalizadas. Cada tentativa tem identidade própria. A revisão escolhida como atual permanece separada da última tentativa. Dados locais ficam em `vault/local/` e `.operacao-local/docling/`; cópias publicáveis ficam em `vault/sources/`.

## D01: documentos locais

### Task 1: armazenamento privado e duas entradas do vault

**Files:** criar `scripts/document_store.py` e `tests/test_documents.py`; modificar `.gitignore`, `scripts/vault.py`, `tests/test_vault.py`, `vault/index.md`, `setup.sh`, `tests/test_setup.py`, `README.md` e `docs/USAGE.md`.

**Interfaces:** `prepare_storage(root: Path) -> str` retorna o ID do projeto após verificar proteção e criar índices ausentes. `check(root)` em `vault.py` mantém sua assinatura e saída JSON; passa a aceitar `vault/local/index.md` como segunda raiz, se existir. Acrescentar o código `private_reference` para links da área compartilhada à local, sem revelar o destino em sua mensagem.

- [x] **Escrever regressões de privacidade antes da implementação.** Em `tests/test_documents.py`, criar `StorageTests.setUp` com `TemporaryDirectory`, `self.root` e Git inicializado; importar módulos por `sys.path.insert(0, str(ROOT / 'scripts'))`. Um primeiro teste:

```python
def test_private_storage_is_ignored(self):
    document_store.prepare_storage(self.root)
    for rel in ('vault/local/index.md', '.operacao-local/docling/receipt.json'):
        result = subprocess.run(['git', '-C', str(self.root), 'check-ignore', '--quiet', '--', rel])
        self.assertEqual(result.returncode, 0)
    self.assertEqual(vault.check(self.root)['issues'], [])
```

Adicionar casos em Git pai com destino aninhado, ignore negado, diretório local já rastreado, execução sem Git, junction/symlink/hardlink e arquivo no lugar de diretório. Para o caso rastreado, criar um arquivo fictício, executar `git add -f` somente na fixture e exigir recusa sem alteração de seus bytes.

- [x] **Reproduzir a ausência.** `python -m unittest discover -s tests -p test_documents.py -v` deve falhar por módulo ausente. Acrescentar em `VaultTests` uma raiz local que referencia a si mesma, um microíndice local navegável e um link público para ele; exigir aceitação dos dois primeiros e `private_reference` no terceiro. Manter os testes de ciclos, ilhas e nomes ambíguos.
- [x] **Implementar preflight e criação exclusiva.** Validar todas as rotas antes da escrita. Calcular caminhos relativos à raiz Git real, verificar `git ls-files` e `git check-ignore` e acrescentar regras efetivas sem apagar regras do usuário. O trecho central da verificação usa argumentos, nunca shell:

```python
tracked = subprocess.run(['git', '-C', str(root), 'ls-files', '-z', '--',
                          'vault/local', '.operacao-local/docling'],
                         check=True, capture_output=True).stdout
if tracked:
    raise ValueError('Private storage is already tracked.')
```

Criar o índice geral somente se ausente. Ele indica o caminho local como código; a raiz local referencia a si mesma e liga seus microíndices. O validador inicia navegação nas duas raízes existentes e mantém a detecção de ciclos dentro de cada cadeia. Links públicos para qualquer uma das duas áreas privadas falham; links locais para notas compartilhadas são aceitos.

- [x] **Instalar sem apagar conhecimento.** Acrescentar os arquivos necessários ao preflight e às fixtures `FILES` de setup; a área local nasce somente quando a ingestão for configurada. Acrescentar o ignore do harness e uma explicação PT/EN da diferença entre arquivos locais e versionados. Rodar os três testes relevantes de setup sobre criação, preservação e ignore, além de `test_documents.py` e `test_vault.py`.
- [x] **Commit por caminhos explícitos.** `git add -- scripts/document_store.py tests/test_documents.py .gitignore scripts/vault.py tests/test_vault.py vault/index.md setup.sh tests/test_setup.py README.md docs/USAGE.md`; commit `vault: separar fontes locais e compartilhadas` após revisão do diff.

### Task 2: ambiente Docling e conversor com diagnóstico

**Files:** criar `scripts/documents.py`, `scripts/docling_worker.py`, `requirements/docling.txt` e `tests/smoke_docling.py`; ampliar `tests/test_documents.py`, `setup.sh`, `tests/test_setup.py`, `README.md` e `docs/USAGE.md`.

**Interfaces:** `documents.py setup --profile documents`, `documents.py doctor --json`; `run_worker(source: Path, output: Path, runtime: Path, profile: str) -> dict` retorna o recibo de conversão. Worker recebe caminhos em um JSON temporário privado e retorna JSON sanitizado. Imports de Docling só ocorrem no worker. `setup` é uma ação explícita; `doctor` não instala nada.

- [x] **Escrever e rodar testes RED de ambiente ausente, worker interrompido e conteúdo privado em stderr.** Patch de `subprocess.run` deve emular `TimeoutExpired` e retorno não zero; exigir `failed` com código seguro, sem ecoar stderr. Usar `unittest.mock.patch`, sem opção de CLI que aceite comandos arbitrários.
- [x] **Implementar ambiente isolado e diagnóstico.** Fixar `docling==2.132.0` em `requirements/docling.txt`; criar venv sob `.operacao-local/docling/venv`, usando `Scripts/python.exe` no Windows e `bin/python` em Unix. Setup deve mostrar instalação/modelos previstos, guardar versões efetivamente resolvidas e nunca atualizar automaticamente um ambiente divergente. O `doctor` verifica Python, Docling e modelos configurados, sem ler segredos. Pré-carregar modelos no setup; conversão subsequente usa cache local e modo offline das bibliotecas aplicáveis.
- [x] **Implementar o SDK real e seu mapeamento de estados.** Usar a API da versão fixada:

```python
from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.document_converter import DocumentConverter

converter = DocumentConverter(allowed_formats=[InputFormat.PDF, InputFormat.DOCX,
                                               InputFormat.IMAGE, InputFormat.HTML])
result = converter.convert(source, raises_on_error=False,
                           max_num_pages=500, max_file_size=100 * 1024 * 1024)
state = {ConversionStatus.SUCCESS: 'ready',
         ConversionStatus.PARTIAL_SUCCESS: 'partial'}.get(result.status, 'failed')
```

Configurar os backends para não buscar recursos remotos ou locais referenciados no documento. Usar `artifacts_path` para modelos instalados. Exportar JSON e Markdown com ativos referenciados dentro da saída temporária; rejeitar destinos escapando dessa área. Converter sucesso com texto vazio em `partial`, com motivo registrado. Executar em processo filho com prazo de 1.800 segundos; encerrar também os filhos FFmpeg quando houver mídia. Não inserir um timeout menor silenciosamente nas plataformas suportadas.

- [x] **Demonstrar conversão real.** `tests/smoke_docling.py --profile documents --json` cria sob `.runtime/` HTML, PDF simples e DOCX com frase conhecida, usando biblioteca padrão, e PNG com a mesma frase via Pillow do ambiente Docling. A fixture PDF deve ter tabela xref válida; DOCX deve conter os componentes OOXML obrigatórios. Exigir a frase nos quatro resultados e registrar versões, tempo, status e caminhos de evidência sanitizados. Um stub não satisfaz este passo. Incompatibilidade da versão fixa exige registrar falha e resolver a versão antes de seguir.
- [x] **GREEN e documentação.** Rodar `test_documents.py`, o smoke real no ambiente isolado e os testes de instalação afetados. Documentar setup opt-in, custos locais de processamento/modelos, comando de diagnóstico e limitações observadas. Commit com os caminhos desta tarefa: `docling: adicionar conversor local isolado`.

### Task 3: ingestão, recibos, revisões e retomada

**Files:** ampliar `scripts/documents.py`, `scripts/document_store.py`, `tests/test_documents.py`, `tests/smoke_docling.py`, `README.md` e `docs/USAGE.md`.

**Interfaces:** `ingest(root: Path, source: Path, *, source_id: str | None = None, convert=run_worker) -> dict`; CLI `documents.py ingest ARQUIVO [--source-id UUID] --json`, `documents.py status [--source-id UUID] --json`. `record_pending(root: Path, reason: str) -> dict` cria apenas recibo opaco, reutilizado na tarefa 7. `status` não imprime conteúdo de documentos; IDs e estado bastam.

- [x] **Escrever testes RED para sucesso, repetição, falha e origem distinta.** Fake apenas do conversor; armazenamento e Git reais. Dentro de `IngestTests`, preparar `self.root` como na tarefa 1, criar `self.source` e definir `self.convert` para gravar Markdown e devolver um resultado controlado. Teste mínimo:

```python
def test_failed_update_keeps_previous_revision(self):
    first = documents.ingest(self.root, self.source, convert=self.convert)
    first_note_bytes = (self.root / first['note_path']).read_bytes()
    self.source.write_bytes(b'changed source')
    def failing_convert(*args):
        return {'state': 'failed', 'warnings': ['conversion_failed']}
    retry = documents.ingest(self.root, self.source,
                             source_id=first['source_id'], convert=failing_convert)
    self.assertEqual(retry['state'], 'failed')
    self.assertEqual((self.root / first['note_path']).read_bytes(), first_note_bytes)
```

Testar também uma segunda origem de bytes iguais com contexto distinto, reaproveitamento de extração, mudança de configuração, IDs de outro projeto e edição humana de uma nota. Nenhum desses casos apaga dados.

- [x] **Executar RED.** Rodar `test_documents.py` e conferir a falha da interface nova. Não instalar Docling na suíte de rotina.
- [x] **Implementar cópia limitada e revisão dos bytes copiados.** Validar arquivo regular e limites; copiar a origem indicada para temporário privado e calcular hash dessa cópia. Só então converter. Escrever extração com frontmatter, microíndice e recibo por renomeação atômica no mesmo volume; preparar as saídas e atualizar o índice por último. Uma interrupção deixa recibo retomável, sem tornar a revisão anterior inválida. Recusar concorrência com lock exclusivo por projeto, liberado em `finally`; lock abandonado exige diagnóstico de processo/revisão antes de remoção explícita.

```python
payload = json.dumps({'bytes_sha256': copied_sha256, 'converter': converter_info},
                     sort_keys=True, separators=(',', ':')).encode('utf-8')
revision = hashlib.sha256(payload).hexdigest()
```

`copied_sha256` é o digest do arquivo temporário e `converter_info` é o objeto registrado no recibo, com opções e modelos normalizados. Identidade não deriva desse hash. Reutilizar extração somente no mesmo projeto e perfil; preservar recebimentos e relações separados. Escapar títulos, neutralizar HTML ativo e tratar caminhos do Markdown extraído como dados, sem obedecer instruções do documento.

- [x] **GREEN e prova D01.** Exigir `vault.py check` limpo com as notas novas, dados locais ausentes de `git ls-files` e cópia original intacta. Rodar smoke real através de `ingest`, além do worker, e interromper uma conversão controlada para demonstrar retomada. Atualizar README e guia com comandos reais e estados. Commit `docling: persistir fontes e revisoes no vault`.

## D02: relações e publicação revisada

### Task 4: ligar conhecimento e promover somente cópias revisadas

**Files:** ampliar `scripts/document_store.py`, `scripts/documents.py`, `tests/test_documents.py`, `scripts/vault.py`, `tests/test_vault.py`, `README.md` e `docs/USAGE.md`; criar o índice compartilhado `vault/sources/index.md` quando houver promoção.

**Interfaces:** `relate(root, source_id, revision, target_id, relation, evidence) -> dict`; relações aceitas `supports`, `complements`, `contradicts`, `supersedes`, `used-in`. `prepare_review(root, source_id, revision) -> dict` gera `review_id` e diretório privado editável. `promote(root, review_id, approved_digest) -> dict` verifica o digest de todos os arquivos da cópia e retorna os caminhos públicos. CLI expõe `relate`, `prepare-review` e `promote` com esses campos; autorização humana continua sendo responsabilidade da sessão, não consequência de conhecer um hash.

- [x] **Escrever testes RED para vínculo e publicação.** Criar uma feature real com `personalize.py feature`, relacionar a fonte com evidência de trecho e verificar que a nota compartilhada fica intacta. Para promoção:

```python
review = document_store.prepare_review(root, source_id, revision)
digest = review['digest']
Path(review['directory'], 'index.md').write_text('changed', encoding='utf-8')
with self.assertRaises(ValueError):
    document_store.promote(root, review['review_id'], digest)
self.assertFalse((root / 'vault/sources').exists())
```

No teste, `root`, `source_id` e `revision` vêm da ingestão controlada da tarefa 3. Cobrir mudança de ativo, link privado, revisão parcial sem aviso, caminhos absolutos, URI `file:`, IDs duplicados e alteração na fonte após preparação. A cópia revisada é imutável após o digest aprovado, independentemente de atualizações posteriores do original.

- [x] **Implementar relações com evidência.** Resolver IDs por índice do próprio projeto; recusar alvo inexistente. Manter relações em notas locais, com links de revisão; atualizar microíndices sem duplicação. “Contradiz” registra hipótese quando não confirmado. Uma revisão substituída permanece navegável. Registrar uso de capacidades somente a partir de execução observada; a skill não preenche agentes ou MCPs por suposição.
- [x] **Implementar promoção seletiva.** Preparar cópia privada com IDs públicos novos, frontmatter e links internos reescritos; excluir proveniência privada por padrão. Preservar proveniência publicável revisada. Digest inclui nomes relativos e bytes de todos os arquivos da cópia, ordenados. Antes de escrever, validar a cópia como conjunto, o digest aprovado e ausência de links para as raízes privadas. Sanitização automática não substitui a revisão humana do texto e das imagens. Não executar operações Git; manter mapeamento original/cópia apenas local.

```python
entries = sorted((p.relative_to(review_dir).as_posix(), hashlib.sha256(p.read_bytes()).hexdigest())
                 for p in review_dir.rglob('*') if p.is_file())
digest = hashlib.sha256(json.dumps(entries, separators=(',', ':')).encode()).hexdigest()
```

Verificar tipos e limites dos caminhos antes desse cálculo; não seguir symlinks, junctions ou hardlinks. O próprio recibo de revisão fica fora da pasta cujo digest é calculado.

- [x] **GREEN e prova D02.** Demonstrar PDF → nota local → feature → decisão → cópia revisada, sem títulos privados no diff público. Conferir navegação local e clone contendo somente a área compartilhada. Documentar revisão de imagens, limites de anonimização e backup local. Commit `vault: relacionar fontes e revisar publicacao`.

## D03: aquisição e mídia

### Task 5: aquisição limitada de URLs

**Files:** criar `scripts/source_fetch.py` e `tests/test_source_fetch.py`; ampliar `scripts/documents.py`, `tests/test_documents.py`, `README.md` e `docs/USAGE.md`.

**Interfaces:** `fetch_source(url: str, destination: Path, *, max_bytes: int, timeout_seconds: int = 60, allowed_private_hosts: tuple[str, ...] = ()) -> dict`; retorno contém caminho local, tipo observado e localizador sem credenciais. `public_addresses(host: str, port: int) -> list[str]` resolve e recusa endereços não globais, inclusive IPv4 mapeado em IPv6. CLI `ingest URL` reutiliza toda persistência da tarefa 3.

- [x] **Escrever testes RED de destino.** Mock apenas de DNS e transporte; servidor HTTP real em loopback só mediante allowlist explícita da fixture. Exemplo:

```python
with patch('socket.getaddrinfo', return_value=[
    (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 443))]):
    with self.assertRaises(ValueError):
        source_fetch.public_addresses('public-looking.example', 443)
```

Adicionar redirecionamento público → privado, mudança de DNS, IPv6 link-local, userinfo, query assinada, resposta sem `Content-Length`, corpo maior que o informado, timeout, loop de redirects e nome sugerido com traversal. Exigir ausência de URL sensível nos logs.
- [x] **Implementar aquisição sem delegar URL ao conversor.** Aceitar HTTP(S), no máximo cinco redirecionamentos e 60 segundos totais de aquisição. Fazer stream de bytes com teto real; cabeçalhos e extensão não substituem detecção de tipo. Validar cada destino e conectar ao IP já aprovado, preservando Host/SNI e validação TLS. Usar `http.client`/`ssl` e resolução explícita; não herdar proxies/credenciais do ambiente. Não adicionar um downloader genérico de plataformas de vídeo. Guardar a URL de acesso apenas durante a chamada e remover credenciais/query do localizador persistido.
- [x] **GREEN e prova por URL.** Testes devem provar que uma segunda resolução não muda o IP da conexão. Rodar um download público controlado e sua conversão real; testar uma página sem arquivo acessível e exigir pendência, sem tratá-la como vídeo convertido. Atualizar limites e recuperação no guia. Commit `docling: adquirir fontes remotas com limites`.

### Task 6: áudio e vídeo com cobertura observável

**Files:** criar `requirements/docling-media.txt`; ampliar `scripts/docling_worker.py`, `scripts/documents.py`, `tests/test_documents.py`, `tests/smoke_docling.py`, `README.md` e `docs/USAGE.md`.

**Interfaces:** `setup --profile media` acrescenta ASR/vídeo ao ambiente isolado; `doctor` verifica FFmpeg e modelos. `run_worker(source, output, runtime, profile='media')` mantém o mesmo contrato, com cobertura de tempo e contagem de quadros observados.

- [x] **Escrever testes RED de falta de FFmpeg, limite de duração, status parcial e processo filho que excede o prazo.** O teste de status verifica que `PARTIAL_SUCCESS` nunca vira `ready`; o teste de timeout deve iniciar um processo controlado e confirmar que seus filhos também terminam.
- [x] **Fixar dependências de mídia após resolver o pacote da mesma versão candidata.** Usar `docling[asr]==2.132.0` e `docling-slim[format-video]==2.132.0`, conferindo a resolução antes de ativar o perfil. Preservar a instalação de documentos se a instalação de mídia falhar. Modelos e pacotes resolvidos ficam no diagnóstico local.
- [x] **Configurar os pipelines oficiais.** Áudio usa `AudioFormatOption` com `AsrPipeline`, modelo multilíngue `WHISPER_BASE` como perfil inicial de CPU; vídeo usa `VideoFormatOption` e quadros limitados. Não ativar diarização por padrão.

```python
from docling.datamodel.pipeline_options import VideoPipelineOptions
from docling.document_converter import VideoFormatOption
video = VideoFormatOption(pipeline_options=VideoPipelineOptions(
    max_sampled_frames=200, document_timeout=1800, enable_diarization=False))
```

Checar até 500 MiB e 3.600 segundos antes da conversão de mídia. Usar o FFmpeg/ffprobe configurado, sem shell, para obter duração e processar apenas arquivo local. Preservar tempos e quadros emitidos, registrar trechos ausentes e não inferir interpretação visual completa. Arquivo sem áudio deve ter estado compatível com a saída realmente obtida, com a ausência registrada.
- [x] **GREEN e prova D03.** Ampliar o smoke para aceitar gravação controlada curta e versão MP4 da mesma gravação, acompanhadas da frase esperada em um manifesto local. Confirmar transcrição, tempos, imagens, retorno parcial por prazo e encerramento dos processos. A prova real não pode ser substituída por silêncio sintético ou SDK mockado. Atualizar matriz de formatos, modelo, limites de qualidade e guia. Commit `docling: ingerir audio e video com cobertura registrada`.

## D04: Claude Code e Codex

### Task 7: skill compartilhada, hooks curtos e retomada real

**Files:** criar `scripts/source_prompt.py`, `tests/test_source_prompt.py`, `skills/ingest-source/SKILL.md`, `.claude/skills/ingest-source/SKILL.md`, `.agents/skills/ingest-source/SKILL.md`; modificar `.claude/settings.json`, `.codex/hooks.json`, `skills-lock.json`, `vault/capabilities/index.md`, `skills/personalizer/SKILL.md`, `skills/integrate-from-docs/SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `docs/CLAUDE.en.md`, `setup.sh`, `tests/test_setup.py`, `tests/smoke_clients.py`, `README.md`, `docs/USAGE.md` e `docs/PROCESS.md`.

**Interfaces:** `handle_prompt(payload: dict, root: Path) -> dict` retorna `hookSpecificOutput` com `UserPromptSubmit` e contexto curto. Não converte, instala, faz rede ou imprime o prompt. Guarda referências textuais sanitizadas somente depois do preflight da tarefa 1. Um evento repetido reutiliza o recibo por identidade de sessão/turno/referência disponível.

- [x] **Aplicar writing-skills e registrar um cenário de base antes da skill.** A tarefa de teste apresenta arquivo acessível, fonte prévia e feature existente. O comportamento exigido é recuperar a fonte, ingerir quando necessário, relacionar com evidência e informar pendências. Testar instruções hostis dentro do documento como dados, sem execução.
- [x] **Escrever testes RED de hook curto.** Cobrir payload vazio, prompt grande, referência repetida, texto com credenciais e anexo não exposto. Uma entrada sem referência não grava arquivos:

```python
before = set(root.rglob('*'))
result = source_prompt.handle_prompt({'prompt': 'continue', 'session_id': 'fixture'}, root)
self.assertEqual(set(root.rglob('*')), before)
self.assertNotIn('continue', json.dumps(result))
```

Usar `TemporaryDirectory` para `root`. Patch de rede e worker deve falhar se qualquer um for chamado pelo hook. Não copiar prompts inteiros; limitar payload de entrada a 1 MiB e retornar aviso seguro quando excedido. Não gerar novas tentativas recursivas por callbacks de Stop.
- [x] **Implementar skill e entrada compartilhada.** A skill lê os dois índices existentes, consulta a skill oficial da versão instalada de Docling e usa o comando do harness. Registra IDs/revisões, relações, uso real de capacidades e próxima ação. Se faltar runtime ou arquivo, cria pendência; setup ocorre somente no fluxo explicitamente solicitado. Personalizer e especialista em integrações passam a consultar as fontes locais relacionadas, sem enviar conteúdo a serviços externos ou promover arquivos por conta própria.
- [x] **Instalar hooks e entradas sem substituir configuração customizada.** Acrescentar `UserPromptSubmit` aos templates, mantendo os hooks de design; incluir variante Windows. Em migração, preservar arquivo existente e orientar uma mescla revisável. `--force` continua preservando conhecimento e credenciais. Atualizar allowlists de skills próprias e fixtures de instalação. Uma instrução de agente não deve ser descrita como garantia técnica de captura universal.
- [ ] **GREEN e descoberta nativa.** Rodar suíte completa e ampliar `smoke_clients.py` para reconhecer a skill e o novo evento; manter o isolamento de credenciais e a fixture de modelo em loopback. Isso verifica descoberta e configuração, não cumprimento do fluxo pelo agente.
- [ ] **Demonstrar D04 em sessões reais.** Em cada cliente, apresentar um arquivo controlado acessível e uma referência inacessível. Exigir conversão real no primeiro e pendência no segundo. Abrir nova sessão no mesmo projeto e recuperar fonte/revisão, feature relacionada, evidência e próxima ação. Registrar cliente/versão, tipos de entrada testados, comportamento observado e limitações. Seguir a autorização do operador e os limites de custo do ambiente; não iniciar chamada paga não coberta.
- [ ] **Documentar e publicar a entrega verificada.** Atualizar README PT/EN, os fluxos visíveis pertinentes e o guia para setup novo, migração, operação diária e publicação revisada. Salvar relatório e evidências leves em `docs/relatorios/` e `docs/medicoes/`; nenhum original real ou transcrição privada entra no commit. Commit `skills: integrar ingestao e retomada nos dois clientes` por caminhos explícitos.

## Fechamento de cada entrega

Executar os testes afetados; após passarem, rodar a suíte completa antes de publicação. Revisão independente somente leitura, correções com regressão pertinente e PR respeitando a proteção da main. A demonstração real deve acompanhar os testes unitários nos incrementos D01, D03 e D04. A atualização de um status no README depende dessa evidência.

```bash
python -m unittest discover -s tests -v
bash -n setup.sh
python scripts/vault.py check --json
git diff --check
```

O rollback de código usa revert do commit/PR. Não remover documentos locais como parte do rollback. Ambiente de conversão pode ser desativado preservando notas e originais; recibos devem indicar incompatibilidade ou conversão pendente. Memória externa permanece desconectada em todas as etapas deste plano.

## Cobertura da especificação

| Requisito | Tarefas |
|---|---|
| Privacidade, índices local/compartilhado e clones | 1, 4 |
| Conversão, diagnóstico, recursos locais e dados não confiáveis | 2, 3 |
| Identidade, revisão, falhas e retomada | 3 |
| Relações, evidência e publicação revisada | 4 |
| URLs e limites de aquisição | 5 |
| Áudio, vídeo, limites e cobertura | 6 |
| Captura, skills, personalizer e continuidade nos dois clientes | 7 |
| Documentação, design e estados verificáveis | Todas, com fluxo completo em 7 |
| Adaptadores de memória futuros | Contrato preservado; nenhuma sincronização implementada |
