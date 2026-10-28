# Como contribuir

Abra uma [issue](https://github.com/playertwo1/sprite-identity-lock/issues) para
descrever um problema ou envie um pull request com uma mudança focada.

Para um bug, inclua versão do Python e Pillow, comando usado, resultado esperado
e resultado observado. Um manifesto mínimo e sprites que você pode compartilhar
ajudam a reproduzir. Remova caminhos pessoais, credenciais e material privado.

## Verificação local

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/sprite_audit.py --manifest examples/minimal/character-lock.json --frames-dir examples/minimal/frames --out-dir out/contribution-audit --fps 6
```

Use uma saída nova em cada auditoria. Mudanças nos scripts devem incluir um teste
que reproduza o comportamento relevante. Mantenha instruções, exemplo e README
compatíveis. A CI executa a suíte e o exemplo em Windows e Linux.

Não substitua mestres aprovados nem relaxe verificações para esconder um FAIL.
Descreva limitações e mudanças de comportamento no pull request. Confira os termos
de uso no README antes de enviar código ou imagens de terceiros.
