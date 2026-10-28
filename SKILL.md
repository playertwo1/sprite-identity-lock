---
name: sprite-identity-lock
description: Preserva a identidade visual de personagens e animais em pixel art ao criar ou corrigir frames, spritesheets e animações com ferramentas de edição e geração disponíveis. Use quando rostos, roupas, paletas, acessórios, proporções ou contornos mudam entre quadros; também ao revisar sprites existentes. Não use para gerar ilustrações isoladas sem continuidade, voxel/3D ou animações sem sprites.
---

# Sprite Identity Lock

## Objetivo

Preservar **o mesmo personagem** entre quadros, evitando redesenho involuntário. Preferir preservar pixels aprovados em vez de regenerar imagens completas. A skill não torna o ImageGen determinístico nem garante identidade anatômica só com métricas; exigir revisão visual.

## Princípios inegociáveis

1. **Fonte de verdade:** partir de um `master_sprite` já aprovado, sem alterar o original silenciosamente. Se não existir, gerar um conceito e obter aprovação antes da animação.
2. **Character DNA:** definir traços imutáveis (rosto, cabelo, roupas, acessórios, silhueta, paleta) e elementos autorizados a mudar (pose, partes móveis, expressões). Registrar no manifesto; consultar `references/character-dna.md`.
3. **Mudança mínima:** para respirar, piscar, mexer a cauda, acenar levemente ou efeitos semelhantes, duplicar o sprite base e editar **somente** os pixels/camadas da parte móvel. Preferir animação por camadas no motor quando possível.
4. **Geração por referência:** para movimentos grandes, enviar o sprite mestre como imagem de referência a uma edição ImageGen e solicitar uma faixa completa com o número de poses definido pelo projeto em um único pedido. Evitar gerar quadros independentes apenas a partir de texto.
5. **Geometria e transparência:** quadros PNG, grade e tamanho explícitos; nunca redimensionar cada personagem individualmente para forçar consistência. Se a imagem gerar em escala maior, normalizar com uma **escala global** e `nearest neighbor`; alinhar por âncora compartilhada.
6. **Nunca mascarar drift com pós-processamento:** quantizar cores ou alinhar caixas não corrige cabeça, figurino ou rosto redesenhado. Rejeitar e reparar esses frames pela referência aprovada.
7. **Aprovação:** exportar para o jogo **apenas** após auditoria técnica e inspeção da sequência animada. Não sobrescrever assets existentes sem pedido explícito.
8. **Ferramentas opcionais:** funcionar com Codex, editor de imagem e Python/Pillow. Se alguma ferramenta de geração/edição não estiver disponível, orientar o operador; não inventar APIs, plugins, contas, licenças ou capacidades.

## Fluxo operacional

### 1. Descobrir contrato visual

- Inspecionar motor do jogo, sprites existentes, resolução real, paleta, organização dos arquivos e direções exigidas.
- Reutilizar a configuração do projeto; **não** impor 64×64, estilo ou número de frames se já existir padrão.
- Identificar `master_sprite`, sua âncora (normalmente centro inferior), regiões rigidamente estáticas e partes móveis.
- Salvar um manifesto JSON baseado em `assets/character-lock.example.json` (substituir caminhos e dimensões reais). Manter o manifesto junto ao personagem, separado dos assets desta skill.
- Para um personagem sem imagem-base aprovada, fazer uma etapa de criação e aprovação separada.

### 2. Escolher um dos três modos

- **PIXEL_LOCK (preferido para idle, blink, breathing, tail, pequenos gestos):** duplicar sprite/camadas e modificar só os pixels aprovados; manter as regiões não móveis pixel a pixel (ignorando RGB em pixels totalmente transparentes). Usar edição determinística somente quando permitida pelo ambiente; se a ferramenta exigir ImageGen para edições, seguir essa regra e verificar os pixels depois.
- **REFERENCE_STRIP (andar, correr, pular, dançar):** gerar uma faixa de poses numa única edição com o master visível, quadro 1 igual ao master quando fizer sentido e restrições explícitas de figurino, paleta e proporções. Ver `references/prompts.md`.
- **REPAIR (quadros existentes inconsistentes):** comparar com o mestre, identificar mudanças não autorizadas e reparar somente quadros/regiões afetados. Evitar refazer a animação inteira.

