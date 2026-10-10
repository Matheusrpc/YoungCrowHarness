# Exceções da fixture nas anotações do CI

Frente: diagnóstico do CI Windows. Base: `35fe0f9dd0c86e6c60570b63c4be680e322097c8`.

## Problema e mudança

O auxiliar `EgressTests.inherited` publicava os estados do supervisor somente depois
de encerrar o contexto da pasta temporária. Uma exceção no preparo, em `supervise`
ou nessa limpeza encerrava o teste antes da anotação. A API do GitHub mostrava
apenas o identificador do caso falho; o traceback permanecia no log separado.

O auxiliar agora captura essas exceções e publica `fixture.reason`, com a última
etapa alcançada, e `fixture.failure`, limitado às categorias aceitas por
`annotate_case`. Categoria desconhecida vira `other`. Quando disponível, o resultado
do supervisor passa pelo filtro existente. Nenhuma mensagem, caminho, traceback,
identidade de processo ou conteúdo de stdout/stderr entra na anotação.

A exceção continua sendo propagada. Uma falha de I/O ao imprimir a anotação também
preserva a exceção da fixture. A etapa indica progresso, não causa: uma exceção de
limpeza durante a saída do contexto pode substituir uma exceção anterior. O log
completo ainda é necessário para distinguir esse caso.

Somente `tests/test_mission_egress.py` e `tests/ci_unittest.py` mudam comportamento.
Prazos, asserts existentes, workflow, fontes do executor, reservas e perfis permanecem.

## Validação

A regressão inicialmente falhou em quatro subcasos por ausência de anotação. Após
o ajuste, cobre preparo, supervisão, limpeza e nome de exceção privado, com Actions
ativado e desativado. Verifica a mesma instância da exceção e ausência de conteúdo
privado. A revisão independente identificou o risco de `BrokenPipeError` substituir
a exceção original; a segunda regressão demonstrou essa falha e passou após a correção.

Na versão final, 26 testes focados passaram em 12,731 s. A suíte ampla iniciada
antes da proteção final contra falha de I/O concluiu 679 casos em 460,642 s:
659 aprovados e 20 pulados. Essa rodada não é uma prova da suíte inteira nos bytes
finais; os dois arquivos alterados foram revalidados pelos 26 casos focados.

Resultados, comandos e hashes estão na
[medição](../medicoes/2026-10-10-ci-fixture-diagnostics.json).
Revisão somente leitura por `review_queue_dependency_boundary`, sem achados pendentes.

O CI da base `35fe0f9` passou nos oito jobs de push/PR. A falha do commit anterior
`136469e` continua sem causa identificada; este ajuste não afirma corrigi-la e não
recupera retroativamente suas anotações. Em futuras falhas desse caminho no CI, a
anotação emitida poderá ser consultada pela API; falhas de escrita podem impedir
sua publicação. Nenhuma chamada de modelo ou ciclo Docker realizado.

## English overview

Egress fixture exceptions previously escaped before supervisor diagnostics were
annotated. The test helper now reports the last stage reached and an allowlisted
error category, plus filtered supervisor results when available. Private exception
text, paths and output remain excluded. The fixture exception is re-raised even if
annotation output fails with an I/O error. A stage is not a root-cause diagnosis.

Regression checks cover setup, supervision, cleanup, private exception names,
non-Actions runs and broken annotation output. Only test diagnostics changed;
product code, deadlines and native execution gates remain intact. The historical
Windows failure is still unexplained. Full logs may still be required. All 26
focused checks passed on the final code. The broader run started before the last
I/O-error protection change: 659 passed and 20 skipped, not a full final-code run.

ATRASO: CI deste incremento pendente | causa histórica e aceite nativo pendentes.
