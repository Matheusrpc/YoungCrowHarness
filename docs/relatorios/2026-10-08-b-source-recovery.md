# Recuperação dos fontes de B

Frente: YC-203.8, transferência privada e inspeção estática.

Seis arquivos recebidos em 8 de outubro de 2026 correspondem, byte por byte, aos
SHA-256 registrados nas medições de captura, integração e diagnóstico da prova corrigida.
A cópia privada conserva os nomes e a pasta `corrected-egress-proof`. Nenhum conteúdo
bruto de recibo foi publicado. [Medição](../medicoes/2026-10-08-b-source-recovery.json).

## Verificação realizada

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
do Windows. Os 11 testes de captura e 15 de integração foram identificados por análise
estática; **zero testes originais executados nesta recuperação**.

## Dependências diretas ausentes

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
também leem o cliente e os dois snapshots da raiz. A lista cobre dependências diretas
visíveis, sem garantir que os imports e manifestos ainda ausentes não referenciem
outros arquivos. Os JSON públicos de medição não substituem os snapshots privados.

## Limites e próxima ação

O coletor reconhece uma recusa Windows específica dentro da janela de B. Ele depende
do chamador para identidade, ausência do guard e callbacks de transporte/política.
Seu manifesto cobre somente B. O produto atual conserva código 126 como
`blocked_unattributed`; importar o coletor não converte esse estado em aceite.

Próximo passo: recuperar os módulos e recibos originais, inspecionar suas dependências
e executar a suíte offline quando o conjunto estiver completo. Não recriar provas
históricas nem reexecutar entradas nativas consumidas. O contrato local sbx 0.46.0
continua pendente, com 2/3 ciclos consumidos, perfis bloqueados e `proof_accepted=false`.

## English overview

All six recovered files match the historical SHA-256 records. Four Python files
parsed successfully and both receipt JSON files were valid. The source receipt's
excerpt hash matches the recovered event. This verifies transferred bytes and their
recorded link, not the full Windows log or native acceptance.

Static inspection found 26 test methods and 13 missing direct dependencies, listed
above. No original tests ran. Transitive imports and pinned manifests still need
inspection; public measurement JSON cannot replace private snapshots. Recover those
originals before offline replay. No Docker/sbx/model calls or new native cycles occurred.
The local vendor contract remains unresolved, with native profiles blocked.

ATRASO: reprodução offline aguardando dependências | YC-203 sem aceite nativo.
