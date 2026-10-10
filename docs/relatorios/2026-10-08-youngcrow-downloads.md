# Downloads dos vídeos do YoungCrow

Frente: entrega do tutorial audiovisual em 16:9 e 9:16.

O operador não conseguiu baixar os dois vídeos pelos caminhos internos da sessão
cloud. A entrega passa a incluir cópias MP4 comprimidas no repositório, com links
diretos no README, no guia de uso e na documentação do filme.

| Arquivo | Resolução | Tamanho | Duração |
| --- | --- | --- | --- |
| `YoungCrow-16x9.mp4` | 1920 × 1080 | 40.144.704 bytes | 4min58s |
| `YoungCrow-9x16.mp4` | 1080 × 1920 | 51.998.318 bytes | 4min58s |

Ambos ficam em `docs/media/youngcrow-guide/downloads/`, com H.264, AAC, 24 fps
e 7.152 quadros. Incluem a introdução e o caso encenado do atendente da clínica,
que começa em 01:58. O vídeo foi recodificado para reduzir o tamanho; os pacotes
de áudio foram copiados. Os originais de maior qualidade continuam preservados
fora do Git.

## Verificação local

- Decodificação integral dos dois arquivos pelo FFmpeg: código 0.
- Comparação do payload de áudio por SHA-256: idêntico ao respectivo original.
- SHA-256 dos dois originais: preservado.
- Inspeção visual de um quadro de cada cópia no segundo 256: texto legível,
  composição horizontal e vertical preservadas.
- Cada arquivo abaixo do limite de 100 MiB por arquivo do GitHub.

Medição: [`2026-10-08-youngcrow-downloads.json`](../medicoes/2026-10-08-youngcrow-downloads.json).
Após a publicação no commit `f064df3e2ed33f77e383ce929bfc007d87fa9ea3`, os dois
links públicos foram baixados integralmente por HTTPS, sem autenticação. Ambos
retornaram HTTP 200, com os mesmos bytes e SHA-256 dos arquivos locais. Os links
da documentação também retornaram HTTP 200. O recibo está na mesma medição.

O conteúdo continua identificado como encenação. Esta entrega não altera o
executor nem representa aceitação nativa do harness.

ATRASO: arquivos de download 0 | links públicos 0 | executor: validação pendente.
