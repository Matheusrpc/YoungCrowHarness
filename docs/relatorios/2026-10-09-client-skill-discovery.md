# Descoberta das skills de missão por cliente

Frente: YC-011, prova de descoberta sem prompt. Base: `5fa0c65321e6a99af45aea88a8089b451fb4e730`.

O smoke existente agora permite consultar Claude ou Codex separadamente e guardar
um recibo JSON. Isso permite observar o cliente disponível sem aguardar o outro.
O Codex real desta cloud encontrou `yc-personalizer`, `yc-config`, `yc-missao` e
`yc-status`. Nenhum prompt de usuário foi enviado.

## Mudança e uso

```bash
python3 -B tests/smoke_clients.py --discovery-only --codex /caminho/codex --report .runtime/descoberta-codex.json
```

A pasta do recibo deve existir; o arquivo deve ser novo. Para Claude, usar
`--claude` com seu executável nativo. Ambos os argumentos podem ser fornecidos
para uma sequência que para na primeira falha. Cliente omitido fica `not_run`.
O modo completo anterior, que exige ambos e usa fixture de modelo em loopback para
conferir o agente Codex, permanece disponível.

O novo modo consulta somente `initialize`/`skills/list` no Codex ou a inicialização
de controle do SDK no Claude. Reutiliza o instalador e consumidor temporários do
smoke, sem copiar login pessoal. As quatro skills são os arquivos reais do repo;
a dependência humanizer usa a fixture local existente. O setup não instala plugins
externos; o teste não os executa.

O recibo registra plataforma, versão e hash do executável, revisão base e hash do
smoke, nomes encontrados e hashes das quatro skills e suas entradas instaladas.
Os hashes são conferidos novamente depois da consulta. São identidades dos arquivos
locais, não prova de que um modelo interpretou ou aplicou seu conteúdo.

Skill ausente, resposta inválida, timeout e falha de limpeza produzem falha e saída
não zero. O recibo é reservado antes da preparação e não sobrescreve evidência antiga.
Uma interrupção abrupta pode deixá-lo `running`; esse estado não é sucesso.
O prazo é por consulta, e a limpeza do probe cobre os processos diretos; este smoke
não demonstra um limite global nem contenção de descendentes como o executor isolado.

## Observação nativa

Em 9/out, às 20h36 de Brasília, a revisão final do probe rodou em Linux com
`codex-cli 0.159.0-alpha.3`. A consulta concluiu com as quatro skills encontradas,
zero prompts e remoção da fixture temporária. Claude não está instalado nesta cloud
e ficou `not_run`. A [medição](../medicoes/2026-10-09-client-skill-discovery.json)
registra horários UTC, hashes e resultados exatos. Um primeiro ensaio também passou;
seu recibo permanece privado, separado da prova da revisão final.

No Claude, as regressões usam um filho local que fala o protocolo. Isso testa o
probe, não representa descoberta pelo Claude real. A leitura manual de skills na
prova P06 permanece uma evidência diferente.

## Verificação e continuidade

As primeiras quatro regressões falharam antes da implementação: dez falhas contando
subcasos. A revisão encontrou ainda dois casos: falha de limpeza não refletida na
saída e envelope Claude inválido deixando o recibo `running`. Ambos tiveram teste
vermelho antes da correção. Os sete testes focados passaram em 14,496 s.

A suíte completa executou 678 testes: 658 aprovados, 20 pulados, sem falhas,
em 372.599 s. O vault da raiz (55 notas) e o do exemplo
(21 notas) passaram sem problemas. Contagens e hashes estão na medição.
O CI Windows ganhou a mesma suíte de protocolo pelo wrapper já existente.
A revisão independente de código e testes não encontrou impedimentos após as correções.
Não houve mudança de catálogo, permissões, perfis do executor, fila ou P06.

O CI do commit anterior `5fa0c65` terminou com os oito jobs de push/PR aprovados,
incluindo Windows. Isso não substitui o CI deste incremento. A issue Docker
[#690](https://github.com/docker/sbx-releases/issues/690) continuava aberta sem comentários
na consulta desta sessão; seus bloqueios e o contador de ciclos foram preservados.

YC-011 permanece parcial: falta observar a descoberta no Claude e provar a aplicação
das quatro skills em ambos os clientes, com os limites do pacote de execução.
O comando acima não inicia agente de produto, chama modelo, realiza login ou libera YC-203.

The existing smoke now supports one-client metadata discovery with a preserved JSON
receipt. Real Codex discovery passed; Claude was not run here. Native application
of the four skills and Docker executor acceptance remain pending. No model prompt
was sent, and the previous full smoke remains available.

ATRASO: descoberta Codex 0 | descoberta Claude pendente | aplicação nativa/YC-203 pendentes.
