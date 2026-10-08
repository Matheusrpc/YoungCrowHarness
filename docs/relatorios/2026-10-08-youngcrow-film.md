# Tutorial do YoungCrow e agente de atendimento da clínica

Frente: tutorial audiovisual. Verificação de 8 de outubro de 2026, sobre `bb9eb48`.

O filme reúne a introdução original de 118 segundos e um novo capítulo de 180 segundos.
São 25 cenas em português, com versões 16:9 e 9:16 recompostas, lettering, Three.js e a arte
de vitrais do repositório. O corvo com medalha de São Bento permanece na arte original.
Magnific não estava disponível; não houve geração ou ampliação atribuída a esse serviço.

## O caso demonstrado

Ana cria um protótipo fictício de atendente administrativo para uma clínica. O roteiro mostra
a conversa paciente/agente, a oferta de horários e a confirmação após a reserva. F1 organiza
o atendimento e encaminha dúvidas clínicas a uma pessoa; F2 consulta disponibilidade e
agenda sem conflitos; F3, cancelamento, permanece no backlog.

Terminal, prompts, features, PBIs, Markdown, código, testes e quadro da missão aparecem na tela.
PM e Tech Lead definem o escopo; Dev implementa; QA revisa em contexto independente, somente leitura.
As sessões são conduzidas pela operadora. O checkpoint precede o esgotamento encenado da cota.
Ana confere o diff, encerra o Codex e abre o Claude no mesmo projeto. A retomada lê os arquivos
salvos, os índices e as fontes atuais; decisões nunca registradas não são recuperadas.

As interfaces, o código, os dados e os resultados são encenados, com aviso permanente no capítulo.
Nenhum agente clínico foi implementado ou colocado em produção para produzir o vídeo.
Não houve chamadas de modelos, execução dos comandos mostrados ou ciclo do executor nativo.
A coordenação automática dos agentes continua em desenvolvimento.

## Prova técnica e visual

| Resolução | Quadros | Duração do contêiner | Bytes |
|---|---:|---:|---:|
| 1920 × 1080 | 7152 | 298.023 s | 90,346,540 |
| 1080 × 1920 | 7152 | 298.023 s | 120,208,616 |

Ambos usam H.264/AAC a 24 fps e trilha instrumental procedural original, sem locução.
Os capítulos foram unidos por cópia do vídeo. Os WAV originais foram reunidos e codificados
em uma trilha AAC contínua, sem sobreposição de timestamps na junção. Os primeiros 2.832 pacotes de vídeo conferem
por SHA-256 com cada original, sem reencodificação. Os MP4 originais permanecem preservados
por hash. As 22 capturas da introdução continuam idênticas às anteriores.

A decodificação integral dos dois MP4 terminou com código 0. As 14 cenas novas em cada formato
passaram pela medição de limite inferior do conteúdo, sem overflow ou erro JavaScript.
Houve inspeção visual de capturas de planejamento, código, checkpoint, troca, QA e conversa.
A revisão encontrou título coberto, prompt fora do painel e indicação de reserva prematura;
os três ajustes foram conferidos antes da renderização final.

A apresentação HTML completa passou reprodução/pausa, seek, teclado, navegação entre capítulos,
navegação até a cena de retomada no Claude, troca de formato e viewport 390 × 844. Seus recursos são incorporados;
via servidor local, foram medidas zero requisições externas e zero erros JavaScript.
A navegação `file://` está bloqueada por política neste ambiente e não foi validada.
Após renderização e QA, a medição de processos dos navegadores desta frente retornou zero.

O fundo decorativo do capítulo novo é atualizado a 6 Hz; textos, cursor e ações têm 24 fps.
As tentativas interrompidas de exportação não são entregáveis. Seus processos foram encerrados
por PIDs identificados da própria task; os vídeos finais passaram por verificação completa.

## Entrega e limites

[Fontes, transcrição e reprodução](../media/youngcrow-guide/README.md).
[Medição do primeiro capítulo](../medicoes/2026-10-08-youngcrow-film.json).
[Medição final, hashes e preservação](../medicoes/2026-10-08-youngcrow-clinic-demo.json).
README e guia de uso foram atualizados em PT/EN. Three.js e fontes incluem suas licenças.
MP4, HTML com base64, ZIP e recibos privados ficam fora do Git, em `.runtime/youngcrow-film/`.
A publicação segue a branch `feat/isolated-executor` e o PR #24 em rascunho; main é preservada.

Esta medição cobre mídia e apresentação. Não encerra a validação do executor. O CI herdado de
`bb9eb48` teve push aprovado e falha no PR em `adoption-windows`, na recuperação de processo/rede;
essa investigação permanece na frente do executor, sem mudança de limites ou aceite nativo.

ATRASO: mídia 0 | executor: validação pendente.
