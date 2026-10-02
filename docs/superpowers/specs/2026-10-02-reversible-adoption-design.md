# Adoção reversível do YoungCrow

Estado: proposta para revisão do mantenedor. Nenhum comando de restauração foi implementado.

## Resultado esperado

Uma pessoa pode experimentar o YoungCrow e recuperar o repositório como estava imediatamente
antes da primeira alteração do harness. Isso inclui mudanças sem commit. O trabalho produzido
durante o teste fica numa cópia de recuperação, mesmo quando a pessoa decide sair.

O pedido é restaurar o repositório inteiro. A proposta assume esse alcance, em vez de tentar
identificar automaticamente quais mudanças posteriores pertencem ao harness ou ao produto.
Configurações globais da máquina, instalações de plugins, serviços externos e publicações remotas
ficam fora da restauração. Essa fronteira precisa aparecer antes do primeiro setup.

## Alternativas consideradas

| Abordagem | Benefício | Limite |
|---|---|---|
| Cópia local verificada antes da adoção | Recupera arquivos, mudanças sem commit e estado local do Git | Exige espaço e pausa de escritores durante a captura/restauração |
| Experimentar em outra cópia do projeto | Mantém o diretório original intocado | A pessoa trabalha em outro caminho; instalações globais ainda precisam de isolamento |
| Commit/tag antes do setup | Usa apenas Git | Não preserva sozinho index, arquivos não rastreados, ignorados e segredos locais |

Recomendação: cópia local verificada. A experiência em outra pasta continua sendo uma opção manual;
um commit isolado não atende ao estado pedido pelo usuário.

## Fluxo proposto

1. O setup valida destino, repositório, espaço e possibilidade de recuperação, antes de escrever no projeto.
2. Captura e verifica um ponto inicial fora do repositório. Se não conseguir verificá-lo, não inicia a adoção.
3. Informa o identificador do ponto e como consultar a prévia de saída. Instala o harness e registra o resultado.
4. Ao pedir a saída, a pessoa recebe uma prévia dos arquivos que voltarão, sairão ou foram criados depois.
5. Antes de restaurar, o comando guarda e verifica uma cópia do estado atual, incluindo trabalho feito no teste.
6. Com confirmação do usuário sobre essa prévia, restaura o ponto inicial e verifica o resultado.
7. Informa onde estão o repositório recuperado e a cópia do teste. Preserva ambos; apagar backups é uma ação separada.

Comandos propostos, ainda indisponíveis:

```text
youngcrow adoption status
youngcrow adoption restore --dry-run
youngcrow adoption restore --confirm PREVIEW_ID
```

Os nomes finais devem acompanhar o padrão Python/Bash do projeto no plano de implementação;
não criar um empacotamento novo apenas para esses exemplos.

## O que precisa ser preservado

- Conteúdo e nomes dos arquivos anteriores, inclusive não rastreados, ignorados e `.env`.
- HEAD, branch local, index e histórico local do Git de um repositório independente suportado.
- Distinção entre alterações preparadas para commit e alterações ainda fora do index.
- Permissões necessárias para uso dos arquivos e executáveis, conforme suporte comprovado da plataforma.
- Ausência original de um diretório, quando o setup iniciar um projeto em uma pasta que ainda não existia.

Não prometer uma imagem do disco: timestamps, donos e ACLs arbitrárias exigem tratamento específico.
Se uma característica necessária não puder ser preservada e restaurada, a preparação precisa recusar
o modo reversível e explicar o motivo. Não pode ignorar arquivos silenciosamente.

O primeiro incremento atende repositórios Git independentes e pastas comuns. Git worktrees com
metadados compartilhados, submódulos, repositórios aninhados e caminhos especiais entram somente
quando houver captura/restauração demonstrada. Detectá-los e recusar antes da adoção é obrigatório.

## Armazenamento e interrupções

O ponto inicial e as cópias de recuperação ficam numa pasta privada fora do repositório, em caminho
explicitamente resolvido e informado ao usuário. Não entram no vault público, Graphify, claude-mem
ou num commit. Podem conter credenciais locais; o armazenamento precisa restringir acesso ao dono.

Um manifesto registra identidade do projeto, versão do formato, conjunto de arquivos, hashes e
estado da operação. Uma nova execução do setup não substitui o primeiro ponto inicial. Se já houver
adoção em curso ou concluída, o comando retoma/verifica seu registro, sem criar um falso “antes”.

A restauração usa estado persistido e recuperação após interrupção. O diretório atual só pode ser
retirado depois da verificação das duas cópias. O plano deve definir a troca de diretórios no mesmo
volume e seu diário de recuperação. Falha ou falta de espaço preserva o trabalho atual. Uma prévia
fica inválida se o projeto mudar antes da confirmação.

O operador precisa encerrar escritores no repositório durante captura e restauração. O comando
confere locks/operações Git e mudanças durante a captura; não promete bloquear editores e processos
externos que não cooperem. Não encerra sessões ou processos do usuário automaticamente.

## Integração com o harness

O ponto inicial deve preceder setup, personalizer e migração. A documentação orienta o mesmo rito
em Claude Code e Codex. O vault registra apenas a existência/identidade da adoção e a próxima ação;
segredos e conteúdos das cópias ficam fora da memória indexada.

O setup atual pode instalar skills/plugins no perfil do usuário. O modo de teste proposto deve
isolar esses componentes ou impedir a instalação global, de forma explícita. `--no-plugins` sozinho
não basta para garantir isolamento das skills de usuário do Claude.

Instalações antigas sem ponto inicial não podem receber uma promessa retroativa de restauração.
Nesses casos, registrar “estado anterior indisponível” e oferecer orientação manual, sem inventar
um baseline a partir do commit atual.

README, guia de uso e caixas do processo devem mostrar: preparar ponto inicial, experimentar,
continuar usando ou revisar saída, guardar trabalho do teste, restaurar e verificar. A funcionalidade
só entra como disponível depois das provas correspondentes.

## Critérios de aceite

| Caso | Resultado exigido |
|---|---|
| Projeto com alterações staged/unstaged, ignorados e não rastreados | Mesmo estado lógico e bytes após retorno |
| Setup repetido ou interrompido | Ponto original preservado e operação retomável |
| Trabalho novo durante o teste | Recuperável na cópia anterior à restauração |
| Falta de espaço, corrupção ou interrupção em cada etapa | Trabalho atual preservado ou recuperação determinística indicada |
| Prévia antiga ou caminho diferente | Restauração recusada antes da troca |
| Links, Git compartilhado ou plataforma não suportada | Detecção e recusa anterior à adoção; nenhum descarte silencioso |
| Repo público | Cópias/segredos nunca entram no Git nem nos índices de memória |
| Projeto sem ponto inicial | Nenhuma promessa de recuperação retroativa |
| Claude Code e Codex | Mesmo resultado de arquivos, sem depender de histórico da conversa |

Próximo passo: revisar este alcance e escrever o plano de implementação com testes de perda de dados,
recuperação de interrupções e isolamento dos clientes antes de adicionar o caminho destrutivo de retorno.
