# Recuperação dos fontes de B

Frente: YC-203.8, recuperação privada e reprodução offline.

**Os 26 testes de captura e integração passaram na cloud**, sem falhas, erros ou
skips, em 0,375 s. O ZIP de 1.050.342 bytes contém 635 arquivos, totalizando
5.493.727 bytes descompactados. Ele trouxe as 13 dependências que faltavam e as
transitivas necessárias à suíte selecionada. [Medição](../medicoes/2026-10-08-b-source-recovery.json).

O teste usou uma cópia privada dos fontes recebidos, sem alterá-los. Os 17 hashes
fixados efetivos do controlador integrado e os quatro recibos do manifesto de
restauração conferem. Os hashes dos 635 originais e das 635 cópias permaneceram
iguais depois da execução. Transporte, guard e efeitos nativos continuam simulados
pelos próprios testes; isso não conclui o aceite nativo de YC-203.8.

## Primeira transferência

Os seis arquivos recebidos inicialmente em 8 de outubro de 2026 correspondem aos
SHA-256 registrados nas medições de captura, integração e diagnóstico da prova corrigida.
A cópia privada conserva os nomes e a pasta `corrected-egress-proof`. Nenhum conteúdo
bruto de recibo foi publicado.

| Arquivo | Bytes | SHA-256 conferido |
|---|---:|---|
| `captured_egress.py` | 6721 | `cd4394082e8da687efeff9bd835169163a540385e80faaacec8dc06b8fb7531c` |
| `test_captured_egress.py` | 9315 | `6945516531eaa08b0bdb89c31f257f26b10919ec2a481311069af5b5ae55330c` |
| `integrated_egress.py` | 7508 | `3a5a6f365c3cef6dc18437b278c8a068b3eeb138aaf51467f7571918ac65b62b` |
| `test_integrated_egress.py` | 16664 | `7c226217284a76cd55b8a145493203446220d76636da132640cd915fa6d0d3a6` |
| `corrected-egress-proof/B-daemon-refusal.jsonl` | 488 | `e16a55e82f8105b22dee598cd4d5efbd0b7dabf05d5f880d5236d5e17433cb46` |
| `corrected-egress-proof/B-daemon-refusal-source.json` | 479 | `154d5f3270309f91c1e863c893325fa2207de04a68f861b8438d4a3afa06c6b6` |

`hashlib.sha256` conferiu os seis arquivos e as cópias preservadas. `ast.parse` leu
os quatro Python sem importar ou executar seu código; `json.loads` leu os dois recibos.
O campo `excerpt_sha256` do recibo de origem coincide com o hash do evento recebido.
Isso confirma a transferência e o vínculo registrado, sem verificar o log completo
do Windows. Nessa primeira transferência, os 11 testes de captura e 15 de integração
foram apenas identificados por análise estática. Sua execução ocorreu após o ZIP.

## Dependências recuperadas no ZIP

Caminhos relativos à pasta original `2026-10-04-isolated-executor`:

```text
exclusive_egress.py
corrected_egress.py
observed_egress.py
guardian_vm.py
hostname-cidr-client.py
hostname-cidr-proof.json
native-package-proof.json
corrected-egress-proof/control.json
corrected-egress-proof/B-diagnosis.json
corrected-egress-proof/restoration-verified.json
corrected-egress-proof/attempt.json
corrected-egress-proof/receipt.json
corrected-egress-proof/commands.jsonl
```

`test_captured_egress.py` lê controle e diagnóstico ao importar. Seu teste de preservação
lê o manifesto de restauração e cada recibo listado nele. `integrated_egress.py`
importa os quatro módulos antigos e incorpora `corrected_egress.PINNED`; os testes
também leem o cliente e os dois snapshots da raiz. Todos esses arquivos estão presentes.
A inspeção também resolveu os imports de `egress_guard.py`, `nested-docker-probe.json`
e os manifestos/recibos anteriores necessários aos testes. Os JSON públicos de medição
não foram usados como substitutos dos snapshots privados.

