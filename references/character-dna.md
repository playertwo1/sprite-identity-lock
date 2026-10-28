# Character DNA — contrato visual

O `master_sprite` é a referência aprovada; não substituí-lo por variantes geradas. Definir primeiro identidade visual sem termos ambíguos, por exemplo:

- **Forma:** cabeça redonda 12 pixels de largura, corpo curto, duas orelhas pontudas.
- **Paleta:** conjunto exato de cores do mestre; novas cores precisam de aprovação.
- **Rosto:** olhos na mesma posição relativa ao rosto; cor e estilo constantes. Piscar é exceção intencional.
- **Figurino:** desenho, cinto, bolso, costura, acessórios; indicar o que nunca deve desaparecer.
- **Sombras:** luz do mesmo lado; sem mudanças aleatórias de materiais.
- **Animação:** definir direção, número de quadros, poses e partes móveis.

## Manifesto JSON

Usar `assets/character-lock.example.json` como ponto de partida. Os caminhos de `master_sprite` são resolvidos **relativamente ao próprio manifesto**. `canvas` define as dimensões reais de cada frame. `palette_policy`:

- `strict`: cores visíveis fora de `palette` (ou da paleta do mestre, se não for especificada) causam FAIL.
- `review`: novas cores causam REVIEW.

`fixed_regions`: lista de regiões retangulares em coordenadas **absolutas do quadro** `[x,y,w,h]`. `max_changed_pixels` permite mudanças limitadas. Usar somente em região verdadeiramente estática, inclusive na sua posição. `region_exceptions` mapeia nome de arquivo para nomes de regiões liberadas em uma pose específica.

`tolerances` limita deslocamento da âncora (centro inferior da área não transparente), variação percentual das dimensões do bounding box e fração de pixels alterados na união das áreas visíveis do quadro e do mestre. Esses são **avisos**, porque poses podem legitimamente esticar braços, agachar ou saltar.

`lock_first_frame`: se `true`, o primeiro arquivo em ordem alfabética deve ser pixel a pixel idêntico (RGB oculto por alpha zero é ignorado) ao mestre. Ativar somente quando a animação começa exatamente no mesmo idle.

`master_sha256`: opcional; se preenchido, detecta troca do arquivo mestre. Gerar com SHA256 do arquivo aprovado; pode deixar vazio durante protótipo e preencher após aprovação.

Campos desconhecidos e tipos inválidos são rejeitados. Dimensões e retângulos usam inteiros; `lock_first_frame` usa booleano JSON, nunca texto. As tolerâncias de razão ficam entre 0 e 1; `0.30` significa 30%. Deslocamentos e variações de bbox aceitam números não negativos. Não desativar uma verificação para conseguir PASS sem justificar a mudança no contrato.

`identity_notes` e `allowed_changes` não executam verificações semânticas. `fixed_regions` é o único bloqueio espacial automático. A âncora calculada é o centro inferior da área visível, uma heurística que pode mudar ao estender braços ou cauda; ela não mede o pivô cadastrado no motor.

## Checkpoint de revisão humana

Ver a sheet e o GIF em escala nativa e ampliada nearest-neighbor:

1. O mesmo personagem é reconhecível frame a frame?
2. Olhos, orelhas, detalhes de roupa, acessórios e contornos mantêm suas características?
3. Mudanças são apenas de pose/expressão autorizada?
4. Existe flicker de brilho, sombra, número de dedos ou espessura de traço?
5. A animação fica fluida no FPS pretendido na engine?

Se qualquer resposta indicar perda de identidade: **REJECT** e refazer o quadro/região a partir de referência visual, não corrigir apenas bbox.
