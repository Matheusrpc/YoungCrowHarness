# Piloto público: da ideia à publicação

Frente: exemplo reproduzível do YoungCrowHarness. Data: 2026-10-03.
Estado: desenho aprovado pelo mantenedor em 2026-10-03 pelas respostas “Próximo” e “Aprovado”.
Aplicação e publicação ainda não implementadas. O [plano de implementação](../plans/2026-10-03-public-pilot.md)
detalha as entregas e suas verificações.

## Objetivo e contexto confirmado

O público inicial são desenvolvedores individuais e pequenos times com Claude Code e Codex.
O mantenedor quer demonstrar projeto novo, migração, memória por índices, qualidade de código,
documentação, publicação e retorno ao estado anterior à adoção. README e guia devem acompanhar
as entregas em PT/EN, preservando o design atual. Fontes ingeridas ficam locais até revisão.

A frente anterior comprovou ingestão e retomada no Claude e foi publicada pelo
[PR #15](https://github.com/Matheusrpc/YoungCrowHarness/pull/15). Falta um exemplo público que una
as etapas numa entrega de produto. O ensaio anterior do personalizer usou uma agenda Python local;
não exercitou produção. Esta proposta não chama esse ensaio de aplicação publicada.

Sucesso: um visitante consegue abrir a demonstração, percorrer a feature até suas decisões e provas,
reproduzir o roteiro em uma pasta própria e entender onde a IA precisa de contexto ou autorização.

## Aplicação proposta e alternativas

A aplicação aprovada é um **quadro de entregas**: página com lista de features, filtro por
estado e detalhes de aceite e evidências públicas. A aprovação do desenho confirma essa opção.

| Opção | O que demonstra | Consequência |
|---|---|---|
| Quadro estático com filtros, recomendado | Feature visível, testes, revisão, deploy e navegação para o vault | Publicação de arquivos estáticos; dados de demonstração revisados |
| API de tarefas | Contratos HTTP e testes de servidor | Acrescenta hospedagem de processo e decisões de operação |
| Projeto real do mantenedor | Adoção com restrições reais do produto | Exige selecionar o projeto e conferir permissões e dados publicáveis |

O quadro usa dados fictícios identificados como demonstração. A revisão da aplicação publicada
é real e aparece separada dos estados fictícios das features. A página permite consultar e filtrar;
alterações nos dados passam por arquivos e PR. Autenticação, edição colaborativa, banco e serviço
de IA em produção ficam fora desta entrega.

## Arquitetura e fronteiras

`examples/delivery-board/` guarda HTML, CSS, módulos JavaScript, dados de demonstração e testes
do exemplo. A aplicação funciona com servidor estático. Node 24 executa testes pelo runner nativo;
não se acrescenta dependência de Node ao instalador do harness. O ambiente atual tem Node 24.15.0.
O gerador do pacote usa biblioteca padrão e uma lista explícita de arquivos permitidos.

Um vault público do exemplo, sob `examples/delivery-board/vault/`, contém perfil, entrevista,
feature, decisão, integração, execuções e operação. Sua identidade pertence ao exemplo. Ele será
validado separadamente do vault do template; o setup do harness não o copia para outros produtos.
Os scripts comuns continuam vindo do setup existente, sem cópias concorrentes para manutenção.

O navegador recebe somente dados públicos do exemplo. Ele não percorre o vault local, transcrições,
recibos ou diretórios operacionais. Links de evidência apontam para notas públicas revisadas no GitHub.
Falha ao carregar dados apresenta mensagem de erro; filtro vazio apresenta um resultado vazio legível.
Texto dos dados é inserido como texto, sem interpretar HTML. Links externos aceitam apenas destinos
HTTPS revisados; esquemas executáveis e caminhos privados são recusados na preparação do pacote.

O layout usa a paleta e a linguagem visual existentes: fundo escuro, texto claro, gemas e títulos
serifados. O README mantém seus assets atuais. Controles precisam de rótulos, foco visível e navegação
por teclado; o estado não depende só de cor. A demonstração deve funcionar em tela estreita.

## Rito demonstrado

1. **Descoberta.** O personalizer registra problema, público, limites, respostas confirmadas e hipóteses.
   O modo de adoção é decidido antes das primeiras notas no consumidor.
2. **Definição.** A responsabilidade de PM produz aceite; a de Tech Lead divide a listagem e o filtro
   em entregas pequenas, com decisão de arquitetura e comandos de teste.
3. **Implementação.** Testes pertinentes antecedem a lógica. Cada incremento atualiza código, README
   do exemplo, documentação afetada e execução no vault.
4. **Revisão.** Um revisor independente compara diff, aceite e evidências. Capacidades usadas ficam
   separadas das disponíveis ou apenas recomendadas. PM e Tech Lead continuam sendo papéis do rito.
5. **Publicação.** Uma revisão aprovada entra na main protegida. O pacote público passa pelas verificações
   antes do deploy. URL, revisão, execução e observação externa ficam na nota de operação.
6. **Retomada.** Uma sessão nova encontra a feature pelos índices e explica o que está em desenvolvimento,
   o que foi publicado, quais provas sustentam isso e qual é a próxima ação.

O quadro e seu roteiro são um exemplo de consumo do harness. Não acrescentam um orquestrador autônomo.

## Projeto novo, migração e retorno

Os dois percursos usam consumidores descartáveis, com raízes e backups privados no mesmo volume,
fora de outros repositórios Git. O repositório do mantenedor não é alvo de restauração.

- **Novo:** destino inexistente, `setup --trial --client both`, personalização, primeira entrega e retomada.
  A saída deve restaurar a ausência original e preservar o trabalho do experimento na recuperação.
- **Existente:** cópia da versão inicial da aplicação, com Git e instruções próprias, antes da adoção.
  Registrar revisão e estado inicial; instalar o trial, auditar e adaptar sem substituir configurações
  próprias. Implementar a segunda pequena entrega. O retorno deve conferir arquivos, alterações
  preparadas e não preparadas no Git, e recuperação do trabalho feito durante o trial.

Reutilizar os mecanismos de `smoke_adoption.py` e do executor externo. O roteiro apresenta a prévia
antes da confirmação. A confirmação automática do ensaio vale exclusivamente para essas fixtures
descartáveis; um consumidor real revisa seu próprio digest. A restauração do diretório não reverte
publicações, perfis globais ou dados de serviços externos.

## Publicação proposta

O destino proposto é GitHub Pages no próprio repositório público. A consulta ao endpoint Pages
retornou 404 nesta sessão; não existe configuração recuperada que permita afirmar site habilitado.
Nenhum site foi criado durante o desenho.

Seguir o [fluxo oficial de Actions e Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages):
preparar e enviar o artefato, depois executar deploy dependente da validação, no ambiente `github-pages`.
Permissões de publicação ficam só no job de deploy; ações serão fixadas por commit verificado durante
a implementação. PRs validam o exemplo sem receber permissões de publicação. Deploy usa uma revisão
aprovada da main e envia apenas o pacote do exemplo.

O pacote inclui um manifesto com revisão Git e hashes dos arquivos. A verificação externa lê a URL
retornada pelo deploy, confere o manifesto e exercita o filtro. Produção só muda para verificada
depois disso. Falha mantém explícito o último estado observado. Se houver uma revisão publicada
anterior, o retorno republica seu artefato/revisão e exige nova observação; na primeira publicação,
sem versão anterior, o procedimento é retirar a demonstração e registrar a causa.

## Memória, integrações e capacidades

As notas têm UUID, origem, data, índice e vínculos entre perfil, feature, decisão, revisão e operação.
O resumo da feature será conciliado explicitamente com cada execução concluída. A próxima sessão
consulta o índice, o microíndice e suas fontes, sem carregar o histórico inteiro.

A documentação de Pages entra pelo Docling na área privada do harness. O registro público da
integração contém URL oficial, decisão própria e contrato revisado; nenhuma transcrição privada
entra no pacote. A fonte deve ser relacionada à frente e permanecer acessível por seu microíndice.

Catálogo e auditoria identificam as skills necessárias. MCP externo não é requisito desse exemplo;
os existentes ficam preservados e desativados quando não forem necessários. Registrar zero uso de
MCP é um resultado válido. Graphify é opcional, sobre seleção explícita; claude-mem segue fora deste
piloto. Não há API adicional de IA ou instalação global necessária à demonstração pública.

## Aceite e fechamento

| ID | Evidência exigida |
|---|---|
| P01 | Aplicação lista e filtra dados; testes cobrem combinação sem resultados, retorno à lista completa e tratamento de dados inválidos |
| P02 | Navegador confere fluxo, teclado e tela estreita; processos abertos pelo ensaio encerrados |
| P03 | Setup real em destino novo e adoção existente, com registros recuperáveis e configurações preservadas |
| P04 | Retorno em ambos os consumidores confere o ponto inicial e preserva o trabalho do trial |
| P05 | Vault público navegável, links válidos, resumo conciliado e distinção de DEV/produção |
| P06 | Uma sessão nova de cada cliente recupera feature, decisão, revisão, evidência e próxima ação sem receber as respostas no prompt |
| P07 | CI valida testes e pacote; conteúdo privado e arquivos fora da lista permitida não são publicados |
| P08 | URL pública e manifesto correspondem à revisão aprovada; produção registrada com data e evidência |
| P09 | README principal e guia PT/EN ligam demonstração, roteiro e limites, preservando o design e os processos visíveis |

As provas com clientes usam a assinatura existente e teto declarado antes das chamadas: proposta
de até uma sessão nova de cada cliente, 300 segundos e 24 ferramentas por sessão, sem API adicional.
Uma nova tentativa exige novo limite declarado e conserva o resultado anterior. Revisão independente
usa o mecanismo de subagente da sessão, com um único escritor no checkout.

Esta entrega termina com P01–P09 comprovados no escopo medido. Falha em publicação ou em um cliente
fica pendente, sem fechar o piloto como entregue. Depois vem o fechamento da primeira release do
harness: versão, requisitos e roteiro de adoção consolidados. Novas integrações de memória e
orquestração autônoma não ampliam o escopo deste piloto.

## Decisões confirmadas

O mantenedor aprovou o quadro estático em `examples/delivery-board/`, o vault público do exemplo,
consumidores descartáveis para adoção/retorno e GitHub Pages como destino. A execução permanece
na sessão atual, com um escritor e revisão independente ao final. A aprovação do desenho permite
detalhar o plano; nenhum código de produto ou recurso de publicação foi criado nesta etapa.
