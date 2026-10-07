# Protocolo do executor isolado

Frente: executor isolado, 2A-R1. Estado: implementação local com prova sintética;
R1 incompleto, sem publicação em main e sem chamadas a modelos.

O [guardian em Python](../../runtime/sbx/guardian.py) agora registra o consumo da
operação antes de iniciar qualquer subprocesso. Ele aceita uma descoberta e um
diagnóstico pelo canal privado, dentro do mesmo prazo. Uma repetição, mensagem
inválida ou reinício com o mesmo diretório de controle termina em recusa.

O controle fica em armazenamento da microVM, com diretório root/0700 e manifesto
root/0600. Os marcadores usam criação exclusiva, flush, fsync do arquivo e do
diretório. Um marcador incompleto também bloqueia a operação. Isso garante no
máximo uma tentativa nesse controle; uma queda pode impedir a conclusão depois
de consumir a tentativa. A vinculação desse controle à reserva SQLite do host
ainda pertence a R2.

## Provas

[Medição e hashes dos quatro arquivos](../medicoes/guardian-protocol.json).
Windows 11 AMD64, `sbx` 0.46.0, template `shell-docker` fixado por digest.
O contêiner interno usa Python 3.14.4, copiado dos arquivos de sistema já presentes
na microVM. Essa preparação não baixou dependências nem copiou caches pessoais.
A imagem é de ensaio; ainda falta a receita de distribuição do runtime.

| Verificação | Resultado observado |
|---|---|
| Testes locais no Windows | 9 passaram; incluem concorrência, persistência com falha, JSON inválido e relógio regressivo |
| Mesmos testes no Linux da microVM | 9 passaram, incluindo fsync real do diretório |
| Descoberta e diagnóstico válidos | Um cliente de diagnóstico; término normal em 0,464 s |
| Segundo despacho durante execução | Recusa 125, apenas um cliente iniciado; 0,412 s |
| Identidade divergente | Recusa 125, nenhum diagnóstico iniciado; 0,310 s |
| Descoberta com falha | Término 126, nenhum diagnóstico iniciado; 0,339 s |
| Cliente tentando permanecer ativo | Término 124, observação de parada em 5,110 s |
| Saída acima de 8 MiB | Término 122; 2,907 s |
| Reinício dos seis contêineres | Todos retornaram 125, sem novo cliente |

Todos os seis contêineres terminaram com `Running=false` e PID externo zero.
Os tempos incluem a observação de parada pelo Docker; o manifesto fixa cinco
segundos para o trabalho e a prova admite até cinco segundos adicionais de observação.
O cliente observou UID/GID 1000, `no_new_privs=1` e os cinco conjuntos de
capabilities zerados, inclusive o bounding set. Não conseguiu ler ou reescrever
o controle, acessar os descritores de PID 1 ou sinalizar o supervisor. Seu stdin
estava fechado e o HOME privado continuou gravável. O ambiente tinha apenas
HOME, PATH, LANG e PYTHONDONTWRITEBYTECODE. Cgroups confirmaram 2 CPUs, 4 GiB e
64 PIDs; o contêiner recebeu `network=none` e nenhum socket Docker.

A primeira corrida real encontrou `PermissionError` antes do lançamento: o
supervisor tentava entrar no HOME 0700 do cliente ainda como root sem permissão
DAC adicional. A correção moveu a troca de diretório para depois da redução de
UID/GID. A mesma prova passou mantendo as permissões restritas. As tentativas
negativas foram preservadas no registro privado.

## Como verificar e retomar

No checkout do harness:

```bash
python -B -m unittest discover -s tests -p test_mission_guardian.py -v
```

O [smoke da microVM](../../tests/smoke_mission_guardian.py) exige uma microVM de
ensaio já identificada, `YC_PROBE_NONCE`, Engine interno e a imagem preparada
por digest. Ele recebe `--image DIGEST --root DIRETORIO_NOVO` dentro dessa VM.
O diretório deve ser exclusivo; os recibos e contêineres encerrados ficam
preservados. Esse script não cria um ambiente seguro no host nem instala o
runtime em projetos consumidores. O lançador precisa validar identidade e
política antes de usá-lo.

O contrato está no [desenho aprovado](../superpowers/specs/2026-10-04-isolated-executor-design.md#protocolo-do-guardian-refinamento-de-r1-2026-10-04).
O [guia de uso](../USAGE.md#sandbox-environment) continua indicando
`runtime_profile_unverified`; o catálogo de perfis nativos permanece vazio.
As duas sandboxes de ensaio foram observadas paradas ao fim da corrida.

## Limites e próxima atividade

A próxima atividade é empacotar o lançador e o guardian para que o preflight
confira a configuração efetiva antes de liberar o cliente. Esse pacote precisa
resolver a compatibilidade do gateway MCP externo, provar rede permitida e
sentinelas proibidas e repetir os cenários de perda do coordenador/transporte
com o código Python. Os resultados da fixture Go anterior não certificam este código.

Também faltam reinício do daemon com trabalho ativo, suspensão completa da VM/host
e observação OAuth/catálogo. O timer usa sinais Python; a documentação informa que
o handler roda no interpretador e pode ser adiado por operações longas em C.
Os seis casos medidos não demonstram um prazo incondicional sob suspensão ou
bloqueio do sistema. [Comportamento documentado dos sinais](https://docs.python.org/3/library/signal.html#execution-of-python-signal-handlers).

A redução de privilégios ocorre antes do exec em um supervisor sem threads;
esse requisito deve permanecer na receita. [Restrição de preexec_fn](https://docs.python.org/3/library/subprocess.html#subprocess.Popen).
O guardian retira o bounding set ainda com SETPCAP e só depois reduz UID/GID.
[Contrato de PR_CAPBSET_DROP](https://man7.org/linux/man-pages/man2/PR_CAPBSET_DROP.2const.html).

## English overview

The Python guardian passed nine unit tests on Windows, the same nine on the
microVM's Linux, and six real synthetic container scenarios. It durably consumes
an operation before any child starts, permits one discovery followed by one
diagnostic within a fixed deadline, and refuses replay or restart using the same
control directory. Restarting each of the six containers started no new client.

The client ran as UID/GID 1000 with all capability sets zero, no_new_privs,
closed stdin, a private writable HOME, no Docker socket and no network.
Its cgroup reported 2 CPUs, 4 GiB and 64 PIDs. All containers stopped with PID zero.
No model was called. Both test sandboxes were observed stopped afterward.

This is a partial R1 proof. Runtime packaging, effective outer policy, network
sentinels, Python coordinator/transport-loss tests, active daemon restart,
suspension semantics and OAuth/catalog proof remain pending. R2 must bind the
control directory to the host reservation. Python signal handlers can be delayed
by long C operations, so the measured deadline is not an unconditional guarantee.
Native profiles remain disabled; no consumer setup or production command changed.

ATRASO: main 1
