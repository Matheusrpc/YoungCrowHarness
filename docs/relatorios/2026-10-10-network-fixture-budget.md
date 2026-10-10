# Prazo do teste integrado de rede

Frente: correção do CI Windows. Base: `44cd90fc9e0afbaa8f6717f41962d7346aa4658e`.

O [job Windows do push](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38071148714/job/114268640307)
interrompeu a fixture v4 aos 15,031 s. O diário mostra A concluída aos 9,701 s,
B aos 14,410 s e o guard de A2 pronto aos 14,801 s. O supervisor externo usava
15 s, embora o plano compartilhasse 30 s entre as três fases. Não há evidência
para atribuir a pausa em A a uma causa específica ou afirmar deadlock.

`NetworkBindingTests.run_network` agora usa `manifest.agent_seconds` no supervisor,
30 s nesta fixture. O plano começa antes da admissão/supervisão e conserva seu
prazo absoluto. O controlador já reserva um segundo para encerramento. Nenhum
limite do produto, critério de resultado, repetição ou dependência foi alterado.

## Provas

Uma reprodução local inicia o controlador com `runpy` no mesmo processo, após
16 s de atraso controlado. O código anterior falhou com timeout aos 15,376 s e
árvore recolhida. Com o ajuste, a mesma prova concluiu em 18,223 s: A/B/A2 observadas,
30 eventos do diário, 21 eventos de rede, recuperação confirmada e árvore recolhida.
A reprodução demonstra o corte prematuro; não reproduz a causa da lentidão Windows.

Testes afetados: 28 de rede aprovados em 13,347 s; 12 de processos em 6,920 s,
dez aprovados e dois exclusivos de Windows pulados. Incluem timeout, limite de
saída, contenção, recusa de efeito e recuperação. A suíte completa de 767 testes
foi executada na base; não foi repetida localmente para esta mudança apenas de
fixture. O novo CI executará suas verificações habituais.

Revisão independente sem achados materiais. README PT/EN, guia, backlog e handoff
atualizados. Código de produto, catálogo e permissões permanecem iguais.
[Medição e hashes](../medicoes/2026-10-10-network-fixture-budget.json).

No checkpoint da base, os seis checks Linux passaram. O job Windows do PR passou
a etapa inicial que falhou no push, mas a execução completa ainda estava em andamento.
Isso não encerra a confirmação Windows. Não houve chamada de modelo, Docker ou
cliente nativo; P06 e contador nativo 2/3 preservados. YC-205/206 continuam parciais.

## English overview

The integration fixture's 15-second outer watchdog could stop A2 before the existing
30-second plan expired. It now uses the manifest's budget while retaining the same
absolute product deadline and result assertions. A controlled delayed-controller
probe failed before the change and passed afterwards. Network/process checks passed
locally; Windows CI confirmation remains pending. No native acceptance is implied.

ATRASO: GitHub a conferir após commit | CI novo pendente | executor nativo pendente.
