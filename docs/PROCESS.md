# Processo completo / Complete process

[← README](../README.md#processo-pt) · [Guia de uso / Usage](USAGE.md) · [English](#english)

<a id="portugues"></a>

Os diagramas visíveis no README mostram as três entradas práticas: projeto novo, adoção e operação.
Este fluxo detalha as decisões de descoberta, revisão e publicação, incluindo pausas e recuperação.
Os círculos representam eventos; as caixas, tarefas; os losangos, decisões. É uma documentação
inspirada em BPMN. Pessoas e agentes executam o rito; PM e Tech Lead são responsabilidades.

```mermaid
flowchart TB
  subgraph descoberta["Personalizer e operador"]
    A((Ideia)) --> B{Projeto existente?}
    B -->|Sim| C[Auditar código e convenções]
    B -->|Não| D[Entrevistar e salvar respostas]
    C --> D
    D --> E{Contexto suficiente?}
    E -->|Não| P[Salvar pendências e próxima pergunta]
    P --> Z((Retomar depois))
  end
  subgraph planejamento["PM e Tech Lead"]
    E -->|Sim| F[Adaptar perfil e guias]
    F --> G[Definir feature, entregas e aceite]
  end
  subgraph execucao["Executor e especialista em integrações"]
    G --> H[Implementar entrega e testar]
    H --> J[Atualizar README e vault]
  end
  subgraph verificacao["Revisor e responsável pela publicação"]
    J --> K{Revisão aprovada?}
    K -->|Não| H
    K -->|Sim| L{Publicar no escopo autorizado?}
    L -->|Sim| M[Publicar e observar]
    M --> N{Ambiente verificado?}
    N -->|Não| R[Recuperar ou reverter e registrar]
    R --> H
    N -->|Sim| V[Registrar versão e evidência de produção]
    L -->|Não| W[Registrar entrega e publicação pendente ou não aplicável]
  end
  V --> X[Salvar resultado e próximo passo no vault]
  W --> X
  X --> Y((Entrega registrada))
  classDef event fill:#1F7A4D,color:#fff,stroke:#17130f,stroke-width:3px;
  classDef task fill:#1F4FA3,color:#fff,stroke:#17130f,stroke-width:2px;
  classDef gate fill:#f6d77a,color:#17130f,stroke:#17130f,stroke-width:2px;
  classDef memory fill:#5B2E8A,color:#fff,stroke:#17130f,stroke-width:2px;
  class A,Z,Y event;
  class C,D,F,G,H,J,M,R,V,W task;
  class B,E,K,L,N gate;
  class P,X memory;
  style descoberta fill:#f8f4eb,stroke:#17130f,color:#17130f
  style planejamento fill:#f8f4eb,stroke:#17130f,color:#17130f
  style execucao fill:#f8f4eb,stroke:#17130f,color:#17130f
  style verificacao fill:#f8f4eb,stroke:#17130f,color:#17130f
```

Uma entrevista pausada retoma pelo índice de produto. Cada entrega registra capacidades usadas,
testes, revisão e próximo passo; produção exige evidência do ambiente. Quando a publicação não faz
parte do escopo, registre “não aplicável”; quando falta autorização, registre a pendência.

<a id="english"></a>

The README diagrams cover three practical paths: a new project, adoption and daily work.
This detailed flow includes discovery, review and release decisions, pauses and recovery.
Circles are events, boxes are tasks and diamonds are decisions. This is BPMN-inspired documentation.
People and agents carry out the process; PM and Tech Lead are responsibilities.

```mermaid
flowchart TB
  subgraph discovery["Personalizer and owner"]
    A((Idea)) --> B{Existing project?}
    B -->|Yes| C[Audit code and conventions]
    B -->|No| D[Interview and save answers]
    C --> D
    D --> E{Enough context?}
    E -->|No| P[Save gaps and next question]
    P --> Z((Resume later))
  end
  subgraph planning["PM and Tech Lead"]
    E -->|Yes| F[Adapt profile and guides]
    F --> G[Define feature, slices and acceptance]
  end
  subgraph execution["Executor and integration specialist"]
    G --> H[Implement a slice and test]
    H --> J[Update README and vault]
  end
  subgraph verification["Reviewer and release owner"]
    J --> K{Review approved?}
    K -->|No| H
    K -->|Yes| L{Release in authorized scope?}
    L -->|Yes| M[Deploy and observe]
    M --> N{Environment verified?}
    N -->|No| R[Recover or roll back and record]
    R --> H
    N -->|Yes| V[Record version and production evidence]
    L -->|No| W[Record delivery and release pending or not applicable]
  end
  V --> X[Save outcome and next action in the vault]
  W --> X
  X --> Y((Delivery recorded))
  classDef event fill:#1F7A4D,color:#fff,stroke:#17130f,stroke-width:3px;
  classDef task fill:#1F4FA3,color:#fff,stroke:#17130f,stroke-width:2px;
  classDef gate fill:#f6d77a,color:#17130f,stroke:#17130f,stroke-width:2px;
  classDef memory fill:#5B2E8A,color:#fff,stroke:#17130f,stroke-width:2px;
  class A,Z,Y event;
  class C,D,F,G,H,J,M,R,V,W task;
  class B,E,K,L,N gate;
  class P,X memory;
  style discovery fill:#f8f4eb,stroke:#17130f,color:#17130f
  style planning fill:#f8f4eb,stroke:#17130f,color:#17130f
  style execution fill:#f8f4eb,stroke:#17130f,color:#17130f
  style verification fill:#f8f4eb,stroke:#17130f,color:#17130f
```

Resume a paused interview through the product index. Each delivery records capabilities used,
tests, review and the next action; production requires environment evidence. Record release as
“not applicable” when outside scope, or pending when authorization is missing.

Os SVGs editáveis em `assets/process-*.svg` são as versões visuais do README. Ao mudar o rito,
atualize os diagramas PT/EN, este fluxo e o guia de uso. Preserve a paleta e confira a legibilidade.
The editable SVGs in `assets/process-*.svg` supply the README visuals. Process changes must update
both languages, this flow and the usage guide. Preserve the palette and check readability.
