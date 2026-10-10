# Consumo local do pacote v3

Frente: executor isolado, 2A-R1. Exceção temporária aprovada pelo operador em
2026-10-04: “Autorizar a exceção temporária (recomendado)”.

## Resultado já observado

Buildx 0.37.1 construiu a receita existente para Linux AMD64 dentro de uma microVM
dedicada. O arquivo OCI tem 599.219.712 bytes, com SHA-256
`b188746044acf545464c89a8f9da4c1b7a40d570483ab0480c5847ace14461b5`.
Manifesto: `sha256:3e6a380a46840656b9e724694ef2964e2d13471bc3dd0fe92ae66492217dfe2f`.
Os hashes dos blobs e os cinco arquivos de entrada foram conferidos. O descritor
preserva `sbx@1` e `resources@1` com 2 CPUs e 4 GiB.

`sbx template load` importou o arquivo, mas o resolvedor de kits ainda procura a origem
OCI, mesmo com `--pull never`. Um registry oficial temporário serviu o mesmo manifesto
na VM de build, com porta exposta somente em `127.0.0.1` no Windows. Nenhum arquivo do
projeto foi montado. Nenhuma imagem foi publicada na internet.

O Docker recusou a criação por sua lista de origens confiáveis: `kit.allowedSources`
aceita atualmente `docker.io/`. A criação da VM do pacote não ocorreu. O registry foi
parado e a porta temporária foi removida, inclusive no primeiro ensaio que encontrou
o serviço ainda sem prontidão HTTP.

## Exceção de origem aprovada

1. Conferir de novo versão/hash do runtime, lista original de origens e propriedade
   da VM de build. Conservar o registro da tentativa recusada.
2. Reabrir somente `127.0.0.1:61831`, encaminhado à porta 5000 da VM de build. Se essa
   porta estiver ocupada, parar; não substituir o serviço que a ocupa.
3. Conferir a prontidão HTTP e o digest exato do manifesto acima.
4. Acrescentar temporariamente apenas `127.0.0.1:61831/youngcrow-diagnostic/` à lista
   `kit.allowedSources`, preservando todas as entradas originais. Não usar curingas.
5. Criar o kit pelo digest, sem workspace, skills, portas ou rede na VM do pacote.
   Conferir UUID, imagem, recursos efetivos e hashes dos arquivos. Nenhum cliente de
   IA será iniciado; o catálogo de perfis continua vazio.
6. Em `finally`, restaurar a lista original, remover a porta e parar o registry por
   ID/imagem/nonce. Verificar o estado final. Preservar as VMs e os recibos para retomada.

A exceção altera temporariamente uma configuração global de confiança do Docker.
Ela não muda a política global de rede, não habilita MCP, não aprova perfil de execução,
não autentica modelos e não autoriza publicação remota. Se a lista de origens mudar
durante o ensaio, interromper a criação e preservar a mudança alheia ao reconciliar.

## Aceite

Sucesso exige consumo do kit v3 com seu descritor aplicado, integridade dos arquivos
e retirada comprovada da exceção/porta. Um retorno 0 do importador sozinho não basta.
Depois disso ainda faltam rede/MCP, reinício do daemon, suspensão, R2 e provas autenticadas.

## Resultado da execução autorizada

A entrada exata foi aceita. A criação terminou com código 1 porque o resolvedor tentou
HTTPS contra o registry HTTP. Nenhuma VM do pacote foi criada. A lista voltou à origem
`default` e ao valor `["docker.io/"]`; a porta foi removida e o registry parado com PID 0.
O [relatório](../../relatorios/2026-10-04-native-kit-build.md) registra também a retirada
das quatro regras de download da VM de build e as quatro VMs próprias paradas.

## Certificado TLS temporário — autorizado

O operador pediu para prosseguir (“bora p?”) após a solicitação específica. Essa
autorização abrange o certificado, escopo, limite e reversão descritos abaixo.

O registry agora foi preparado com HTTPS, armazenamento somente leitura e certificado
de servidor para `127.0.0.1`. O teste com esse certificado explicitamente fornecido ao
cliente recebeu o mesmo manifesto; a confiança padrão o recusou. Nessa preparação,
nada foi instalado nos repositórios de certificados do Windows.

- Certificado DER SHA-256: `c6b2a8614a34ad4f83f4f9a5ad3328d28df1e715b63eca3dbfb5c3dc91c883a7`.
- Thumbprint: `CDD89D73080C1A54FF4B817F4DBEBADF210F34CB`.
- SAN: somente IP `127.0.0.1`; Basic Constraints crítico `CA:FALSE`; EKU `serverAuth`.
- Validade: 2026-10-04 22:18:33 UTC até 2026-10-05 22:18:33 UTC.
- Chave privada: root/0600 na VM de build; nunca copiada para o host.

