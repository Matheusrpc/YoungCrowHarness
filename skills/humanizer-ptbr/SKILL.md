---
name: humanizer-ptbr
description: Juiz de texto em português do Brasil. Julga qualquer texto final que uma pessoa vai ler (e-mail, página, laudo, documento, legenda) e devolve uma punch list com o trecho, o padrão ferido e a reescrita. Adaptação PT-BR do humanizer 3.0.0 (blader/humanizer, MIT). Use quando o texto está em português; para inglês, use o `humanizer`.
---

# humanizer-ptbr

Adaptação em português do `humanizer` (blader/humanizer 3.0.0, commit `9862685f`, MIT), que o
`setup.sh` deste harness instala ao lado em `~/.claude/skills/humanizer`. O original julga em inglês;
este arquivo vale quando o texto está em português. São 25 padrões numerados.

## O que este juiz faz

Entrada: um texto final que uma pessoa vai ler. Saída: punch list, um item por achado, cada um com o
trecho literal, o padrão que ele fere e a reescrita proposta. Quem chama conserta e rejulga, no máximo
duas voltas. O juiz não inventa fato: se a reescrita precisa de um dado que o texto não tem, ele pede o
dado ou escreve a frase mais simples, e registra a pendência no item.

Três recusas duras:

1. Travessão e meia-risca reprovam. Nenhum `—` nem `–` no texto final, nem o ` -- ` que faz as vezes
   deles. Trocar por ponto, vírgula, dois-pontos ou parênteses, ou reescrever a frase. Hífen de palavra
   composta fica. Dentro de bloco de código, comando, caminho e URL fica tudo como está.
2. Fabricação de fato reprova. Nome, número, data, citação, fonte, prêmio ou veículo que não esteja no
   material de origem não entra, nem para ilustrar. Falta o dado: peça, ou escreva menos.
3. Resíduo de conversa reprova (padrão 22). É o mais certo da lista e o mais fácil de deixar passar
   quando embrulha conteúdo bom.

## Como julgar

1. Ler o texto inteiro uma vez e marcar os achados, do mais forte para o mais fraco. Olhar também a
   forma do parágrafo: contraste partido em duas frases, três exemplos paralelos e o mesmo fecho depois
   de cada seção são o mesmo padrão em escala maior.
2. Cada frase que fica tem de acrescentar algo. Um padrão pesa na medida em que um escritor cuidadoso
   dificilmente o faria de propósito. Os padrões estão em ordem: 1 a 5 justificam edição com uma
   ocorrência; os marcados *fraco sozinho* precisam de companhia no mesmo trecho.
3. Reescrever mantendo toda afirmação sustentada. Pode encurtar, juntar e partir parágrafo. Não pode
   acrescentar fato, nome, número, data, citação ou fonte que não venha da origem.
4. Reler em voz alta. Depois procurar os cinco que sobrevivem a quase toda reescrita: contraste
   «não X, e sim Y», fecho de uma linha, travessão, tríade, rótulo em negrito.

### Voz

Com amostra de quem assina (textos já aprovados, guia de marca), a amostra manda: comprimento de frase,
vocabulário, pontuação, aberturas. A amostra vence inclusive a regra do travessão se a pessoa escrever
com travessão, exceto onde um contrato proíbe (documento formal, e-mail transacional, laudo).

Sem amostra, a voz vem do tipo de texto. Página, e-mail e legenda podem ter opinião e humor. Referência,
técnico, fiscal e jurídico ficam neutros e diretos.

## A. Encenar em vez de dizer

Agem com uma ocorrência.

### 1. «Não X, e sim Y»
**Olhe para:** não é X, é Y; não apenas X, mas Y; mais do que X, é Y; não se trata de X, e sim de Y; a
forma invertida «X, e não Y»; o contraste partido em duas frases; a cauda negativa curta («…, sem
adivinhação»).
**Problema:** a metade negativa nomeia algo que ninguém afirmou, só para a positiva parecer maior. Diga
direto. O contraste fica quando a metade negativa corrige uma crença real do leitor.
**Antes:** «Não é só um relatório, é uma decisão.»
**Depois:** «O relatório decide o que entra na próxima rodada.»

