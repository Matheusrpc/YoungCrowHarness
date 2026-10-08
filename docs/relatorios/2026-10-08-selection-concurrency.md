# Concorrência na seleção do destino

Frente: estabilidade de YC-203, PR #24. Data: 8 de outubro de 2026.

Um leitor ou segundo escritor podia enumerar o temporário da seleção antes de o
primeiro processo publicá-lo com `os.replace`. A inspeção seguinte encontrava um
arquivo ausente e retornava `execution_storage_unprotected`. A falha foi reproduzida
no baseline e agora tem provas com dois processos e barreiras no temporário real.

## Comportamento

Consultas e alterações adquirem o mesmo `reclaim.lock` antes do inventário. A aquisição
de arquivo existente usa somente leitura, não cria arquivo nem escreve no lock vazio.
A leitura interna evita aquisição recursiva; o digest é conferido dentro do lock.
Um concorrente recebe `execution_selection_busy`. Depois da gravação do vencedor,
um digest antigo recebe `execution_selection_conflict`, sem uma segunda escrita.

A primeira configuração mantém as verificações antes de criar a área e o lock, e as
repete sob proteção. Se outro escritor criar o lock durante esse preflight, a operação
retoma uma vez sob o lock e refaz todos os gates. Erro de proteção persistente continua
sendo recusado. Nenhum temporário é ignorado e nenhuma ACL existente é reparada.
O helper compartilhado inicializa um lock novo somente depois de adquiri-lo.

## Provas

| Verificação | Resultado |
|---|---|
| Quatro casos iniciais com barreira no temporário | Falharam antes: erro de proteção em vez de ocupado |
| Bateria ampliada sobre o baseline | 19 testes, 6 falhas esperadas de concorrência, 1 skip |
| Bateria da seleção corrigida | 18 aprovados, 1 junction Windows pulada |
| Focais de rede, lock e encerramento | 7 aprovados em 6,882 s |
| Duas escritas com o mesmo digest, 30 execuções | 30 aprovadas |
| Suíte pública completa | 610 aprovados, 20 pulados, 249,942 s |

As barreiras cobrem leitura/alteração durante a primeira configuração e uma atualização,
além do lock que surge durante o preflight. A bateria também verifica lock vazio,
somente leitura e ausente, preservação dos bytes, recusa sem reparo e liberação após
morte do processo. Os testes no Windows continuam necessários: os resultados
Linux não provam a semântica do lock naquele sistema. Dois casos foram acrescentados
à etapa inicial do CI; a suíte completa continua habilitada.

Revisão independente sem bloqueadores. O apontamento sobre abertura para escrita de
lock somente leitura foi corrigido antes do QA final. O catálogo mudou somente dez
hashes de conteúdo de cinco capacidades nos dois clientes; contratos, permissões e
26 digests nulos foram preservados. Auditoria: 20 correspondências, 30 não verificadas,
saída zero. A revisão de catálogo conferiu os hashes reais.

## CI anterior e próximo passo

O CI completo de `25ee51d`, que reduziu as consultas Git, passou no
[push 37724707270](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37724707270)
e no [PR 37724712042](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37724712042).
Os oito percursos positivos nas etapas focais/completas concluíram entre 8,625 e
10,656 s, com recuperação aprovada, dentro do mesmo supervisor de 15 s. Isso comprova
essas rodadas; não é garantia de duração em qualquer host.

Destino autorizado: branch `feat/isolated-executor`, PR #24. A próxima prova é o CI
Windows da aquisição somente leitura, inclusive em arquivo vazio, e da exclusão
entre processos. Retorno: reverter o
incremento e seus hashes associados. A seleção persistida mantém o mesmo formato.

O lock coordena a seleção; `Sbx.persist` grava outros recibos nessa área sem participar
dele. O contrato sbx local e os fontes/evidências originais de B continuam pendentes.
Nenhum Docker/sbx, login, modelo ou novo ciclo nativo foi executado; contador 2/3,
perfis bloqueados e `proof_accepted=false` preservados.

## English overview

Selection reads and updates now acquire the same existing lock before inventory,
without creating or writing lock bytes during queries. Bootstrap retains its checks
and revalidates under the lock; a newly observed lock permits one bounded recheck.
Concurrent operations return busy and stale digests remain conflicts. Process/barrier
regressions pass; the full local suite passed 610 tests with 20 skips. Windows proof
of read-only and empty-file locking remains pending. Full Windows CI for the previous
Git preflight optimization passed on push and PR, with positive flows at 8.625 to 10.656 s.
Other receipt writers and native executor acceptance remain outside this proof.

ATRASO: PR #24 incremento local | CI Windows da concorrência e aceite nativo pendentes.
