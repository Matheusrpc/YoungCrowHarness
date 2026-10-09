# Preparação da fila de desenvolvimento

Frente: refinamento de YC-204, sem implementação de 2B.

A [matriz proposta](../superpowers/specs/2026-10-09-queue-eligibility-refinement.md)
converte regras já aprovadas em dez cenários de decisão. Distingue vagas de PBI,
vagas de execução e capacidade comprovada do executor. Também registra o trabalho
ainda necessário para recuperar uma intenção entre SQLite e a reserva compartilhada.
PM, Tech Lead, Dev e QA mantêm suas responsabilidades na especificação geral.

O complemento detalha uma proposta de ordem entre etapas e papéis: primeiro trabalho
iniciado e decisões necessárias dos líderes, pela sequência em que ficaram prontos;
depois novos PBIs pela prioridade persistida. Trabalho ativo impedido não retém
capacidade livre quando outro PBI pode avançar. Repetir um evento conserva a candidatura;
uma etapa nova recebe sequência própria. Retomada de bloqueio exige vaga de PBI novamente.
Seis casos exemplificam critérios futuros, sem alegar testes executados. A preferência
por trabalho iniciado ainda está em revisão, sem aprovação registrada nesta entrega.

O documento está em revisão e não é um plano autorizado de implementação. YC-203
continua pré-condição; a consulta Docker está em espera. Não houve alteração de código,
esquema, permissões, perfis ou limites. README PT/EN, backlog e handoff apontam o rascunho.

A verificação desta entrega cobre vínculos locais, formato do diff e revisão documental.
Não foi repetida a suíte de produto: nenhum arquivo executável foi alterado. A prova
autenticada do Claude e o aceite nativo continuam pendentes. A
[medição](../medicoes/2026-10-09-queue-refinement.json) identifica os arquivos e o escopo
das verificações. Destino: PR #24; retorno por revert do incremento documental.

ATRASO: YC-204 em refinamento | aceite do executor pendente.