A proposta é confiar temporariamente **nesse certificado exato** em
`Cert:\CurrentUser\Root`, reabrir somente `127.0.0.1:61831` e reaplicar a origem já
aprovada para uma tentativa de criação por digest, limitada a 120 segundos.
O inventário e a intenção devem ser persistidos antes da inclusão. Se o certificado
já existir, estiver vencido ou o estado divergir, não incluí-lo nem substituí-lo.
Não alterar `LocalMachine`, desabilitar validação TLS, instalar uma CA genérica ou
reiniciar o daemon para tentar passar.

Ao terminar ou falhar: remover somente o certificado incluído por este ensaio, conferindo
thumbprint e bytes DER; restaurar a origem sem sobrescrever mudanças alheias; fechar a
porta; parar o registry; verificar o inventário final. Uma interrupção do controlador
exige reconciliar o registro persistido antes de qualquer retomada.

Essa confiança afeta os aplicativos do usuário durante o teste, além do Docker. A
aprovação foi solicitada separadamente porque a autorização anterior permitia **somente
acrescentar a origem à lista do Docker**. Se o runtime não reconhecer o certificado sem reinício,
registrar a falha e restaurar tudo. A proposta não garante que a criação passará nem
aprova o perfil do executor.

## Preparação: confirmação indisponível no terminal do agente

A preparação encontrou duas esperas ao usar a API de certificados e `certutil`; os
processos próprios foram encerrados e a ausência do certificado foi conferida. O CLI
também devolveu uma publicação de porta duplicada; o diário do daemon e a leitura da
configuração permitiram reconciliar somente o binding exato, que foi retirado.

O cmdlet `Import-Certificate`, após carregar explicitamente o módulo nativo que fornece
`Cert:`, retornou “Interface do usuário não permitida nesta operação”. Nenhuma tentativa
chegou ao comando de criação da sandbox. A confiança permaneceu ausente; inventário,
origem e política foram preservados; registry e quatro VMs próprias terminaram parados.

O ensaio foi preparado para o PowerShell normal do operador, sem administrador. Ele
herda o console para que `certutil` possa apresentar a confirmação do Windows: até 90
segundos para essa interação e até 120 segundos para a única tentativa de criação.
O certificado exato, sua validade e ausência são conferidos antes da inclusão. A
retirada usa a mesma conferência de identidade, com verificações independentes para
certificado, origem, porta e registry. Erros ficam registrados e impedem anunciar sucesso.
A preparação terminou antes da execução no terminal do operador.

## Resultado do operador e correção do consumo local

O ensaio de 2026-10-04 às 23:35 UTC confirmou o certificado e resolveu o descritor
com 2 CPUs/4 GiB. A única criação retornou 1: `pull_policy=never` exigia a referência
exata no cache. Nenhuma sandbox pelo pacote foi criada. A remoção `.NET` excedeu 15 s;
o certificado ficou instalado até a reconciliação com `certutil -user -f -Silent -delstore`.
O comando retornou 0 e o inventário original foi restaurado. O recibo anterior é preservado.

Reimportar a referência no índice OCI não confirmou o alias na listagem do cache.
O script corrigido usa `--pull missing` para buscar o mesmo digest somente no registry
HTTPS aprovado. Ele conserva os limites de 90 s para confirmação e 120 s para uma criação,
registra um novo recibo e usa a remoção nativa já comprovada. A repetição do mesmo script
com recibo existente é recusada. A inclusão continua exigindo o PowerShell do operador;
nenhuma nova inclusão foi feita durante a correção. Se o certificado vencer, interromper.
Esse preparo manteve política de rede e perfis inalterados.

## Consumo concluído

O operador executou o ensaio corrigido às 00:08 UTC de 2026-10-05. `--pull missing`
criou a sandbox em 4,872 s; digest esperado, 2 CPUs/4 GiB e nenhuma montagem do projeto.
Certificado removido, inventário original restaurado, origem e porta revertidas, registry
parado/PID 0; nenhum erro de limpeza. O [relatório do pacote](../../relatorios/2026-10-04-native-package-proof.md)
registra as verificações seguintes. Essa exceção temporária terminou; não integra o setup
consumidor e não habilita perfil nativo. Próximo ensaio não requer certificado.

ATRASO: main 1
