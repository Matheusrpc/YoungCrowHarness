# Adoção reversível: revisão do plano

Frente: adoção reversível. O mantenedor aprovou o [desenho](../superpowers/specs/2026-10-02-reversible-adoption-design.md)
em 2026-10-02. O [plano escrito](../superpowers/plans/2026-10-02-reversible-adoption.md) segue para revisão;
esta entrega não implementa nem executa restauração.

A revisão do plano confrontou os critérios de aceite com cinco tarefas e seus testes previstos.
Corrigiu quatro pontos antes da publicação: separar permissões privadas do inventário lógico;
proteger a árvore Windows antes de movê-la para o backup; fazer ensaios fora de árvores Git;
e registrar a identidade do processo de setup antes de liberar suas escritas.

As verificações documentais estão registradas na [medição](../medicoes/2026-10-02-reversible-adoption-plan.json).
Elas cobrem links locais, sintaxe dos exemplos Python, ausência de marcadores de rascunho,
correspondência das restrições citadas e integridade do vault. Não provam a execução da feature.

README PT/EN registra desenho aprovado, plano em revisão e restauração indisponível. Os diagramas
continuam mostrando o funcionamento atual; a atualização das caixas faz parte da implementação.
Não houve captura de dados de projetos, restauração, navegador ou chamada paga a modelo nesta etapa.

Próxima ação: revisão do plano pelo mantenedor. Depois, executar na sessão atual, com um escritor
por checkout e uma revisão independente final, conforme o método já escolhido.
