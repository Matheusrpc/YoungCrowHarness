---
id: "2dc50f58-624a-5e75-bc51-dbec4d93d6a3"
type: "run"
title: "Implementação do piloto"
origin: "youngcrow/public-pilot"
updated: "2026-10-03T12:24:54.296Z"
index: "../index.md"
---

# Implementação do piloto

[Feature](../index.md) · [Entregas](../delivery.md) · [Capacidades](../../../capabilities/index.md)

2026-10-03. Revisão inicial do harness: 91d420a59cd2d3cfd83eb2a0b8371f21e833efad.
Executor: Codex, Windows, um escritor na branch do piloto. Plano aprovado pelo mantenedor.

Task 1: teste Node executado antes do módulo, falhou por módulo ausente; depois 4 testes passaram.
Comando: `node --test examples/delivery-board/tests/model.test.mjs` na raiz do harness.
Cobertura: combinação de filtros/vazio/limpeza, imutabilidade, contrato, links permitidos e dados reais.
Personalizer e integrations criaram o vault deste exemplo com identidade independente.

Baseline de helpers: 8 testes personalizer e 22 vault passaram, com um skip de plataforma em cada.
Não confundir esse baseline com a prova de adoção da aplicação. A revisão estava pendente nesta etapa; o resultado final está no relatório público.
Skills lidas/usadas pelo executor: executing-plans, test-driven-development, karpathy, ponytail,
humanizer, personalizer, retrieve-memory e integrate-from-docs. Nenhuma conversa nativa nova nesta etapa.
MCP externo: zero. Graphify e claude-mem: não usados. README e guia acompanham a entrega.

Durante a implementação: página e modelo verificados localmente; produção ainda não observada.
Naquela etapa, próxima ação: retomada nativa. Consulte [a prova nativa](native-memory.md) e a [operação atual](../../../operations/index.md).

Task 2: primeiro navegador recebeu HTTP 404 antes da página existir. Depois o ensaio em Edge headless
verificou 1280px/360px, combinação/vazio/limpeza, Tab/Shift+Tab/Enter/Espaço, foco, HTML literal
e falhas HTTP/JSON/rede. Capturas inspecionadas; zero processos próprios ao fim, servidor encerrado.
O servidor de prova usou Node e Playwright já disponível no host. Não se adicionou dependência ao projeto.
Links externos apontam à main; disponibilidade real será conferida após integração.
Vault validado: 20 notas, zero problemas. README e guia PT/EN atualizados com humanizer.

Task 3: gerador testado após falha por módulo ausente. Oito testes Node: sete aprovados e um
skip de symlink de arquivo por falta de privilégio no Windows; Linux precisa exercitar esse caso.
O ensaio cria arquivos privados sintéticos ao lado da aplicação e confirma que apenas seis arquivos
e o manifesto chegam ao staging. Destino existente é preservado; hardlinks e dados inválidos são recusados.
A página recupera uma revisão válida do manifesto e conserva a prévia quando ele é inválido.
Prova de navegador passou novamente, com processos próprios zerados. Workflow de CI preparado;
o resultado remoto está registrado abaixo. O manifesto não é assinatura nem autorização.

Task 4: Windows/Python 3.14.4/Git 2.54.0, perfil both. Setup real em destino ausente e Git
existente; ambas as restaurações confirmaram árvores, Git e cópias do trabalho do trial. Perfil global
inalterado; 4 testes Node e auditoria de capacidades com código 0 em cada consumidor.
A configuração própria e os prefixos das instruções/README foram preservados na migração.
O script copiou a versão canônica e usou helpers reais; não chamou modelos nem simulou conversa nativa.
A prova Linux também passou no CI. O README contém os três percursos e limites do retorno.

CI Linux em 2026-10-03T12:04:10Z: [job public-pilot](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/37121661946/job/111198803858),
revisão de merge de teste f2610c15bfad52133d3921f770f7e03b18f0a7d1.
Oito testes Node passaram sem skips, incluindo symlinks. Vault: 20 notas, zero problemas.
Setup e retorno passaram em ambos os modos, com trial preservado e perfil global inalterado.
Python 3.12.3, Git 2.55.0, Node 24.21.0. Zero chamadas de modelo nesse ensaio.
