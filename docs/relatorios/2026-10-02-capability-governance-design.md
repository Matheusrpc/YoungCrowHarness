# Governança de capacidades — preparação do desenho

Frente: governança de skills, agentes e MCPs. A proposta está em
[capability-governance-design](../superpowers/specs/2026-10-02-capability-governance-design.md).
É uma alteração documental, sem novo controle de execução ativo.

## Contexto recuperado

Base inspecionada: main `16191ec`, PR #7 integrado. O vault local registra a memória consultável,
seu estado publicado e o aceite M04 parcial. Não havia seleção de notas neste projeto: `memory.py`
retornou `selection_missing` e ofereceu os índices. A retomada seguiu esses índices, sem construir
um grafo nem ampliar automaticamente a seleção.

Foram lidos o catálogo, `skills-lock.json`, as configurações nativas dos dois clientes, o setup,
os testes de descoberta e a direção aprovada do produto. O catálogo ainda é documental; o
instalador fixa humanizer, mas não resolve versões imutáveis de todos os plugins. A proposta
separa identidade declarada, configuração observada e prova de uso.

Claude Code 2.1.220 retornou `loggedIn: false`. Codex CLI observado: 0.158.0-alpha.2.1. Foram
consultadas apenas informações de versão, ajuda e autenticação; nenhum MCP foi iniciado e nenhuma
nova sessão de modelo foi executada. O orçamento da prova anterior não foi renovado implicitamente.

## Referências e ingestão

As cinco páginas oficiais citadas no desenho foram abertas e consultadas. O runtime Docling
2.132.0/Python 3.12.10 existente passou no diagnóstico. A ingestão das cinco URLs terminou em
`failed`, aviso `incomplete_conversion`; originais e recibos foram preservados localmente.
Nenhum Markdown dessas conversões foi apresentado como pronto.

Uma reprodução diagnóstica com os mesmos bytes da página Codex MCP identificou `SimplePipeline`:
`Path traversal blocked: '/llms.txt' resolves outside base directory`. Isso confirma a causa
nessa fonte; a causa interna das outras quatro falhas ainda não foi isolada. Não se removeu a
proteção de caminhos, não se habilitou acesso externo durante conversão e não se alterou o adapter.
A leitura direta das páginas fundamenta o desenho; o problema de ingestão fica registrado para
correção e nova prova antes de depender dessas extrações no vault.

## Revisão do documento

O desenho compara três abordagens e recomenda catálogo verificável com controles nativos.
O primeiro incremento cobre descoberta local, auditoria sem efeitos colaterais, pacote privado de
revisão e provas por cliente. Não instala plugins nem acrescenta um serviço central. A aplicação
de configuração segue a autorização já dada pelo operador, preservando o que existir.

A revisão conferiu escopo, migração do manifesto, privacidade, diferença entre autorização e hash,
configurações herdadas, permissões desconhecidas, revogação e critérios G01–G09. Recursos presentes
na documentação atual precisam ser verificados nas versões instaladas antes de virarem suporte
anunciado. Nenhuma revisão por subagente foi aberta nesta etapa documental.

README PT/EN atualizado com a proposta; o desenho da fundação foi corrigido para refletir a
publicação do PR #7. Os diagramas operacionais existentes foram preservados. Não houve alteração
de código que justificasse repetir a suíte de produto local; os checks documentais e o CI do PR
registram a validação desta etapa.

Próxima ação: revisão do desenho pelo mantenedor e, depois, plano de implementação. A falha
reproduzida de HTML precisa de uma correção delimitada, com regressão e prova real, antes de usar
essas fontes convertidas como evidência. M04 de memória continua parcial.
