# Pacote v3: criação e execução sintética

Frente: executor isolado, 2A-R1. Desenvolvimento local, sem publicação.

O operador criou a sandbox pelo pacote v3 em 4,872 segundos, com `--pull missing`.
O digest observado coincide com o [build verificado](2026-10-04-native-kit-build.md):
`sha256:3e6a380a46840656b9e724694ef2964e2d13471bc3dd0fe92ae66492217dfe2f`.
Inspeção: 2 CPUs, 4 GiB, nenhuma montagem do projeto, nenhuma sessão de agente.
O código de produto permaneceu igual ao medido no build.

| Verificação | Resultado |
|---|---|
| Certificado temporário | Removido automaticamente; inventário original restaurado |
| Origem e porta do registry | Origem original restaurada; nenhuma porta publicada; registry parado/PID 0 |
| Guardian e launcher no pacote | SHA-256 esperado; root/0644; usuário 1000 não consegue abrir para escrita |
| Diretório de operações | root/0700; leitura recusada ao usuário do agente |
| Entrada sem coordenador | Retorno 125; nenhuma operação criada |
| Launcher: conclusão | Retorno 0; processo encerrado, PID 0; segundo início recusado |
| Launcher: prazo | Retorno 124; processo encerrado, PID 0; segundo início recusado |
| Launcher: perda do transporte | Retorno 125; processo encerrado, PID 0; segundo início recusado |
| Estado final | Cinco VMs próprias paradas; zero chamadas de modelo |

Os três casos usaram o launcher entregue pelo pacote. A imagem interna sintética contém
Python e bibliotecas já presentes na VM, guardian do pacote e fixtures locais; não houve
download, credencial, instalação de cliente ou alteração dos arquivos do produto na VM.
Os tempos totais de observação foram 0,902 s, 5,072 s e 0,570 s; incluem transporte e leitura
do estado final. Esses tempos não medem isoladamente a duração do processo cliente.
Hashes e recibos estão na [medição](../medicoes/native-package-proof.json).

Também congelamos somente um contêiner sintético antes do prazo e o retomamos um segundo
depois. Ele terminou com 124/PID 0 e recusou novo início. Não apareceu heartbeat posterior
ao prazo no transporte observado. Como a saída passa pelo guardian, esse resultado não
exclui execução transitória do cliente durante a retomada. O teste usa o freezer de cgroups;
não suspende o Windows e não fecha a prova de suspensão do host.

## Atualização posterior

O operador executou o ensaio de reinício. O serviço voltou, mas o timestamp de término
excedeu o deadline em 3,8935 ms. A prova permanece reprovada. A [correção e os novos testes](2026-10-04-shutdown-reserve.md)
registram uma candidata separada; os hashes e resultados abaixo pertencem ao pacote anterior.

## Próxima prova e limites (estado deste checkpoint)

Foi preparado um ensaio para o PowerShell normal do operador: iniciar uma operação
sintética de cinco segundos, observar seu início e reiniciar o serviço Docker Sandboxes
uma vez. Ele recusa outras sandboxes ativas, persiste a intenção, conserva o prazo original
e confere identidade, término e recusa de repetição. O script verifica sintaxe e pré-condições;
o reinício em execução ainda não foi testado. Não instala certificado nem reinicia o Windows.
O console do operador é necessário pela falha de acesso a sockets já reproduzida quando
o daemon foi iniciado pelo terminal do agente.

O cliente sintético ainda usa rede desabilitada. Isso não comprova inacessibilidade MCP
com o provedor acessível. Rede, sentinelas, reinício ativo do daemon e suspensão do host
continuam no aceite de R1. R2/R3 e os perfis nativos seguem bloqueados.

## English overview

Later update: the operator ran the restart test. The daemon returned, but termination was
recorded 3.8935 ms past the deadline. That proof remains failed. See the [candidate correction](2026-10-04-shutdown-reserve.md#english-overview).
The following findings and hashes describe the earlier package checkpoint.

The operator created the v3 sandbox in 4.872 seconds with `--pull missing`. Inspection
confirmed the expected digest, 2 CPUs, 4 GiB and no project mount. Temporary certificate,
source setting and port changes were reversed. Packaged guardian/launcher hashes and
file protections passed; the default non-root invocation refused with exit 125.

Three launcher cases passed in this VM: completion, deadline and transport loss. All
ended with PID 0 and refused another start. The synthetic inner image used VM-local
Python, packaged code and local fixtures, with no download or model call.

One cgroup freeze/thaw case ended with timeout and refused replay. No late heartbeat was
forwarded, but this cannot exclude transient execution after thaw and does not establish
whole-host suspension safety. Five owned VMs are stopped.

An operator-console test is prepared for one daemon restart during a five-second synthetic
operation. Only syntax and read-only prerequisites have passed. Networking/MCP with provider
access, sentinels, active daemon recovery and host suspension remain unverified. R1 is partial;
R2/R3 and native profiles remain blocked. No production code changed or publication occurred.

ATRASO: main 1
