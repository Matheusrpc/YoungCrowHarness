# Build nativo do kit v3

Frente: executor isolado, 2A-R1. Desenvolvimento local, sem publicação.

A receita foi construída dentro de uma microVM dedicada e importada pelo Docker
Sandboxes 0.46.0. Isso supera o impedimento de build registrado no
[checkpoint anterior](2026-10-04-launcher-boundary.md). A criação de uma sandbox pelo
kit [passou no ensaio seguinte](2026-10-04-native-package-proof.md) com `--pull missing`.
As falhas de cache e confiança abaixo ficam preservadas como histórico.
R1 continua incompleto; R2/R3 e os perfis nativos permanecem bloqueados.

## Evidência

| Etapa | Resultado observado |
|---|---|
| Buildx 0.37.1 / Engine 29.8.1 | Build Linux AMD64 concluído na microVM, sem alterar os cinco arquivos da receita |
| Arquivo OCI | 599.219.712 bytes; hashes de manifesto, configuração e camadas conferidos |
| Descritor v3 | `sbx@1` e `resources@1` preservados; declaração de 2 CPUs e 4 GiB |
| `sbx template load` | Retorno 0; imagem listada no armazenamento local |
| Criação pela tag com `--pull never` | Recusada: o resolvedor tentou consultar o registry remoto |
| Registry HTTP em loopback | Mesmo digest; origem inicialmente recusada |
| Exceção de origem aprovada | Origem aceita; conexão recusada por exigir HTTPS |
| HTTPS com certificado explícito no cliente de teste | Mesmo manifesto recebido; validação TLS ativa |
| HTTPS antes da confirmação do operador | Certificado recusado; sem alteração da confiança nesse ensaio |
| Confirmação do operador e resolução do kit | Certificado aceito; descritor resolvido com 2 CPUs/4 GiB e sem workspace |
| Criação por digest com `--pull never` | Retorno 1 em 0,877 s: referência ausente no cache; nenhuma sandbox criada |
| Limpeza do certificado instalado | `.NET Remove` excedeu 15 s; retirada posterior com `certutil` retornou 0 e restaurou o inventário original |
| Reimportação com referência exata no índice OCI | Retorno 0, 21 blobs preservados; a listagem continuou mostrando a tag anterior, sem comprovar o alias |
| Criação seguinte com `--pull missing` | Retorno 0 em 4,872 s; digest esperado, 2 CPUs/4 GiB e nenhuma montagem do projeto |
| Estado final | Lista de origens e política anteriores restauradas; portas removidas; registries e quatro VMs próprias parados |

Manifesto: `sha256:3e6a380a46840656b9e724694ef2964e2d13471bc3dd0fe92ae66492217dfe2f`.
O [registro de medição](../medicoes/native-kit-build.json) conserva versões, hashes,
resultados e limites. Nenhuma chamada de modelo ou publicação remota foi feita.