### 2. Fecho de uma linha e fragmento dramático
**Olhe para:** parágrafo de uma frase que repete o anterior; «É isso que importa.»; «Leia de novo.»;
o mesmo fecho depois de várias seções; fileira de fragmentos («Sem enfeite. Sem desculpa.»); palavra em
CAIXA ALTA para dar peso.
**Problema:** a linha pede uma pausa em vez de acrescentar. Uma frase curta vale quando traz fato novo.

### 3. Dito que soa profundo
**Olhe para:** a verdadeira questão é, no fundo, o que realmente importa, fundamentalmente, o cerne da
questão, X é o Y de Z, X vira uma armadilha, X não é ferramenta, é espelho, a linguagem de, a moeda de.
**Problema:** um ponto comum vestido de verdade escondida. Troque o dito pela afirmação específica.

### 4. Aquecimento antes do assunto
**Olhe para:** vamos direto ao ponto, vamos explorar, vamos destrinchar, aqui está o que você precisa
saber, sem mais delongas, sinceramente?, olha, a questão é a seguinte, vou ser honesto.
**Problema:** anuncia-se o assunto em vez de tratá-lo. Tire o aquecimento inteiro.

### 5. Discutir com ninguém
**Olhe para:** não se trata de, não estou dizendo que, para deixar claro, não me entenda mal, alguns
diriam que… mas, uma abordagem tentadora seria, seria fácil apenas.
**Problema:** o texto responde a uma objeção que não aparece em lugar nenhum. Corte a defesa. Fica a
objeção que o texto atribui e responde inteira.

## B. Ritmo por regra

### 6. Tríade forçada
Ideias em três para soar completo. Cada item tem de trazer ideia distinta; se não trouxer, junte,
desenvolva o mais forte ou varie a estrutura.

### 7. Aberturas repetidas
Várias frases seguidas começando pelo mesmo sujeito. Junte as frases, mude o sujeito ou comece pela
ação. Repetição de propósito, por ritmo, fica.

### 8. Travessão como conector universal
Regra dura: o texto final não tem travessão (`—`) nem meia-risca (`–`), inclusive os espaçados e o
` -- `. Troque por ponto, vírgula, dois-pontos ou parênteses, ou reescreva. Travessão dentro de bloco
de código, comando, caminho e URL fica. Travessão de diálogo em ficção também fica.
**Antes:** «A nova política — anunciada sem aviso — afeta milhares.»
**Depois:** «A nova política, anunciada sem aviso, afeta milhares.»

### 9. Ressalvas empilhadas
**Olhe para:** é possível que, pode eventualmente, talvez seja possível argumentar, em alguns casos pode.
Uma ressalva por afirmação, quando a origem a sustenta. *Fraco sozinho.*

### 10. Locução estrangeira e composto ao pé da letra
«orientado-a-dados», «cliente-facing», «ponta-a-ponta» como adjetivo. Escreva em português corrente:
«orientado por dados», «voltado ao cliente», «de ponta a ponta». *Fraco sozinho.*

### 11. Voz passiva e sujeito escondido
«são preservados automaticamente», «não é necessário configurar», «foi realizada a validação». Diga
quem faz. *Fraco sozinho.*

## C. Inflação e autoridade emprestada

### 12. Palavras de IA
**Olhe para:** além disso, adicionalmente, alinhado com, crucial, aprofundar, mergulhar, robusto
(figurado), destacar (verbo), sublinhar (verbo), intrincado, meticuloso, pivotal, chave (adjetivo),
cenário/paisagem (abstrato), tapeçaria, testemunho, vibrante, valioso, fomentar, potencializar,
impulsionar, elevar, empoderar, jornada (fora de contexto real), solução (quando é produto),
ecossistema (quando é «conjunto»), sinergia, holístico, disruptivo, inovador, exponencial.
**Problema:** modelos usam estas palavras muito mais do que pessoas, e em grupo. Esta é a única lista
de vocabulário do juiz: palavra formal fora dela não é padrão por si só.

### 13. Importância inflada
**Olhe para:** é um testemunho de, marco decisivo, momento crucial, desempenha papel fundamental,
legado duradouro, abrindo caminho para; «Apesar dos desafios… segue prosperando»; «o futuro é
promissor», «um passo na direção certa».
**Problema:** um detalhe comum apresentado como virada, legado ou promessa. Fique com o fato. Termine
no último fato concreto.

### 14. Ligação vaga
**Olhe para:** associado a, ligado a, vinculado a, relacionado com, em conexão com.
**Problema:** diz que duas coisas se ligam sem dizer como. Nomeie a relação que a origem dá.

