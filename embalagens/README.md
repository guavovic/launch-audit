<!-- Arquivo gerado por ferramentas/gerar_embalagens.py a partir de skills/ e agents/. Não edite à mão: mude a fonte e rode o script de novo. -->

# Embalagens

Cópias das skills de `skills/` e do subagente de `agents/` no formato de cada ferramenta. Tudo aqui é gerado por `python ferramentas/gerar_embalagens.py`: pra mudar, edite a fonte e rode o script.

O Claude Code não tem pasta aqui: ele usa a fonte direto, como plugin (ver o README da raiz).

Nas cópias, `${CLAUDE_SKILL_DIR}` vira `<pasta-desta-skill>`, a parte braçal diz o que fazer quando não há subagente e a descrição do frontmatter vai entre aspas. O `regras-locais.md` de cada skill nunca entra.

| Pasta | Ferramenta | O que tem | Onde colocar |
|---|---|---|---|
| `codex/` | OpenAI Codex | `.agents/skills/<skill>/` e `.codex/agents/<agente>.toml` | No projeto, as duas pastas na raiz. Pra todos os projetos, as skills em `~/.agents/skills/` e o agente em `~/.codex/agents/` |
| `gemini/` | Gemini CLI | Extensão: `gemini-extension.json`, `GEMINI.md`, `skills/`, `agents/` | `gemini extensions install <clone>/embalagens/gemini` (ou `gemini extensions link` pra acompanhar o clone). Subagente de extensão ainda é prévia no Gemini CLI |
| `cursor/` | Cursor | `.cursor/skills/`, `.cursor/agents/` e uma regra `.cursor/rules/launch-audit-skills.mdc` pedida pelo agente | A pasta `.cursor/` na raiz do projeto, ou skills e agente em `~/.cursor/skills/` e `~/.cursor/agents/` |
| `copilot/` | GitHub Copilot | `.github/skills/`, `.github/agents/<agente>.agent.md` e `.github/instructions/launch-audit-skills.instructions.md` | A pasta `.github/` na raiz do repositório. No Copilot CLI, skills e agente também valem em `~/.copilot/skills/` e `~/.copilot/agents/` |

Copie as três skills juntas, lado a lado: as skills legal e site usam o script da skill de segurança pela pasta vizinha.

Cursor sem MCP: as skills não têm servidor, o script roda pelo terminal do agente.

Nenhuma dessas embalagens foi testada na ferramenta ainda. O teste de cada uma é a issue #14.
