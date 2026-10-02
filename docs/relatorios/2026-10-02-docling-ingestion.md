# Ingestão de fontes com Docling

Frente: documentos, mídia e retomada pelo vault. Implementação conforme o
[desenho](../superpowers/specs/2026-10-02-docling-ingestion-design.md) e o
[plano aprovado](../superpowers/plans/2026-10-02-docling-ingestion.md).

## Arquitetura entregue

`ingest-source` é a instrução comum de Claude Code e Codex. O hook `UserPromptSubmit` registra
referências textuais e orienta o agente a consultá-la. A conversão ocorre pelo comando local,
fora do hook, com recibo persistido, prazo e identificação de fonte/revisão/tentativa.

O vault tem um índice compartilhado e um índice local. Fontes pendentes também têm microíndice;
fontes convertidas acrescentam Markdown, imagens e relações com evidência. Originais, ambientes e
recibos ficam em `.operacao-local/docling/`; notas privadas ficam em `vault/local/`. Ambos são
protegidos pelo ignore antes da escrita. O comando não adiciona arquivos ao Git.

`prepare-review` cria uma cópia privada. `review-status` calcula o digest de texto e imagens;
`promote` exige o mesmo digest e valida os vínculos antes de copiar para `vault/sources/`.
O digest verifica integridade. A autorização humana continua necessária para a cópia exata.

O instalador preserva notas, credenciais e configurações de clientes/MCPs mesmo com `--force`.
Migrações com hooks existentes precisam mesclar `UserPromptSubmit`. Graphify e claude-mem continuam
sem adaptadores; nenhum material é enviado a esses serviços.

## Evidência observada

| Prova | Resultado | Registro |
|---|---|---|
| D01: Docling real, PDF/DOCX/HTML/PNG de página | Extração pronta; frase de controle preservada | [Documentos](../medicoes/2026-10-02-docling-documents.json) |
| D01: origem, revisão e interrupção real | Identidades preservadas, retomada após recuperar lock de dono encerrado | [Armazenamento](../medicoes/2026-10-02-docling-storage.json) |
| D02: relação, edição da cópia, promoção e clone compartilhado | Evidência ligada à feature/decisão; clone sem arquivos privados | [Revisão](../medicoes/2026-10-02-docling-review.json) |
| D03: PDF público por URL direta | Três páginas; repetição reutilizou a extração dos mesmos bytes | [URL](../medicoes/2026-10-02-docling-url.json) |
| D03: WAV e MP4 reais | Frase e três intervalos de fala; MP4 com três quadros amostrados | [Mídia](../medicoes/2026-10-02-docling-media.json) |
| D03: vídeo sem áudio e prazo reduzido | `partial`, com avisos e cobertura real, sem preencher o que faltou | Mesmo registro de mídia |
| D04: descoberta em clientes nativos | `ingest-source` nos dois clientes; `UserPromptSubmit` reconhecido no Codex | [Clientes](../medicoes/2026-10-02-docling-clients.json) |
| D04: conversa real no Codex | HTML convertido, evidência relacionada, anexo inacessível pendente | Mesmo registro de clientes |
| D04: nova conversa no Codex, sem histórico | Recuperou fonte/revisão, feature, citação, pendência e próxima ação pelo vault | Mesmo registro de clientes |
| D04: conversa real no Claude Code | Pendente: cliente local sem autenticação | Mesmo registro de clientes |

A primeira conversa real no Codex levou 235,53 segundos; a recuperação, 73,42 segundos. São tempos
observados de duas execuções, incluindo o modelo e as ferramentas, não um benchmark. O teste usou
Codex `0.158.0-alpha.2.1`, já distribuído com o aplicativo, e a sessão ChatGPT existente, com teto de
gasto monetário adicional zero. O CLI `0.146.0` descobriu a configuração, mas recusou o modelo
configurado por exigir versão mais nova. Nenhuma instalação global foi alterada.

A descoberta também passou com Claude Code `2.1.220`, sem conversa de modelo ou conexão MCP.
Isso prova leitura das entradas nativas, não cumprimento do fluxo por esse modelo. Os comandos
dos hooks foram executados em testes com subdiretório e espaços no caminho, sem Git. A execução
automática após confiança no cliente e anexos binários não expostos pelo payload continuam fora
da cobertura real declarada. A entrada explícita pela skill permanece disponível.

Os testes de skill usam cenário de leitura com prazo, fonte prévia, HTML com instrução hostil,
vídeo inacessível e aprovação antiga invalidada por uma imagem alterada. O cenário inicial já
respeitou essas fronteiras de segurança. A lacuna era operacional: comando de pendência e campos
de registro durável. O ensaio com `ingest-source`, `personalizer` e `integrate-from-docs` encontrou
os comandos e propôs o registro com IDs, evidências, capacidades usadas e próxima ação. Ele não
foi apresentado como uma conversão real; essa prova veio depois na conversa nativa do Codex.

## Limites e decisões de implementação

- Documentos e mídia usam ambientes separados. A falha de instalação de mídia não altera o
  ambiente documental; o custo é mais espaço em disco.
- Whisper Base roda localmente em CPU. Diarização fica desativada. No Windows, o extra opcional
  de vídeo exigia compilação C++ para diarização; o pipeline do fornecedor já está no pacote base
  e foi demonstrado sem esse extra. Nos outros sistemas o extra permanece declarado.
- OCR não garante fidelidade: uma imagem de faixa larga reordenou palavras. A prova positiva usou
  uma imagem de página; a limitação da faixa foi mantida no registro.
- URLs têm validação por conexão, limite de bytes, tempo e redirecionamentos. Links assinados
  renovados precisam do `source_id` anterior para manter identidade; o localizador persistido
  remove query e fragmento. Exceções de rede privada exigem configuração local explícita.
- A memória cresce em arquivos e índices. O validador verifica navegação, não a veracidade da
  evidência nem recuperação semântica ilimitada. Material local exige backup privado.
- Proteções de links, caminhos e ignore não substituem isolamento do sistema operacional contra
  um processo local malicioso concorrente. O projeto mantém um escritor por checkout.

## Decisões de execução

Foi reutilizado o checkout isolado que já estava dedicado à frente. Os commits das tarefas 1–6
foram preservados. A execução teve um escritor e revisão final independente de toda a branch,
com gates por tarefa. Os títulos do plano foram normalizados para `Task` por compatibilidade com
o helper de acompanhamento; seu conteúdo foi mantido.

O diagrama de arquitetura foi atualizado junto com as entregas verificadas. `review-status` foi
acrescentado para calcular o digest após uma edição. `source_fetch` entrou no instalador junto
com seu primeiro consumidor. Pendências ganharam índice pelo caminho já usado para salvar
recibos, evitando um segundo armazenamento de estado. Os hooks localizam o script do harness
mais próximo a partir da pasta da sessão; Python 3 precisa estar no PATH do cliente.

README e guia de uso foram revisados com humanizer em PT/EN. O fluxo de fontes preserva a paleta,
tipografia e símbolos dos demais diagramas. Original, transcrição privada, cache e credenciais
não fazem parte das evidências versionadas.

The implementation keeps documents local by default, with stable source identities, evidence
relations and exact-copy review before sharing. Real Docling document/media tests and real Codex
ingestion/recovery passed. Claude native discovery passed; its live conversation proof remains
pending because the local client is not authenticated. Automatic attachment capture is not claimed.
