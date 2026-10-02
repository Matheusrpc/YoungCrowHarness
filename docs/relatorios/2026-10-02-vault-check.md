# Validação local do vault

Frente: conferir metadados e navegação sem modificar memórias.
Data UTC: 2026-10-02. Escopo aprovado pelo mantenedor após o desenho curto na conversa.

`python3 scripts/vault.py check` confere os campos obrigatórios, identidades repetidas, arquivos
referenciados, vínculo de volta pelo microíndice, ciclos de índices e alcance a partir de
`vault/index.md`. A saída identifica arquivo e problema; `--json` permite consumir os diagnósticos
sem incluir o corpo das notas. Não há escrita nem chamadas de rede.

O setup instala o comando nos modos Claude Code e Codex. Repetir a instalação sem force acrescenta
o arquivo novo e preserva notas e guias existentes. README e guia PT/EN documentam a operação e
os limites do reconhecedor. Os assets do design e os seis diagramas visíveis foram preservados.

## Evidências

| Verificação | Resultado |
|---|---|
| Suíte completa local, iniciada antes das duas regressões finais | 72 testes no Windows/Python 3.14: 67 aprovados e 5 skips por privilégio de symlink. |
| Validador após as correções da revisão | 17 testes: 16 aprovados e 1 skip de symlink no Windows. |
| Suíte completa no Linux, revisão `04906fc` | 74 testes: 72 aprovados e 2 skips exclusivos do Windows. [Execução do CI](https://github.com/Matheusrpc/YoungCrowHarness/actions/runs/36952690673). |
| Instalação real em fixtures isoladas | Comando copiado e executado para cada cliente; todos os arquivos preservados byte a byte pela checagem. |
| Vault gerado por personalizer e integrações | 19 notas válidas; arquivos idênticos antes e depois da validação. |
| Vault do repositório | 3 notas, nenhum diagnóstico. |
| README no GitHub | 6 imagens carregadas e visíveis, nenhum processo recolhido; navegador da verificação encerrado. |

Os testes usam dados fictícios, sem plugins reais, credenciais ou chamadas de modelo. A execução
do comando instalado verifica sua disponibilidade no projeto; não substitui testes dos loaders
nativos dos clientes, que não mudaram nesta entrega.

## Revisão independente

A revisão somente leitura encontrou dois problemas importantes: retrocesso excessivo na expressão
de links com barras escapadas e descarte de links em sublistas indentadas. Ambos foram reproduzidos
por testes que falharam antes da correção. A expressão passou a separar as alternativas, e linhas
indentadas passaram a participar da conferência. O caso malformado tem teste com limite de tempo.

Também foram acrescentadas regressões para metadados que continham apenas comentários e arquivos
especiais que poderiam bloquear a leitura. Junctions foram exercitadas no Windows; symlinks, no Linux.

O apontamento menor sobre rótulos com colchetes internos e aberturas escapadas ficou documentado
no guia. O reconhecedor cobre um subconjunto de Markdown: esses casos ainda exigem inspeção manual.
Prosa verdadeira, segredos, evidências de testes, produção, URLs, fragmentos, YAML completo e alterações
concorrentes permanecem fora da checagem. Esses limites coincidem com o escopo estrutural aprovado.

Detalhes: [medição](../medicoes/2026-10-02-vault-check.json) · [guia](../USAGE.md#vault-check-pt).
O [PR #4](https://github.com/Matheusrpc/YoungCrowHarness/pull/4) reúne a implementação e este registro.

ATRASO: main 1 (publicação pendente no momento deste registro; o estado final está no PR).
