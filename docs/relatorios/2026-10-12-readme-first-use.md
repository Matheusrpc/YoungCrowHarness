# README: primeiro uso e estado publicado

Frente: documentação de entrada do YoungCrowHarness. Recorte da redução preparada na
auditoria, adaptado à main `d6c14c5034dbf6631d393242dd1ee85c785fd554` após os PRs #27 e #28.

O README passou de 811 para 323 linhas, redução de 60,2%. O primeiro uso aparece antes da
arquitetura. Mantém português e inglês, os 14 IDs explícitos de navegação e referências a todos
os 30 assets anteriores. Nenhum byte desses assets mudou. O guia de uso ganhou links de volta
ao início; detalhes operacionais, histórico técnico e provas permanecem nos documentos existentes.

A descrição acompanha a main: preparação de missões disponível; fila, avisos, diretórios por
PBI e pausa/retomada ainda indisponíveis nesta versão. U01 aparece publicado e verificado, com
link para os limites da prova externa. Handoff, tutorial e diagnóstico exclusivos da branch do
executor não entram como recursos instalados. Código do produto, leis e SVGs não foram alterados.

A revisão independente não encontrou bloqueadores. Pediu preservar a ressalva de que o setup
em macOS ainda não foi verificado; o texto final inclui essa informação nas duas línguas.
A redação em português passou pela leitura com `humanizer-ptbr`.

## Provas

- 211 links locais e âncoras conferidos, sem problemas. IDs e conjunto de assets comparados à
  base por leitura estruturada; os 30 arquivos visuais foram comparados por SHA-256.
- Vault: três notas, zero problemas. `git diff --check` passou.
- O GitHub renderizou o Markdown pela API. O HTML foi conferido num leitor CSS local em Chromium,
  com 1280 e 360 pixels: 47 imagens carregadas, quatro tabelas, três blocos de comandos, primeiro
  uso PT/EN alcançável e nenhum transbordamento horizontal da página ou erro JavaScript.
- Capturas: [celular, português](../medicoes/2026-10-12-readme-mobile.png) e
  [desktop, inglês](../medicoes/2026-10-12-readme-desktop.png). A prévia usa CSS local e IDs de
  fragmento normalizados; não representa a interface completa do GitHub.
- A política do navegador recusou a primeira prévia por `file:`. A conferência usou HTTP local,
  permitido pela política, sem alterá-la. Imagens externas passaram por HTTPS com TLS verificada.
  Navegador e servidor foram fechados; a medição de processos próprios terminou em zero.

[Medição e hashes](../medicoes/2026-10-12-readme-first-use.json).
A [main de base](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38263431350)
terminou seus quatro jobs com sucesso, incluindo Windows. Isso fecha a pendência de CI da main
registrada na entrega anterior. A revisão documental tem seu próprio CI; o estado final acompanha
o PR desta entrega. A suíte de código não foi repetida localmente para este recorte documental.

Retorno: reverter somente o PR documental por outro PR. Não há migração, mudança de configuração
de consumidores ou novo deploy Pages, cujos arquivos continuam iguais. Nenhuma chamada de modelo,
prova nativa, instalação de plugins ou ensaio Docker ocorreu. O PR #24 permanece separado.

**English.** The README now has 323 lines instead of 811, while keeping all 14 explicit anchors,
both languages and references to all 30 existing assets. It distinguishes published capabilities
from executor work and links to the verified public example. The review restored the macOS setup
limitation. Local link checks and desktop/mobile GFM previews passed; previews use local CSS.
The base main passed all four CI jobs, including Windows. This change only updates documentation;
its own CI and integration status are tracked in the delivery PR.

ATRASO: GitHub integração documental pendente neste checkpoint | CI da revisão pendente | Pages 0