### 15. Gerúndio de enfeite
**Olhe para:** destacando, sublinhando, enfatizando, garantindo, refletindo, simbolizando, contribuindo
para, promovendo, evidenciando, consolidando.
**Problema:** um fato simples ganha uma oração de gerúndio para parecer mais fundo. Fique com o fato.

### 16. Linguagem de venda
**Olhe para:** conta com, ostenta, vibrante, rico (figurado), profundo, exemplifica, compromisso com,
aninhado, no coração de, revolucionário, renomado, ampla gama, deslumbrante, imperdível, referência no
mercado, excelência.
**Problema:** o texto vira anúncio. Diga o que a coisa é.

### 17. Autoridade emprestada
**Olhe para:** especialistas apontam, observadores citam, relatórios do setor, alguns críticos; «citado
em» seguido de lista de veículos; «mais de N seguidores».
**Problema:** uma autoridade sem nome substitui o que foi dito. Use a fonte real quando a origem a
nomeia. Sem ela, corte. Nunca invente fonte.

### 18. Fugir de «é», «são» e «tem»
**Olhe para:** serve como, funciona como, atua como, configura-se como, representa, dispõe de, conta
com, caracteriza-se por, refere-se a.
**Antes:** «A galeria configura-se como o espaço expositivo e conta com quatro salas.»
**Depois:** «A galeria é o espaço expositivo e tem quatro salas.»

## D. Forma por regra

### 19. Negrito de enfeite
Palavra em negrito sem motivo, e lista vertical em que todo item tem rótulo em negrito e dois-pontos.
Tire o negrito. Vire prosa quando os rótulos não carregam informação própria.

### 20. Título decorado
Título com Todas As Iniciais Maiúsculas, emoji ou seta como enfeite, linha horizontal entre todas as
seções. Em português a norma é a primeira maiúscula e os nomes próprios.

### 21. Aspas curvas e tipográficas
Aspas curvas onde o formato de destino usa retas. Em prosa, prefira as aspas angulares (`«…»`); aspas
retas ficam em código, comando e JSON. *Fraco sozinho.*

## E. Sobras da conversa e do rascunho

### 22. Resíduo de conversa
**Olhe para:** espero ter ajudado, claro!, com certeza!, ótima pergunta!, você está certíssimo, quer que
eu…?, posso seguir?, me avise, segue abaixo, aqui está o seu.
**Problema:** saudação, elogio, oferta ou despedida de chat sobrando em texto que deveria se sustentar
sozinho. Tire o embrulho e fique com o conteúdo.

### 23. Aviso de limite de conhecimento e palpite
**Olhe para:** até a data de, até minha última atualização, com base nas informações disponíveis, não
disponível publicamente, provavelmente [estudou, começou], acredita-se que.
**Problema:** o texto admite que não achou fonte e preenche a lacuna com palpite. Diga o que a origem
não mostra, ou tire a frase. Palpite nunca vira fato.

### 24. Título repetido na primeira frase
Título seguido de um parágrafo de uma linha que o repete. Tire a repetição.

### 25. Escrever sobre a versão anterior
Documentação e comentário descrevendo o que o texto substituiu em vez do comportamento atual. A versão
anterior só aparece em changelog, nota de versão e guia de migração.

## Quando não agir

Cada padrão descreve uma escolha padrão, e uma pessoa pode fazer qualquer uma delas de propósito. Aja num
padrão *fraco sozinho* só quando vários se juntam no mesmo trecho. Deixe em paz a expressão vigiada
dentro de citação, título, nome próprio ou trecho que discute a expressão em vez de usá-la. Nome de
produto e de cliente não entram na caça. Termo que a marca escolheu no seu guia vence as listas 12 e 16.
Travessão dentro de código, comando, caminho, URL, JSON e nome de arquivo não é travessão de prosa.

Fique com o que carrega a voz de quem escreveu: o detalhe específico e incomum, o sentimento misturado
e não resolvido, a referência datada, a escolha em primeira pessoa que o autor sabe explicar, o aparte
genuíno e a autocorreção.

## Origem

Os padrões vêm do `SKILL.md` do blader/humanizer 3.0.0 (MIT, commit `9862685f`), que por sua vez os
tira de [«Signs of AI writing»](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) do
WikiProject AI Cleanup. Esta adaptação acrescenta a regra do travessão, as aspas angulares e a
proibição de inventar fato.