## Reprodução offline

Comando executado no checkout da cloud:

```text
python3 -I -B .runtime/recovered-b-20261008/bundle/run_offline.py
```

O runner privado carrega somente `test_captured_egress` e `test_integrated_egress`.
Python 3.12.14 no Linux usa `sys.path` explícito e `LOCALAPPDATA` apontado a uma pasta
descartável somente nesse processo, porque `guardian_vm.py` lê essa variável ao
importar. Não foi criado executável sbx. Cinco módulos públicos do commit `9b27c8a`
completam o runtime: `adoption_fs`, `adoption`, `document_store`, `integrations` e
`mission_process`; seus hashes estão na medição. Isso reproduz os testes dos fontes
privados com auxiliares atuais, sem alegar reprodução integral do Windows histórico.

Um audit hook instalado antes dos imports recusa eventos de subprocessos, execução
de programas, fork e sockets. Qualquer tentativa reprovaria o runner, mesmo se o
teste capturasse a exceção. A contagem observada foi zero. O log terminou em
`Ran 26 tests in 0.375s` e `OK`, com zero skips. Não houve Docker/sbx, modelos,
mutação de configuração nativa ou consumo de ciclo.

O ZIP, a cópia de trabalho, o runner e os recibos continuam em armazenamento privado.
O conversor de documentos registra ZIP como `unsupported_source`; a extração e a
leitura direta não são uma conversão Docling. A recuperação não requer instalar
esse runtime nem indexar o arquivo inteiro na memória.

## Limites e próxima ação

O coletor reconhece uma recusa Windows específica dentro da janela de B. Ele depende
do chamador para identidade, ausência do guard e callbacks de transporte/política.
Seu manifesto cobre somente B. O produto atual conserva código 126 como
`blocked_unattributed`; importar o coletor não converte esse estado em aceite.

Recuperação e reprodução estão concluídas. O próximo incremento nativo depende de
comprovar o contrato aplicável ao store local sbx 0.46.0: escrita condicionada do
setting completo e identidade/versão, remoção condicionada e revogação observável da
credencial. Os registros `contract-probe` recebidos tratam de descritor de kit; as
consultas de `policy-secret-diagnosis` não provam essas operações condicionais.

A revisão recomenda preservar o bloqueio atual. Portar o coletor antigo agora exigiria
adaptar seu protocolo de transporte sem um consumidor nativo validado. Os efeitos
antigos usam `settings set/unset` e remoção por placeholder, sem condição de versão;
não substituir por eles a interface atual `setting(key, target, *, expected)`.
Não repetir as pesquisas já encerradas nem criar outro roteiro experimental.

Depois do contrato: adaptador e recuperação, candidato exato, atribuição B no transporte
real e A/B/A2 nativo. Permanecem 2/3 ciclos consumidos, perfis bloqueados e
`proof_accepted=false`. Nenhuma operação histórica foi repetida.

## English overview

The private ZIP supplied all inputs needed by the 26 selected capture/integration
tests. All passed in 0.375 seconds with no failures, errors or skips. Seventeen effective
pins matched; all 635 original files and replay copies remained unchanged. The six
initial files still match their historical hashes, and the source receipt identifies
the recovered event by the same digest.

Replay used Linux Python 3.12.14, five current public helpers recorded by hash and
the original tests' mocks for transport, guard and native effects. An audit hook
rejected process/socket boundaries; no attempt occurred. This is offline replay,
not native A/B/A2 acceptance or an exact recreation of the historical Windows runtime.

The local sbx contract remains unresolved. Newly recovered kit descriptors and query
diagnostics do not establish conditional settings writes or versioned credential
removal/revocation. Preserve the existing blocked adapter; porting the old collector
would add an unverified protocol bridge. Next obtain the applicable local contract,
then complete adapter/recovery and attribution on the exact native candidate.

ATRASO: recuperação concluída | YC-203 aguardando contrato e aceite nativos.