### 3. Extrair e validar

Se o gerador devolveu uma grade retangular sem espaçamentos, recortar sem interpolação para uma pasta nova ou vazia:

```bash
python scripts/split_sheet.py --input saida/faixa.png --columns 4 --rows 1 --out-dir saida/frames
```

Se houver bordas, gutters, texto ou células irregulares, **não recortar cegamente**; corrigir/remover antes e validar visualmente.

Auditar os quadros conforme manifesto:

```bash
python scripts/sprite_audit.py --manifest caminho/character-lock.json --frames-dir saida/frames --out-dir saida/audit
```

Executar os comandos com caminhos absolutos para os scripts desta skill quando o diretório atual for o projeto. Requer `Pillow`; reutilizar um ambiente compatível ou instalar `requirements.txt` em um ambiente virtual dedicado. Usar uma pasta de auditoria nova a cada execução. O script escreve `report.json`, `contact_sheet.png` e `preview.gif` fora dos arquivos originais.

### 4. Interpretar auditoria corretamente

- **FAIL:** PNG corrompido, formato diferente de PNG estático, dimensão inválida, região rigidamente bloqueada alterada, primeiro quadro obrigatório diferente, mestre adulterado ou cores extras sob política rígida. Não publicar.
- **REVIEW:** alinhamento, mudança de área ocupada, pixels semitransparentes, cores extras sob política flexível, quadros idênticos, mudança excessiva. Exige inspeção humana.
- **PASS:** todas as verificações de pixels passaram. **Não** equivale a garantia de identidade; ainda inspecionar rosto, roupa, acessórios, silhueta e fluidez no preview e na engine.
- Não usar um `fixed_region` retangular em uma parte que **se desloca no canvas**, como a cabeça durante um salto: a comparação é coordenada a coordenada, não acompanha deformações. Para essas poses, confiar em referências visuais e revisão.
- Configurar exceções por frame apenas quando a mudança tiver justificativa documentada (piscar, direção, expressão).

O bloqueio automático cobre somente `fixed_regions`; `allowed_changes` e `identity_notes` são instruções para revisão, não máscaras executáveis. Em PIXEL_LOCK, declarar regiões que cubram as partes imóveis e revisar também as áreas não cobertas.

O relatório lista `preview_frames`: quadros inválidos podem ficar fora do GIF e da sheet. Nesse caso o preview é parcial e não comprova a sequência completa. GIF quantiza cores e tempo; conferir paleta nos PNGs e ritmo na engine. O código de saída 0 inclui REVIEW, e nunca significa aprovação visual automática.

### 5. Encerrar com evidência

Entregar: manifesto, quadros novos em pasta de trabalho, relatório e preview. Mostrar o que mudou, quais gates passaram/falharam e o que depende de revisão. Integrar no motor quando o escopo e a aprovação vigente do usuário cobrirem esses assets; não pedir novamente uma autorização já concedida.

## Limites de segurança e escopo

- Não instalar serviços pagos ou MCPs sem consentimento.
- Preservar originais e histórico; substituir assets apenas dentro do escopo já autorizado pelo usuário.
- Não baixar nem executar scripts de terceiros automaticamente. Para usar ferramenta externa, primeiro inspecionar licença, código e compatibilidade.
- Evitar overengineering: na ausência de escopo definido, começar com um personagem e uma animação curta. Não construir editor, dashboard ou servidor sem demanda.

## Material de apoio

- `references/character-dna.md` — contrato, campos e decisão entre bloqueios rígidos e revisão semântica.
- `references/prompts.md` — modelos de prompts para geração e reparo.
- `scripts/sprite_audit.py` — auditoria e previews com Pillow.
- `scripts/split_sheet.py` — recorte da grade regular.
- `assets/character-lock.example.json` — exemplo editável.
