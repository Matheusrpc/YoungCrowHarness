# Alternativas para o bloqueio do executor

Frente: YC-203, revisão de arquitetura solicitada após a descoberta nos dois clientes.
Base: `715c8db795d41a1387c4ce4fa2f8c2b1bb6cc2a7`. Proposta em avaliação;
nenhuma substituição de backend aprovada ou implementada nesta rodada.

**Inventário recebido:** Windows 11 Home Single Language, hipervisor detectado e
módulo Hyper-V ausente. A candidata de VM de controle usando a função Hyper-V fica
pausada nesse PC. A consulta está concluída; não é necessário repeti-la.

## Resultado do inventário Windows

O operador enviou estes campos no terminal, transcritos na medição:

| Campo | Observação | Interpretação |
|---|---|---|
| Sistema | Windows 11 Home Single Language, `CoreSingleLanguage`, `10.0.26200` | A função Hyper-V não é suportada nessa edição |
| Módulo Hyper-V | Ausente | Coerente com a edição; não diagnostica o processador |
| Hipervisor | `HyperVisorPresent: true` | Há hipervisor detectado; não prova gerenciamento de VMs nem virtualização aninhada |
| Requisitos Hyper-V | Quatro valores `null` | Indeterminados; não significam virtualização desativada ou CPU incompatível |
| Memória física total | 8.253.427.712 bytes, aproximadamente 7,69 GiB | Não mede memória livre nem demonstra inviabilidade de uma carga |

