# Integração interna do filtro de saída

Frente: YC-203.6 e recuperação de YC-203.5. Data: 2026-10-07.

O controlador A/B/A2 usa o guard no mesmo grupo/job, registra os recursos antes de
liberar configuração e recupera os settings sandbox pelo ledger. A prova local usa
processos e sockets reais com sbx e destino remoto simulados. **203.6 continua parcial:**
o contrato de identidade da credencial customizada ainda impede o adaptador nativo.

## Comportamento entregue

O plano/registro v3 acrescenta os hashes do guard, coordenador de rede e Python,
resolvedor do sistema e IPs proibidos. Os registros v1/v2 preservam seus contratos.
O PID do helper é persistido antes do envio da configuração. Recibos de pedido e
destino precisam de confirmação pelo pipe antes de encaminhar os bytes do túnel. A e A2 reutilizam
a porta; B verifica ausência de listener e permanece `blocked_unattributed`.

O resolvedor cria um filho direto dentro da contenção existente, limitado a cinco
segundos e coletado em timeout. O guard aceita uma conexão, host fixo e porta 443,
valida todo o conjunto DNS e confere o peer numérico antes do tráfego. O túnel tem
limites de tempo e bytes. Um escritor serializa os recibos do guard e da fase.

Somente `proxy.sandbox` e `no_proxy.sandbox` entram no contrato de alteração. O diário
registra intenção antes de setting/restart; o limite é conferido novamente depois da
gravação. Políticas, credenciais e demais settings continuam iguais ao baseline.
A recuperação exige proprietário e porta ausentes, cargas identificadas encerradas
e VM parada antes da restauração. Preserva alterações externas e a origem
`default`/`override`; resposta perdida é observada sem repetir intenção consumida.
Um reinício inesperado do daemon interrompe a recuperação.

O setup distribui `mission_network.py` e preserva cópias locais existentes. Cinco
contratos e dez hashes do catálogo foram atualizados; permissões permanecem iguais.

## Revisão e prova

A revisão independente encontrou `TIME_WAIT` após fechamento iniciado pelo upstream:
a porta parecia ocupada embora o helper tivesse saído. No POSIX, listener e sondagem
usam `SO_REUSEADDR`; a sondagem exige bind **e listen**, recusando listener existente.
Windows conserva `SO_EXCLUSIVEADDRUSE`; seu aceite nativo continua pendente.

A integração também expôs disputa entre escritores do ledger. O coordenador serializa
os recibos das duas threads, mantendo o lock entre processos não bloqueante. A revisão
final reproduziu expiração durante gravação de intenção; a checagem depois do save
agora impede a mutação. A regressão de reinício externo durante restauração também
passou. Nenhum achado crítico/importante ficou pendente na revisão final.

Testes locais focados: 16 de egress, 19 de rede e 23 transacionais passaram. Incluem
A/B/A2 na mesma porta, B sem listener, fechamento iniciado por qualquer lado, resposta
perdida, deriva de setting/política/credencial, fonte default/override, porta ocupada,
falha ao gravar destino com zero bytes enviados e morte abrupta do controlador antes
de liberar configuração. O supervisor confirmou coleta da árvore. Contagens, hashes
dos logs e escopo da suíte pública estão na [medição](../medicoes/2026-10-07-network-integration.json).

A primeira exportação teve quatro falhas no hash do contrato legado de `personalizer`.
O hash foi recalculado após resolver sua identidade; a auditoria conferiu os dez
pares componente/cliente e 30 testes de catálogo passaram. A suíte pública foi
reexecutada com o catálogo corrigido; a medição conserva os dois resultados.

A suíte pública corrigida executou **594 testes: 574 aprovados e 20 pulados**,
zero falhas/erros em 233.787 s. Os pulados dependem principalmente de
Windows nativo; a medição lista cada motivo. Fontes, testes, setup e catálogo
coincidem com a árvore testada; depois dela mudaram somente documentos.

## Lacuna nativa e próximo passo

Fontes oficiais consultadas: Docker Docs no commit
`7ba25eeb0c4c594f79e6efadad1af5eaca0500a8`, em 2026-10-07. A medição preserva os hashes.

- [`secret set-custom`](https://github.com/docker/docs/blob/7ba25eeb0c4c594f79e6efadad1af5eaca0500a8/data/sbx_cli/sbx_secret_set-custom.yaml)
  documenta valor por argumento; não documenta entrada por stdin.
- [`secret rm`](https://github.com/docker/docs/blob/7ba25eeb0c4c594f79e6efadad1af5eaca0500a8/data/sbx_cli/sbx_secret_rm.yaml)
  exemplifica `--placeholder`, mas não lista essa opção na tabela de opções.
- [`secret ls`](https://github.com/docker/docs/blob/7ba25eeb0c4c594f79e6efadad1af5eaca0500a8/data/sbx_cli/sbx_secret_ls.yaml)
  não define schema/fingerprint/versão que identifique substituição externa do valor.
- [`settings`](https://github.com/docker/docs/blob/7ba25eeb0c4c594f79e6efadad1af5eaca0500a8/content/manuals/ai/sandboxes/configuration/settings.md)
  distingue default de override; definir o valor default remove a sobreposição.

Placeholder, host e sandbox iguais não demonstram que o valor atual ainda pertence
à operação. Removê-lo por esses campos poderia apagar uma alteração externa. Nenhum
fingerprint foi inventado; `Recovery.setting/restart` recusam a mutação nativa.

O próximo passo é obter esse contrato verificável e a forma segura de fornecer o
valor fictício. Depois implementar o adaptador, usar um valor distinto do placeholder
para provar a injeção e executar os aceites aprovados. O eco atual não prova injeção.
Também faltam Docker TLS real, recusa de MCP/host/rede privada, atribuição de B e os
clientes autenticados. A lista de IPs proibidos ainda precisa de origem nativa
comprovada. Um nonce no recibo não autentica o cliente SOCKS.

Nenhum Docker, modelo, login ou novo ciclo nativo foi executado; o contador permanece
em **2/3**. `client check` conserva `failed/controller_pending`, com `model_calls=0` e
perfis vazios. Políticas e credenciais não ganharam mutadores. A cloud permite
desenvolvimento/testes locais; este incremento não exige novo serviço ou instalação.

## Publicação e retorno

Código publicado em `7d1031c99c326ea7ca8afde2d1daacefe985a5ef`; branch e ref do PR conferidas no GitHub.
Destino autorizado: branch `feat/isolated-executor`, [PR #24](https://github.com/Matheusrpc/YoungCrowHarness/pull/24).
Main permanece na base `932b775`. CI continua não verificado por indisponibilidade da
API nesta sessão; acesso Git é uma prova distinta. Recibos privados ficam fora do Git.

Retorno do código: revert do commit deste incremento na branch, após observar e
recuperar qualquer registro v3 existente. Código v2 não interpreta v3; não apagar o
ledger nem reabrir operações consumidas para contornar essa incompatibilidade.

ATRASO: main 1 frente sem aceite | PR #24 0 incrementos pendentes de publicação | aceite nativo pendente.
