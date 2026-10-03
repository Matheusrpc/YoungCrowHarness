# Piloto público: evidências de implementação

Frente: quadro de entregas. Data: 2026-10-03. O código, o pacote e a adoção estão verificados.
A retomada passou no Codex. Claude permanece pendente por autenticação expirada; revisão e publicação
ainda não foram concluídas. O piloto completo não está fechado.

[Exemplo e roteiro](../../examples/delivery-board/README.md) · [Medições](../medicoes/2026-10-03-public-pilot.json)
· [Vault](../../examples/delivery-board/vault/index.md)

## Aceite observado

| Item | Evidência | Resultado |
|---|---|---|
| P01 | Modelo, dados, filtros combinados, vazio, limpeza e falhas de carga | Passou |
| P02 | Edge headless, 1280px/360px, teclado e foco; processos próprios encerrados | Passou localmente |
| P03 | Setup real both, personalizer e auditoria em consumidores novo/existente | Passou Windows/Linux |
| P04 | Árvores, Git, trabalho do trial e perfil global comparados | Passou Windows/Linux |
| P05 | Vault público com UUID próprio, índices e resumo conciliado | Passou; resumos corrigidos após a consulta nativa |
| P06 | Codex: nove UUIDs e SHA-256; Claude: OAuth expirado | Pendente no Claude |
| P07 | Oito testes Linux sem skips; pacote de seis arquivos e manifesto | Passou |
| P08 | Pages, revisão e observação externa | Pendente |
| P09 | README/guia PT/EN, receitas novo/migração/saída e processos ligados | Roteiro pronto; URL final pendente |

## Testes e limites

O [CI](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37121661946) passou na revisão de merge
f2610c15bfad52133d3921f770f7e03b18f0a7d1: 256 testes Python (11 skips), oito Node sem skips,
43 de armazenamento Windows (dois skips), nove de setup trial Windows e smokes nos perfis Claude,
Codex e both. As provas de adoção usaram helpers reais e copiaram a aplicação revisada; não chamaram modelos.
Os consumidores novo/existente têm UUIDs próprios, diferentes do vault público.

O baseline completo local do Windows foi interrompido por duração; ele não conta como sucesso.
As suítes pertinentes terminaram no CI Windows. Um teste local Node de symlink exigia privilégio ausente;
o mesmo teste passou no Linux. O percurso de navegador usou servidor Node privado para provocar falhas
sem alterar os dados públicos. A receita de prévia usa o servidor estático do Python.

## Recuperação de memória

Uma sessão nova do Codex 0.158.0-alpha.2.1 usou sete ferramentas e 189,994 segundos. O prompt não
forneceu UUIDs nem respostas. A leitura começou pelos índices e recuperou feature, decisão, execução,
desenvolvimento, produção não verificada e próxima ação. Nove UUIDs e hashes foram comparados com os
arquivos reais. Os eventos confirmam leitura de retrieve-memory, karpathy e ponytail. MCPs externos: zero.
Sem seleção de memória, o cliente usou os índices Markdown e declarou essa limitação.

A consulta leu o conteúdo preservado na revisão 3bc9f17644c87669902a5f8e163bde454ae8bc81.
Os hashes observados medem bytes do checkout Windows. O JSON também registra hashes dos blobs Git e
terminações de linha; a igualdade de conteúdo foi conferida normalizando apenas CRLF/LF.
O cliente identificou resumos antigos em delivery.md e Pages. Eles foram conciliados depois da prova,
sem substituir os hashes históricos. A sessão não reexecutou os testes de implementação nem consultou o CI remoto.

Claude Code 2.1.220 recebeu uma tentativa limitada, mas a assinatura recusou a autenticação:
“OAuth session expired and could not be refreshed”. Zero ferramentas e zero tokens de entrada/saída.
Uma verificação anterior de login já havia falhado sem enviar prompt. Os dois registros foram preservados.
A próxima tentativa depende de renovar o login e declarar novo limite. Não houve repetição automática.

Limite por cliente: uma sessão, 300 segundos e 24 ferramentas, assinatura existente e nenhuma API adicional.
Perfis temporários isolados; credenciais temporárias removidas, originais inalterados, processos encerrados
e nenhum arquivo do contexto de prova modificado. Graphify e claude-mem não foram usados neste piloto.

## Revisão e publicação

O workflow preparado publica somente main, com staging permitido e permissão de escrita apenas no job
de deploy. Revisão independente, configuração de Pages e observação externa permanecem pendentes.
A pendência de autenticação não será apresentada como falha ou sucesso de recuperação do Claude.