O build usou o driver Docker com armazenamento containerd, observados nesta VM.
A [documentação dos exportadores](https://docs.docker.com/build/exporters/oci-docker/)
descreve o formato OCI e limitações por driver; este ensaio comprova somente a combinação
medida. A tag do frontend ainda é mutável, portanto não afirmamos reprodução bit a bit.
O [fluxo oficial de distribuição](https://docs.docker.com/ai/sandboxes/customize/author/distribute/)
orienta o uso de Buildx para v3. Nenhum kernel, hook do builder ou backend foi substituído.

## Falhas preservadas e limpeza

O primeiro build não tinha acesso ao CDN observado durante o download. A segunda
tentativa passou após liberar esse host somente na VM de build. As quatro liberações
de download foram retiradas ao terminar; a comparação da política completa conferiu
com o estado anterior.

O primeiro registry HTTP não estava pronto quando a porta foi testada. O ensaio seguinte
serviu o manifesto, mas encontrou a lista de origens. A tentativa autorizada passou
essa verificação e encontrou a exigência de HTTPS, também descrita no
[CLI oficial](https://docs.docker.com/reference/cli/sbx/kit/pull/).

Na preparação TLS, a configuração aninhada de somente leitura via variável de ambiente
falhou no startup. Sua substituição pelo YAML documentado passou; o armazenamento e
os certificados ficam em mounts somente leitura dentro da VM. A chave privada permanece
nessa VM. Nessa preparação, o certificado público foi usado explicitamente pelo cliente do ensaio.
As tentativas malsucedidas foram preservadas; seus processos estão parados.

## Continuação autorizada no Windows

A inclusão temporária do certificado foi autorizada. As preparações pelo terminal do
agente não chegaram à criação da sandbox: a API e `certutil` ficaram pendentes; o
processo próprio de importação foi encerrado. O cmdlet `Import-Certificate` precisou
do módulo que fornece `Cert:` e então retornou “Interface do usuário não permitida
nesta operação”. O certificado não foi incluído.

O operador executou o ensaio às 23:35 UTC de 2026-10-04. A inclusão passou e o Docker
resolveu o descritor; a criação falhou por cache. CPU/memória foram observadas na
configuração resolvida, sem comprovar recursos efetivos de uma VM criada pelo pacote.

A retirada automática do certificado excedeu 15 segundos e deixou a entrada instalada.
Conferimos a identidade e sua origem no recibo antes de executar
`certutil -user -f -Silent -delstore Root` para o thumbprint exato. Retorno 0, certificado
ausente e inventário igual ao anterior. Origem restaurada, porta removida, registry
parado/PID 0 e VM de build parada constam do recibo do operador.

Uma reimportação alterou somente as referências do índice OCI, conservando os 21 blobs
e o digest do manifesto. O loader retornou 0, mas a listagem mostrou somente a tag
anterior; isso não comprova o cache da referência exata. A próxima tentativa usa a opção
[`--pull missing` documentada pelo Docker](https://docs.docker.com/reference/cli/sbx/create/)
para o mesmo digest no registry HTTPS local. A remoção passa a usar o `certutil` nativo
que concluiu a reconciliação. O operador executou esse script às 00:08 UTC de 2026-10-05:
criação e limpeza passaram, sem erros. [Verificações dentro do pacote](2026-10-04-native-package-proof.md).

## Próxima ação

A [decisão de consumo local](../superpowers/specs/2026-10-04-local-kit-publisher-decision.md)
registra as duas autorizações e os resultados. Criação por digest e limpeza passaram.
O [checkpoint atual](2026-10-04-native-package-proof.md) descreve as provas do pacote e
o próximo ensaio: reinício do serviço durante trabalho sintético, no console do operador.

O sucesso de build, importação ou HTTPS não prova os limites efetivos de uma sandbox
criada pelo pacote. A receita continua fora do setup consumidor. Nenhum código de
produto mudou neste checkpoint; a suíte anterior não foi repetida para estes ensaios
de infraestrutura. A revisão final da frente continua pendente.

## English overview

Native Buildx inside a dedicated microVM built the unchanged Linux AMD64 v3 recipe.
The OCI archive and blobs were verified, and `sbx template load` succeeded. Sandbox
creation requires a trusted HTTPS registry to resolve the descriptor, even with
`--pull never`. Operator-confirmed temporary trust passed; Docker resolved 2 CPUs/4 GiB,
but creation failed in 0.877 seconds because the exact reference was absent from cache.

A local HTTPS test using the prepared certificate explicitly returned the same manifest.
Default trust initially rejected it. The operator later installed the exact approved leaf.
Automatic removal timed out; native `certutil` then removed it with exit 0 and the original
certificate inventory was verified. All temporary
ports and download rules were removed, the original source setting was restored, and
all four owned VMs were observed stopped. The managed builder failure remains historical;
it no longer prevents this native build path.

No model calls, remote publication or native profile admission occurred. R1 remains
partial; networking/MCP, active daemon recovery and suspension still need proof before R2/R3.
Reimporting OCI reference annotations preserved all 21 blobs
but did not confirm the required cache alias. The second operator script then passed with
`--pull missing` for the same local digest and native certificate removal. Creation and
cleanup succeeded; [package checks](2026-10-04-native-package-proof.md#english-overview)
record the measured resources, file protections and three launcher cases.

ATRASO: main 1
