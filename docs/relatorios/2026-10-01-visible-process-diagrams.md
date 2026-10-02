# Fluxos de uso visíveis no README

Frente: corrigir a apresentação do processo na main, preservando o design do repositório.

## Problema observado

Na página do GitHub, os diagramas PT/EN estavam dentro de `details` fechados. A inspeção
encontrou dois elementos com `open: false`, chamados “Ver o processo completo” e
“View the complete process”. O leitor precisava abri-los para encontrar as caixas.

## Correção

O README passa a mostrar três SVGs por idioma: começar do zero, adotar um projeto existente
e operar uma entrega. Cada fluxo aponta para os comandos do guia de uso. O fluxo completo
em Mermaid foi preservado em `docs/PROCESS.md`, incluindo pausas, revisão, recuperação e
registro de produção. Os desenhos usam a paleta e a tipografia dos assets existentes.

Os SVGs são documentação inspirada em BPMN. PM e Tech Lead continuam sendo responsabilidades
exercidas durante o trabalho; esta mudança não acrescenta um motor de execução.

## Verificação

- Seis SVGs carregados em Chromium; nenhum texto de tarefa excedeu a largura disponível.
- Inspeção visual das caixas, setas e caminhos de correção, publicação e recuperação.
- XML válido, sem scripts ou recursos externos nos novos SVGs.
- Seis imagens e seis links para abri-las no README; destinos e âncoras conferidos.
- Dois fluxos Mermaid preservados integralmente e nenhum processo recolhido no README.
- Em tela estreita, o diagrama acompanha a largura da página; o link “Abrir diagrama”
  permite ampliar o texto. As imagens também têm descrição textual.

Medição: [resultado das verificações](../medicoes/2026-10-01-visible-process-diagrams.json).
Capturas locais da sessão ficam em `.runtime/process-*.png`. O instalador e suas dependências
não foram alterados. O PR deve passar pelo check obrigatório antes da publicação; depois,
a conferência final deve abrir o README da main no GitHub.

ATRASO: README na main 1 (publicação pendente no momento deste registro)
