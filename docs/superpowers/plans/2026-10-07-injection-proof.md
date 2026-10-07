# Prova interna de substituição da credencial fictícia

Frente: YC-203.6. Continuação autorizada pelo mantenedor; execução inline, root escreve,
revisores somente leitura. Deriva da decisão de egress exclusiva e do handoff de rede.

## Contrato

O relay envia o placeholder. A fixture exige SHA-256 de um valor diferente, recebe
somente esse hash no manifesto/argv e retorna metadados limitados. O valor fictício
continua no host/proxy de teste; nunca entra em manifesto, argv ou recibo. A/B/A2
compartilham placeholder, hash esperado, proxy e CA, com identidades próprias.

Manifesto de fase, plano e registro usam v4. V2/v3 permanecem legíveis para recuperação;
seus resultados de eco não se tornam prova de injeção. A fixture v4 retorna resultado
schema 2. Guardian confere os comandos completos e o controlador confere hash e resultado.
O relay, guard e mutadores nativos conservam o escopo; `proof_accepted` permanece falso.

A API Cloud documenta identidade/versão e remoção condicionada. Sua compatibilidade
com endpoint/store do sbx local 0.46.0 permanece sem prova e bloqueia o adaptador
nativo. A correção independente da fixture não altera esse limite.
Não executar Docker, modelo, login, reconstrução ou novo ciclo nativo (2/3 preservados).

## Execução e provas

- [x] Conferir novas fontes oficiais de secrets locais, separando API cloud e versões.
- [x] RED/GREEN: eco literal, valor errado, duplicado e hash do placeholder recusados;
  valor fictício distinto aceito pelo percurso fixture/relay com sockets locais.
- [x] Integrar manifesto/resultado v4 no controlador, guardian e launcher, mantendo
  leitura/recovery dos contratos antigos e comandos fixos.
- [x] Plano/registro v4 vincula a mesma configuração A/B/A2; rejeitar deriva de fase.
- [x] Exercitar o controlador e diário reais sob contenção; negativo sem injeção.
- [x] Revisão independente e testes apropriados; atualizar hashes de catálogo.
- [ ] Atualizar README PT/EN, USAGE, backlog, handoff, relatório/medição e memória;
  publicar no PR #24 e conferir refs sem alterar main.

## Review Focus

Aceitar um hash fornecido pela própria resposta, promover eco legado ou misturar
placeholders/CA/proxy entre fases invalidaria a prova. O hash esperado deve vir do
plano imutável. Recibos não guardam o valor observado nem o corpo. Testes locais
simulam somente fronteiras externas; não certificam injeção Docker ou limpeza nativa.
