# Verificação nativa dos adaptadores

Frente: 2A / YC-203. Continuação da [entrega dos adaptadores](2026-10-03-mission-runtime-adapters.md).
A inspeção do Claude foi corrigida. Os perfis de execução continuam bloqueados; nenhuma chamada
real de modelo foi enviada. [Medições](../medicoes/native-client-verification.json).

## Inspeção do Claude

O Claude Code 2.1.220 instalado no Windows usa um executável com dois hard links. A inspeção
aplicava a regra dos backups, que recusa arquivos com aliases, e retornava `unsupported_entry`
antes de consultar o cliente. O leitor de executáveis agora aceita esse formato sem escrever no
binário. Ele verifica caminho, identidade e conteúdo durante a leitura; o preflight repete o hash.
Uma alteração pelo outro link invalida a observação. As regras de adoção e backup permanecem iguais.

A inspeção real retornou o catálogo atual e autenticação de assinatura, com
`gaps: ["native_profile_unverified"]`. O catálogo e o login não comprovam isolamento.
O teste de regressão reproduziu a recusa anterior e passou após a correção; os 19 testes dos
contratos de cliente passaram no Windows em 4,968 segundos.

## Fronteira de imagens no Codex

O teste cria uma imagem PNG de um pixel fora da pasta de trabalho do cliente. Um fornecedor
simulado em `127.0.0.1` solicita `view_image` e verifica se recebe a imagem na requisição seguinte.
Ele usa um diretório temporário sem credenciais, o supervisor do harness e prazo de 30 segundos.
Não usa documentos pessoais nem envia requisições a um modelo real.

| Cliente no Windows | Resultado observado |
|---|---|
| Codex 0.146.0 | Ignora `tools.view_image=false`; a imagem fictícia chega ao fornecedor local |
| Codex 0.146.0 com `--strict-config` | Recusa a opção desconhecida antes da primeira requisição; não constitui prova de execução |
| Codex 0.160.0, também instalado | Avisa que ignora a opção; a imagem fictícia chega ao fornecedor local |

As duas versões concluíram a tentativa local com todos os processos próprios encerrados.
O resultado demonstra que esse perfil permite leitura de imagem fora do diretório de trabalho.
Não é uma avaliação geral da segurança do Codex: o harness exige uma prova sem acesso a ferramentas,
e o perfil anunciado não cumpre essa exigência nas versões medidas.

A [referência de configuração](https://learn.chatgpt.com/docs/config-file/config-reference)
lista `tools.view_image`, mas os executáveis testados rejeitam ou ignoram a opção. A evidência
local prevalece para esta matriz. O harness mantém `NATIVE_PROFILES` vazio.

Para repetir a prova a partir de um clone, informe o caminho absoluto do executável nativo:

```bash
python -B tests/probe_codex_image_boundary.py --executable CAMINHO_ABSOLUTO_DO_CODEX
python -B tests/probe_codex_image_boundary.py --executable CAMINHO_ABSOLUTO_DO_CODEX --strict-config
```

O código de saída `1` indica que a imagem chegou ao servidor; `2` indica que a prova não foi
conclusiva. Nenhum resultado desse script certifica o perfil completo. Não é executado pelo CI.

## Pendência para concluir 2A

No Claude, o modo seguro conserva políticas administrativas, inclusive personalizações que
podem executar comandos. Isso está descrito nas [variáveis de ambiente](https://code.claude.com/docs/en/env-vars)
e nas [políticas gerenciadas](https://code.claude.com/docs/en/managed-settings). `--bare` foi
avaliado pela ajuda do cliente, mas exige autenticação de API e não atende à prova por assinatura.

Antes das chamadas autenticadas, é necessário comprovar um perfil que recuse leitura/escrita
fora da fixture, rede não prevista e execução por hooks, MCPs ou agentes. Remover o bloqueio,
trocar a assinatura por API ou instalar um serviço de isolamento não faz parte desta correção.
YC-203 e 2A continuam parciais; 2B depende desse aceite.

## English

Claude inspection now accepts its installer's hard-linked executable and still detects changes
through either link. Adoption and backup guards remain unchanged. Native inspection returned
the current account catalog and subscription authentication; the execution profile is unverified.

The reproducible loopback probe showed that Codex 0.146.0 and 0.160.0 read a synthetic image
outside their working directory despite `tools.view_image=false`. Strict configuration rejects
the unknown option on 0.146.0 before any request. No live model calls were made, and all owned
process trees were reaped. The script reports failure or insufficient evidence, never approval.

Both native profiles remain blocked. Claude safe mode retains managed policy; bare mode requires
API authentication. Completing YC-203 requires an enforceable profile and bounded authenticated
proofs in both clients before the prioritized queue can run.