A [documentação da Microsoft](https://github.com/MicrosoftDocs/windowsserverdocs/blob/a67a8c2abcdc729692a24f904778f0b5e8f67773/WindowsServerDocs/virtualization/hyper-v/get-started/Install-Hyper-V.md)
declara: “The Hyper-V role **can't** be installed on Windows 10 Home or Windows 11 Home.”
Fonte lida na revisão fixa acima; hash e trecho preservados na medição.

Essa conclusão se aplica à função Hyper-V usada na alternativa proposta. O preflight
atual do YoungCrow consulta `HypervisorPlatform` (WHP) em `mission_sandbox._host_facts`.
O inventário recebido não mediu esse recurso e não permite reprovar o sbx existente.
Outras plataformas continuam sem avaliação. Não há recomendação de compra, mudança
de edição ou instalação forçada; isso não resolveria o contrato local Docker por si só.

O objetivo permanece executar Claude Code e Codex por assinatura, com credenciais
fora da VM de trabalho, prazo imposto, recuperação e preservação do estado alheio.
Execução local continua sendo o padrão; runner dedicado é opcional. A
[revisão anterior](2026-10-08-executor-lifecycle-review.md) já descartou tratar
um proxy fixo ou uma máquina dedicada como solução suficiente.

## Comparação apoiada no código

| Caminho | O que resolve | Trabalho ou prova que ainda exige |
|---|---|---|
| Adaptador atual, após contrato local aplicável | Reaproveita reserva, diário, guard e recuperação | Escritas condicionais e ciclo de credenciais da issue Docker #690 |
| Instalação estável, sem mutações por missão | Retira escritas/restauração de settings e reinícios do fluxo da missão | Endpoint permanente protegido, autorização com prazo e manutenção separada |
| VM de controle própria, usando plataforma existente | Pode retirar daemon/store/proxy do domínio compartilhado do PC | Compatibilidade com sbx aninhado, identidade e propriedade da VM, rede e encerramento externo |

Uma VM de controle seria uma fronteira adicional: coordenador/vault no host,
daemon/store/proxy sbx na VM confiável e cliente oficial na microVM de trabalho.
Outra conta, diretório, daemon ou lock do YoungCrow não oferecem essa separação.
Nenhuma das alternativas tem aceite nativo nesta revisão.

## Por que o proxy permanente exige outro contrato

O código atual não aceita essa alternativa por configuração:

- `mission_network.validate_plan` recusa um proxy já configurado; a ativação altera
  settings e reinicia o daemon. `verify` exige o reinício registrado.
- `mission_transaction.validate_plan` exige inventário de credenciais vazio.
- A prova B e o encerramento v3/v4 exigem porta ausente. Um endpoint permanente
  exigiria o mesmo dono, tráfego negado e nenhuma conexão restante da operação.
- O guard de `mission_egress.py` é descartável e atende uma conexão por operação.

O contrato alternativo teria uma geração de instalação, configuração imutável nas
missões e endpoint que nega tráfego quando ocioso. Autorizações expirariam sem
renovação por reinício. Outro processo não poderia ocupar o endpoint nem trocar
o upstream durante uma queda. Monitorar configuração ou reiniciar rapidamente não
impede essa janela; o mecanismo nativo de proteção ainda não foi demonstrado.

Credenciais permaneceriam no mecanismo do fornecedor. A credencial fictícia
pertenceria à instalação de teste, com retirada própria. Manutenção que ainda
altere estado compartilhado continua precisando de escrita condicional ou exclusão
efetiva de outros escritores. Os recibos v3/v4 conservariam a recuperação original.

## Limites da VM de controle

Uma instalação nova e realmente própria pode evitar alterações de registros
compartilhados. Isso não elimina automaticamente o problema: a interface do
hipervisor também precisa impedir substituição/alteração do recurso por outro
cliente. Nome ou UUID seguido de exclusão não comprova essa propriedade.

A VM confiável persistiria durante o uso da instalação, com login realizado pelo
fornecedor no setup. Descartá-la por missão destruiria esse login ou exigiria cópia
de tokens/snapshots autenticados, contrariando o desenho. Uma prova sintética sem
login pode usar instalação descartável. Encerrar seus consumidores comprovaria
cessação local da injeção; não revogação OAuth no servidor do fornecedor.

Continuariam necessárias provas de rede, endpoint, perda do coordenador, expiração,
suspensão e retomada. Estado salvo, clones ou checkpoints não podem reativar uma
operação vencida. A VM não substitui o guard nem certifica esses comportamentos.

## Consulta executada

Antes de escolher uma substituição, foi consultada a infraestrutura nativa do PC.
O resultado acima pausa a candidata Hyper-V nessa edição, preservando o executor
atual e a consulta ao Docker. Não foi construído hipervisor, distribuição, OAuth
próprio, framework de provisionamento ou nova camada remota.

O bloco abaixo registra a consulta já executada no PowerShell do PC original:

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $ycFields = 'OsName','OsVersion','WindowsEditionId','CsTotalPhysicalMemory','HyperVisorPresent','HyperVRequirement*'
    $ycHostInfo = Get-ComputerInfo -Property $ycFields | Select-Object -Property $ycFields
    [pscustomobject]@{
        host = $ycHostInfo
        hyperv_module_available = [bool](Get-Module -ListAvailable -Name Hyper-V)
    } | ConvertTo-Json -Depth 3
}
```

O JSON foi recebido e analisado. O comando consulta versão/edição do Windows, memória,
indicadores de virtualização e presença do módulo Hyper-V. Não enumera VMs, não
imprime identificadores da máquina ou credenciais, não instala recursos e não
inicia Docker, clientes ou modelos. Foi executado pelo operador; a cloud conferiu
os campos recebidos e a documentação oficial, sem repetir a consulta.

Um módulo presente não prova suporte a virtualização aninhada. Indicadores nulos
ou falsos com hipervisor ativo também não demonstram incompatibilidade. A análise
deve separar o que foi observado do que ainda falta: permissões, hipervisor,
sistema convidado, KVM e sbx nessa combinação. Não instalar nem habilitar Hyper-V
automaticamente para obter um resultado positivo.

Não há plano de provisionamento, novo ensaio A/B/A2 ou substituição aprovada.
Permanecem os dois ciclos consumidos de três, perfis bloqueados e recuperação dos
recibos antigos. O contrato local Docker continua sendo o bloqueio do caminho vigente.

## Falha independente do CI

No commit documental `136469e`, o [job Windows do PR](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/38009453104/job/114085811768)
falhou no teste `test_abrupt_controller_exit_before_config_reaps_the_waiting_guard`.
O mesmo diagnóstico passou no job de push da mesma revisão. Os fontes executáveis
não mudaram desde `058be40`. Isso não identifica a causa nem autoriza ampliar prazos.

As anotações identificam o teste, mas não trazem o traceback. O download do log foi
bloqueado pela rede da cloud no host de armazenamento dos Actions. A adição desse
host foi salva no rascunho do ambiente; aplicação e leitura do log ainda precisam
ser confirmadas. O próximo diagnóstico é obter esse traceback, sem repetir o ensaio
do operador ou alterar código com base apenas no nome do teste.

## Evidência da revisão

Leitura dos contratos e do código, com duas revisões independentes somente leitura:
uma sobre instalação estável e outra sobre a fronteira de uma VM de controle.
Sem mudança de fontes executáveis, instalação, chamada de modelo ou teste nativo.
A [medição](../medicoes/2026-10-09-executor-alternatives.json) vincula revisão e hashes.

## English overview

The current executor remains blocked on the local Docker contract. A stable
installation could remove per-mission settings writes, but needs a protected
persistent endpoint and a different proof contract. An additional control VM could
isolate the entire sbx control plane, but requires nested virtualization, ownership,
network and shutdown evidence. Neither alternative is implemented or certified.

The operator supplied the read-only inventory: Windows 11 Home Single Language,
Hyper-V module absent, hypervisor detected, null requirement fields and 7.69 GiB of
total physical memory. Microsoft's pinned documentation excludes the Hyper-V role
on Home editions, so that control-VM candidate is paused on this PC. This does not
establish a WHP/sbx incompatibility, CPU failure or insufficient memory. No upgrade,
installation or repeat inventory is requested. Preserve local-first use, subscription
login, old recovery contracts and the 2/3 cycle count.

Separately, the PR Windows CI failed the abrupt-controller-exit test; the same
diagnostic passed on push. Cause is unverified without its traceback. The log-storage
host is blocked by cloud network policy; an additive draft change is saved, not yet
verified in the running environment. No product-code fix or native retry was performed.

ATRASO: inventário 0 | alternativa Hyper-V pausada | diagnóstico CI pendente | executor bloqueado.
