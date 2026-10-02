# Personalizer: da ideia à primeira entrega

Frente: personalizer e adoção, aprovada pelo mantenedor junto ao fluxo proposto na conversa. Público: desenvolvedores individuais e pequenos times usando Claude Code e Codex.

## Comportamento

A skill `personalizer` lê o contexto disponível, identifica projeto novo ou existente, entrevista o operador e registra respostas, fontes, hipóteses, conflitos, decisões e perguntas abertas no vault. Perguntas dependentes aguardam suas premissas; o operador pode pausar e retomar sem repetir respostas. Dúvidas que dependem de observação produzem uma investigação delimitada. O perfil pode permanecer incompleto enquanto uma entrega independente já tem informações suficientes.

Em projeto existente, o agente primeiro inventaria código, testes, instruções, skills/MCPs/hooks, design e documentação. Distingue observação, intenção documentada e desconhecido. Registra comandos divergentes e resultado de verificações autorizadas. Preserva arquivos existentes; adaptações de `CLAUDE.md`/`AGENTS.md` são edições pontuais com diff e verificação. A skill não promete auditoria estática completa, reparo automático nem configuração universal de fornecedores.

O resultado inclui perfil do produto, entrevista retomável, auditoria quando aplicável, plano de adoção, responsabilidades, capacidades necessárias, comandos reais de verificação e política de publicação. A primeira feature recebe entregas pequenas, aceite, dependências, decisões e estados distintos de desenvolvimento e produção. PM e Tech Lead são papéis do processo; esta entrega não instala uma equipe autônoma de agentes.

## Arquivos e comandos

- `scripts/personalize.py init --mode new|existing --run <id>` cria notas sem substituir dados. Modo existente acrescenta `vault/product/audit.md`. Uma retomada reutiliza o modo persistido; alternância conflitante falha antes de escrever.
- `scripts/personalize.py feature --slug <id> --run <id>` prepara o microíndice da feature, plano de entregas e registro da execução depois de iniciar o perfil.
- `vault/product/index.md`, `profile.md`, `adoption.md`, `interviews/<id>.md`: contexto e personalização.
- `vault/features/`, `vault/decisions/`, `vault/operations/`: índices e registros ligados ao produto. `vault/project.json` mantém a identidade já usada pelas integrações.
- Skill compartilhada `skills/personalizer/SKILL.md`, referência de entrevista e entradas `.claude/skills/personalizer/` e `.agents/skills/personalizer/`.

Os comandos organizam arquivos; o agente conduz entrevista, auditoria e edições autorizadas. Não haverá parser de linguagem natural, serviço novo nem instalação de dependências. O CLI reutiliza validação de caminhos, UUIDs e formatação de notas do núcleo de integrações. Links e novas notas devem ser validados antes das escritas; repetir comando não apaga conteúdo. Cada projeto tem um escritor por checkout.

## Documentação e fluxo

README PT/EN atualizado em toda implementação, com revisão humanizer e preservação do vitral, gemas, tipografia e paleta. Um diagrama Mermaid inspirado em BPMN mostra responsáveis, início/fim, tarefas, decisões e retorno para correção. É a representação do rito assistido; não um motor BPMN ou um fluxo de deploy automático.

Fluxo: ideia → projeto novo/existente → entrevista ou auditoria → perfil e adoção → primeira feature → entregas → implementação/testes/documentação → revisão → correção ou entrega verificada → publicação, se fizer parte do escopo autorizado → evidência e memória → próxima sessão. Gate pendente preserva estado e termina a sessão. Falha de deploy exige recuperação e nova verificação; conclusão local não comprova produção. Graphify/claude-mem automáticos seguem pendentes.

## Aceite

1. Ambos os clientes descobrem a skill e recebem os arquivos necessários.
2. Novo projeto e migração criam navegação válida, IDs únicos e notas preservadas ao retomar.
3. Conflitos de modo/caminho e links redirecionados não produzem escrita parcial previsível.
4. Uma entrevista interrompida retoma pelas notas; uma divergência de comandos não vira evidência de teste.
5. Um projeto piloto percorre uma pequena feature com teste, revisão, README e memória; produção permanece desconhecida sem evidência.
6. README e guia descrevem comandos atuais e limites, com fluxo renderizável e acessível em PT/EN.

Referência de entrevista: [grill-me, AI Hero](https://www.aihero.dev/skills-grill-me), consultada em 2026-10-02 UTC. O personalizer é uma implementação própria com persistência; não instala nem copia a skill externa.
