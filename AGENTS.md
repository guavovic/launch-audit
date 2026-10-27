# AGENTS.md

Guia pra agente de código (Codex, Cursor, Copilot, Gemini, Claude Code) que vai usar ou mexer neste repositório.

## O que é

Três skills que auditam site, API ou aplicativo antes de ir ao ar, mais um subagente pra parte braçal:

- `skills/auditoria-seguranca/`: segurança (segredo exposto, controle de acesso, injeção, headers, dependências, operação). Tem o script `scripts/checagem_passiva.py`, usado pelas três.
- `skills/auditoria-legal/`: risco jurídico no Brasil (LGPD, cookies, CDC, acessibilidade, direito autoral).
- `skills/auditoria-site/`: prontidão de lançamento (formulários, velocidade, SEO, prévia social, monitoramento).
- `agents/auditoria-executor.md`: subagente que roda Lighthouse, o script e as buscas e devolve a evidência.

## Por onde começar

- **Pra auditar um projeto:** abra o `SKILL.md` da skill que responde ao pedido e siga as etapas dele. "Auditoria completa" é as três, na ordem segurança, legal, site.
- **Sem subagente:** se a ferramenta não tiver subagente, ou ele estiver desligado, o agente principal faz a parte braçal com as regras de `agents/auditoria-executor.md` (só o alvo pedido, teste ativo só em localhost, nada que grave em produção, segredo com só 4 caracteres à mostra).
- **Pra instalar em outra ferramenta:** as cópias prontas estão em `embalagens/`, uma pasta por ferramenta. O `embalagens/README.md` diz onde colocar cada uma.

## Regras pra quem mexe no repositório

- **Fonte única:** `skills/` e `agents/`. A pasta `embalagens/` é gerada por `python ferramentas/gerar_embalagens.py` e nunca é editada à mão. Depois de mudar a fonte, rode o script e confira com `python ferramentas/gerar_embalagens.py --conferir`.
- Não mova nem renomeie `skills/<nome>/SKILL.md`: o plugin do Claude Code (`.claude-plugin/`) e instalações locais apontam pra essas pastas.
- `regras-locais.md` dentro das skills é de quem usa, fica fora do git e nunca entra nas embalagens.
- Texto em pt-BR, com acento e sem travessão. Arquivos em UTF-8 com fim de linha LF (ao gravar com Python, `newline="\n"`).
- Nada de exemplo de payload de ataque no conteúdo.
- Mudança que o usuário percebe entra no `CHANGELOG.md`, na seção da data, a mais nova no topo. O repositório não tem versões nem releases.
