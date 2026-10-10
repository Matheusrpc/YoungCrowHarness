# Contrato local do Docker Sandboxes 0.47.0

Frente: YC-203, consulta documental do fornecedor.
Base: `c4fcae10a61711380f6acf96d0c0b7885269f573`. Consulta em 10/out/2026.

**A versão 0.47.0 não libera o adaptador atual.** As fontes consultadas descrevem
correções relevantes, mas não especificam as precondições exigidas pela recuperação
do YoungCrow. Isso é uma lacuna de documentação e prova; não demonstra que o Docker
seja incapaz de oferecer essas garantias. A [issue #690](https://github.com/docker/sbx-releases/issues/690)
continuava aberta, sem comentários, na consulta.

## O que a versão acrescenta

A [release 0.47.0](https://github.com/docker/sbx-releases/releases/tag/v0.47.0),
publicada em 5/out, corrige a interceptação OAuth com variação de maiúsculas ou ponto
final no hostname. Também recusa grants desconhecidos e respostas de criação de
chave Anthropic que o proxy não consegue mascarar. Essas mudanças afetam a fronteira
de credenciais que precisamos provar. O suporte a `sbx run --rm` remove o sandbox
ao fim da sessão; a descrição não oferece uma condição atômica para restaurar
settings ou excluir uma credencial compartilhada.

| Garantia necessária | Evidência encontrada | Pendência |
|---|---|---|
| Escrita condicional do estado completo de um setting | `get --json` inclui origem e padrão; `set`/`unset` escrevem overrides pelo daemon | Comando/endpoint e precondição atômica que comparem valor, origem, padrão e metadados relevantes |
| Exclusão condicional da mesma credencial | `secret rm` identifica serviço e escopo; remover a variante de sandbox pode restaurar a global | Identificador estável, revisão e rejeição de exclusão com revisão antiga |
| Cessação da injeção em consumidores existentes | As notas de 0.46.0 dizem que remoção em lote revoga e falhas podem ser repetidas após apagar o registro | Procedimento e resultado verificável para confirmar a cessação, incluindo falha parcial |

Fontes Docker lidas na revisão fixa
[`18bbfeeb249da011f359d558dba84c4b6dc3a335`](https://github.com/docker/docs/tree/18bbfeeb249da011f359d558dba84c4b6dc3a335):
[settings](https://github.com/docker/docs/blob/18bbfeeb249da011f359d558dba84c4b6dc3a335/content/manuals/ai/sandboxes/configuration/settings.md),
[credenciais](https://github.com/docker/docs/blob/18bbfeeb249da011f359d558dba84c4b6dc3a335/content/manuals/ai/sandboxes/configuration/credentials.md) e
[notas de versão](https://github.com/docker/docs/blob/18bbfeeb249da011f359d558dba84c4b6dc3a335/content/manuals/ai/sandboxes/release-notes.md).
Hashes e trechos estão na [medição](../medicoes/2026-10-10-sbx-047-contract-review.json).

## Consequência para o projeto

`mission_transaction.validate_plan` ainda exige 0.46.0; `mission_sbx` recusa os
efeitos com `native_egress_contract_unverified`. Atualizar o executável não satisfaz
o contrato nem torna um recibo antigo válido para a versão nova. A revisão também
conferiu o plano legado sem coordenador de rede: ele não aceita a prova integrada
de injeção e não fornece um caminho de liberação equivalente.

O operador informou Windows 11 Home Single Language também no computador novo.
A candidata que depende da função Hyper-V continua pausada. A
[instalação oficial do Docker](https://github.com/docker/docs/blob/18bbfeeb249da011f359d558dba84c4b6dc3a335/content/manuals/ai/sandboxes/install.md)
lista Windows 11, Intel/AMD de 64 bits e Windows Hypervisor Platform para execução
local. WHP é distinto da função Hyper-V; a edição Home, sozinha, não reprova sbx.
CPU, RAM e WHP do computador novo continuam sem inventário. Trocar de hipervisor
não comprova as garantias do store local.

Próximo avanço de YC-203: obter um contrato local aplicável aos três pontos acima,
então revisar o plano e a versão candidata antes de qualquer prova nativa. As
correções de segurança de 0.47.0 precisam entrar nessa avaliação; conservar o pin
histórico não é recomendar novo uso autenticado de 0.46.0. Nenhuma atualização,
instalação ou prova foi executada nesta consulta. Contador nativo preservado em 2/3.

A operação assistida já disponível pode continuar com backlog, vault, memória e
revisão nas sessões autorizadas. Isso não conclui YC-203 nem o despacho autônomo.

Verificação documental: 435 caminhos Markdown locais conferidos, nenhum ausente;
hashes e citações das quatro fontes conferidos; `vault.py check` leu 68 notas sem
problemas. Nenhum arquivo executável mudou, e a suíte de código não foi repetida.

## English overview

Docker Sandboxes 0.47.0 includes relevant credential-interception fixes, but the
reviewed documentation does not specify the conditional settings write, secret
identity/revision/deletion and revocation confirmation required by this adapter.
This is an evidence gap, not proof that those guarantees are unsupported. Issue
#690 remains unanswered. The existing 0.46.0 pin and blocked profiles are unchanged;
no upgrade, native trial or model call occurred. Windows Home alone does not rule
out sbx's distinct WHP requirement. Existing assisted use can continue; autonomous
dispatch still depends on YC-203.

ATRASO: consulta documental 0 | contrato local pendente | executor nativo bloqueado.
