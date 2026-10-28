# Prompts operacionais

## PIXEL_LOCK — animação simples

> Use o arquivo mestre aprovado como única origem do personagem. Copie exatamente os pixels/camadas de todas as partes não móveis. Anime somente [PARTES] para produzir [N] quadros em [W]×[H] pixels, com âncora [ÂNCORA]. Para piscar, modifique somente os olhos; para rabo, preserve corpo, rosto e patas. Não redesenhe o personagem inteiro. Guarde originais e exporte cópias em pasta de trabalho.

## REFERENCE_STRIP — geração por edição de imagem

> Edite a IMAGEM DE REFERÊNCIA ANEXADA para criar uma ÚNICA faixa com [N] quadros de [W]×[H] pixels, ação [AÇÃO], direção [DIREÇÃO]. Este é EXATAMENTE O MESMO personagem em todos os quadros, não versões similares. Preserve sem alteração: [IDENTIDADE/ROSTOS/CABELO/ROUPA/ACESSÓRIOS/CORES]. Modifique somente [MEMBROS/POSES]. Pose por quadro: [DESCREVER CADA POSE]. Quadro inicial idêntico ao master [SE APLICÁVEL]. Mantenha centro inferior fixo [SE A AÇÃO PERMITIR], transparência real, bordas pixel-art limpas, sem cenário, letras, sombras externas, padding diferente ou mudança de iluminação. Grade regular [COLUNAS]×[LINHAS]; sem separadores, bordas ou margens.

Não presumir que o modelo siga dimensões exatas ou transparência: verificar saída antes de separar. Se gerar PNG grande, fazer redução global coerente e nearest-neighbor somente depois de revisar o estilo pixel-art.

## REPAIR — reparar identidade

> Compare estes quadros com a imagem mestre aprovada. O frame [NUMERO] tem alterações não autorizadas: [DESCREVER TRAÇOS]. Preserve TODAS as partes aprovadas e corrija exclusivamente [ÁREA/TRAÇO], mantendo posição, escala, paleta, contorno, transparência e a pose atual. Não proponha novo figurino, cabelo, rosto, perspectiva ou iluminação. Exporte para arquivo novo e gere GIF comparativo. Se não conseguir preservar a identidade com edição localizada, sinalize REJECT em vez de inventar correção.

## Dicas operacionais

- Referência textual é insuficiente para identidade exata; **fornecer o PNG** ao modelo de imagem sempre que a ferramenta permitir.
- A geração de uma única faixa reduz a variância entre solicitações, mas **não elimina drift dentro da própria faixa**.
- Para andar, a geometria completa muda; não bloquear um rosto por coordenadas de canvas se a cabeça se move. Descrever identidade semântica e comparar visualmente.
- Ao aumentar resolução, nunca chamar isso de restauração de detalhe. Usar nearest neighbor para pixels já aprovados.
