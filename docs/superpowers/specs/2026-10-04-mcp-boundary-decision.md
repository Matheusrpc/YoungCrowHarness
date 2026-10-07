# Decisão aprovada: gateway MCP do runtime

Frente: executor isolado. O mantenedor aprovou a alternativa 2 em 2026-10-04:
“Aprovar inacessibilidade comprovada (recomendado)”. Esta decisão altera somente o requisito
do gateway no desenho do executor; mantém o plano e o método de execução já aprovados.

O desenho original exigia desligar o gateway MCP do host. A documentação atual do Docker afirma que
toda sandbox inicia um gateway; a CLI 0.46.0 oferece modos estático e dinâmico, sem opção
documentada de desligamento. A inspeção das nossas VMs confirmou `mcp_gateway: true`, mesmo
sem servidores registrados. Um pacote v3 próprio não elimina essa condição documentada.
[Fonte do fornecedor](https://docs.docker.com/ai/sandboxes/mcp-gateway/#choose-an-mcp-mode).

Foram avaliadas duas alternativas:

1. **Manter o requisito original.** Esse runtime permanece recusado. Interrompemos o pacote
   dependente dessa garantia e revisamos a escolha do ambiente, sem trocar automaticamente
   de fornecedor ou executar os agentes no host.
2. **Exigir inacessibilidade comprovada para o cliente.** O gateway pode existir na camada
   confiável do gerenciador, mas o processo de IA, seus filhos e o pacote de trabalho não
   podem alcançá-lo. Esta foi a alternativa aprovada para continuar com o ambiente escolhido.

A segunda alternativa muda um requisito de segurança; não é uma conclusão das provas atuais.
Seu aceite exige todos estes controles:

- O cliente recebe somente o ambiente permitido, sem endereço, token, configuração ou
  descritor do gateway; não acessa diretórios, processos ou sockets da camada externa.
- Regras de rede efetivas bloqueiam o gateway por nome e endereço, o host, a rede privada
  e metadata, inclusive quando os destinos do provedor de IA estiverem liberados.
- Uma fixture sem modelo tenta acessar o gateway e os caminhos alternativos conhecidos.
  O ensaio registra recusas e comprova que nenhuma ferramenta MCP foi chamada.
- Qualquer mudança de imagem, versão, proxy, política, credencial ou configuração invalida
  a prova e mantém o perfil bloqueado até nova validação.

O controle de skills/MCPs do harness continua valendo. Esta decisão não registra servidores,
não muda configurações globais, não concede ferramentas ao cliente e não autoriza inferência
antes das demais provas. Autenticação e prazo permanecem pendências separadas.

O validador deve registrar a presença do gateway separadamente do acesso pelo cliente.
Sem prova da fronteira, reporta `mcp_isolation_unverified` e mantém o perfil bloqueado.
Nenhum resultado atual autoriza ferramentas MCP ou chamadas de modelo.

## English overview

The original design required the host MCP gateway to be disabled. Docker documents that
every sandbox starts one, and the installed CLI exposes no documented off switch.
The operator approved the amendment on 2026-10-04: allow the gateway in the trusted manager layer only after
proving it unreachable from the AI client and its descendants, including with provider
network access enabled. New evidence is still required. Until then,
the validator keeps the observed configuration blocked with `mcp_isolation_unverified`.
