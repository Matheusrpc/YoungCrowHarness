# Alternativas para o bloqueio do executor

Frente: YC-203, revisão de arquitetura solicitada após a descoberta nos dois clientes.
Base: `715c8db795d41a1387c4ce4fa2f8c2b1bb6cc2a7`. Proposta em avaliação;
nenhuma substituição de backend aprovada ou implementada nesta rodada.

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

## Recomendação e próxima ação concreta

Preservar o executor atual e a consulta ao Docker. Antes de escolher uma substituição,
conferir se o PC oferece a infraestrutura nativa para avaliar a VM de controle.
Essa consulta é menor que implementar um serviço permanente ou um backend de VMs
sem conhecer a plataforma. Não construir hipervisor, distribuição, OAuth próprio,
framework de provisionamento ou nova camada remota nesta etapa.

No PowerShell do PC original, executar uma vez:

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

Enviar o JSON para análise. O comando consulta versão/edição do Windows, memória,
indicadores de virtualização e presença do módulo Hyper-V. Não enumera VMs, não
imprime identificadores da máquina ou credenciais, não instala recursos e não
inicia Docker, clientes ou modelos. Foi revisado, mas não executado nesta cloud Linux.

Um módulo presente não prova suporte a virtualização aninhada. Indicadores nulos
ou falsos com hipervisor ativo também não demonstram incompatibilidade. A análise
deve separar o que foi observado do que ainda falta: permissões, hipervisor,
sistema convidado, KVM e sbx nessa combinação. Não instalar nem habilitar Hyper-V
automaticamente para obter um resultado positivo.

O retorno desta consulta orienta a proposta seguinte. Ainda não há plano de
provisionamento, novo ensaio A/B/A2 ou substituição aprovada. Permanecem os dois
ciclos consumidos de três, perfis bloqueados e recuperação dos recibos antigos.

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

The next step is the read-only Windows inventory above. It neither changes system
features nor runs a client or model. Its result will inform a concrete proposal;
module presence alone does not prove nested sbx support. Preserve local-first use,
provider-managed subscription login, old recovery contracts and the 2/3 cycle count.
No new native attempt, provisioning or backend replacement is approved by this review.

ATRASO: revisão preparada | inventário Windows pendente | executor nativo bloqueado.
