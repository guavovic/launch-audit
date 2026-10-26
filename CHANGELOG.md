# Mudanças

## Próxima versão (v0.2)

- Nome novo: o repositório passou de `claude-security-audit` para `launch-audit`, porque audita site, API e aplicativo antes de ir ao ar, nas três frentes, e não depende de uma ferramenta só. O endereço antigo redireciona.
- Instalação como plugin do Claude Code: `/plugin marketplace add guavovic/launch-audit` e `/plugin install launch-audit@launch-audit` trazem as três skills e o subagente, sem copiar pasta.
- As skills acham o script de checagem passiva pela própria pasta (`${CLAUDE_SKILL_DIR}`), em vez do caminho fixo em `~/.claude/skills/`, e passam o caminho pro subagente no pedido. Assim funciona tanto no plugin quanto na cópia manual.
- Embalagens pro OpenAI Codex, Gemini CLI, Cursor e GitHub Copilot em `embalagens/`, geradas de `skills/` e `agents/` por `ferramentas/gerar_embalagens.py` (Python sem dependência, com `--conferir`). Nas cópias, o caminho do script vira relativo à pasta da skill, a descrição vai entre aspas no frontmatter e o texto diz o que fazer quando não há subagente. Ainda sem teste em cada ferramenta (#14).
- `AGENTS.md` na raiz, dizendo por onde começar e quais são as regras do repositório.
- Checklists por stack, lidos só quando o projeto usa aquela tecnologia: Vercel, Astro, PWA/service worker, Supabase, Firebase e ASP.NET na auditoria de segurança, e Vercel, Astro e PWA na de site (#6).
- Auditoria legal cobre e-mail marketing (opt-in e descadastro), cobrança por Pix e gateway, GDPR pra público europeu e jogo com ranking online (#7).
- Primeiro estudo de caso publicado: a rodada de 21/10/2026 no guavovic-website, com o que as skills acharam, o que não se aplicava e o que mudou nelas por causa disso, em `docs/casos/guavovic-website.md` (#5).
- Primeira rodada de placar: `auditoria-seguranca` contra o OWASP Juice Shop 20.3.0 local, com os 116 desafios oficiais como gabarito. 57 acertos, 58 fora do alcance (só aparecem explorando), 1 não achado e 2 falsos positivos, em `docs/placar/juice-shop-2026-10-26.md`. A rodada abriu dois buracos na skill: checagem passiva que não aceita alvo local em HTTP (#25) e falta de item de XXE no checklist (#26) (#2).
- Checagem passiva reconhece o fallback de SPA (sitemap, 404, sourcemap e arquivos sensíveis que na verdade são a home) e API sem página na raiz (`--rota`, headers de página rebaixados pra `info` em resposta JSON, checagens de SEO puladas). Mais plataformas na lista de subdomínios sem DNS próprio (Render, Fly, Railway, Heroku, Azure, Firebase). Veio da rodada na achai-api.

## v0.1.0 (21/10/2026)

Primeira versão pública.

- Skills `auditoria-seguranca`, `auditoria-legal` e `auditoria-site`, com checklists de referência.
- Script `checagem_passiva.py`: HTTPS e HSTS, TLS, headers, CSP, cookies, `<head>`, scripts de terceiros, robots, sitemap, 404, sourcemap, arquivos sensíveis expostos e DNS, em JSON, com `--comparar`.
- Subagente `auditoria-executor` pra parte braçal.
- Regras locais por skill (`regras-locais.md`, fora do git).

Ajustes que vieram da primeira rodada real, num site em produção:

- Caminhos sensíveis consultados por último e resposta de anti-bot marcada como `bloqueado`, não como falha (a hospedagem bloqueia o IP por alguns minutos depois deles).
- Lighthouse antes do script na auditoria completa.
- Aviso pra não aplicar `npm audit fix --force` sem conferir, porque ele pode sugerir downgrade de versão major.
- Escape feito à mão é testado, não só lido.
