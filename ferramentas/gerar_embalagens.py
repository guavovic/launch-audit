"""Gera as embalagens do launch-audit-skills pra cada ferramenta a partir de uma fonte só.

Fonte (editada à mão):
    skills/<nome>/          as três skills, no formato do Claude Code (que já é o plugin)
    agents/*.md             o subagente executor

Saída (nunca editada à mão, sempre regenerada por este script):
    embalagens/codex/       skills em .agents/skills e subagente em .codex/agents (TOML)
    embalagens/gemini/      extensão do Gemini CLI (gemini-extension.json, GEMINI.md, skills, agents)
    embalagens/cursor/      skills, subagente e regra em .cursor/
    embalagens/copilot/     skills, agente e instruções em .github/

Uso (Python 3.9+, sem dependência):
    python ferramentas/gerar_embalagens.py             regenera embalagens/
    python ferramentas/gerar_embalagens.py --conferir  só confere; sai com 1 se embalagens/ estiver desatualizada
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "embalagens"

NOME = "launch-audit-skills"
VERSAO = "0.2.0"  # o manifesto do Gemini exige o campo; o repositório não tem releases
DESCRICAO = (
    "Auditoria de site, API ou aplicativo antes de ir ao ar: segurança, risco jurídico no Brasil "
    "e qualidade de lançamento, com evidência e com o que o projeto não precisa."
)
REPO = "https://github.com/guavovic/launch-audit-skills"

# Arquivos da pasta de cada skill que nunca saem do disco de quem usa.
IGNORAR_NOMES = {"regras-locais.md", "__pycache__"}
IGNORAR_SUFIXOS = {".pyc"}

AVISO = (
    "Arquivo gerado por ferramentas/gerar_embalagens.py a partir de skills/ e agents/. "
    "Não edite à mão: mude a fonte e rode o script de novo."
)

# Trocas no texto das skills pras ferramentas que não são o Claude Code.
# Cada trecho precisa existir na fonte: se a fonte mudar, o script para em vez de gerar texto errado.
TROCAS_SKILL = [
    ("${CLAUDE_SKILL_DIR}", "<pasta-desta-skill>", None),
    (
        "delegue ao subagente `auditoria-executor` (Sonnet), passando",
        "delegue ao subagente `auditoria-executor` se a ferramenta tiver subagente; se não tiver, "
        "ou se ele estiver desligado, você mesmo faz a parte braçal com as mesmas regras dele "
        "(só o alvo pedido, nada que grave em produção, segredo com só 4 caracteres à mostra). "
        "Ao delegar, passe",
        1,
    ),
    ("(`/schedule` no Claude Code)", "(se a ferramenta tiver agendamento)", 1),
]
NOTA_PASTA = (
    "`<pasta-desta-skill>` é a pasta onde está este SKILL.md. As três skills ficam lado a lado, "
    "então `<pasta-desta-skill>/../auditoria-seguranca` é a pasta da skill de segurança."
)

TROCAS_AGENTE_DESCRICAO = [(" Roda no Sonnet pra economizar cota.", "")]


# ---------------------------------------------------------------- leitura da fonte

def ler(caminho):
    return caminho.read_text(encoding="utf-8").replace("\r\n", "\n")


def separar_frontmatter(texto, origem):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", texto, re.S)
    if not m:
        sys.exit(f"erro: {origem} não começa com frontmatter")
    campos = {}
    for linha in m.group(1).split("\n"):
        if not linha.strip():
            continue
        chave, _, valor = linha.partition(":")
        campos[chave.strip()] = valor.strip()
    return campos, m.group(2)


def yaml_texto(valor):
    """String YAML entre aspas duplas (a descrição tem dois-pontos, que quebram YAML sem aspas)."""
    return '"' + valor.replace("\\", "\\\\").replace('"', '\\"') + '"'


def frontmatter(campos):
    linhas = []
    for chave, valor in campos.items():
        linhas.append(f"{chave}: {valor if valor in ('true', 'false', 'inherit') else yaml_texto(valor)}")
    return "---\n" + "\n".join(linhas) + "\n---\n"


def trocar(texto, trocas, origem):
    for antes, depois, vezes in trocas:
        achou = texto.count(antes)
        if achou == 0 or (vezes is not None and achou != vezes):
            sys.exit(f"erro: em {origem}, esperava {vezes or 'algum'} trecho '{antes}' e achei {achou}")
        texto = texto.replace(antes, depois)
    return texto


def skills():
    lista = []
    for pasta in sorted((RAIZ / "skills").iterdir()):
        arquivo = pasta / "SKILL.md"
        if not arquivo.is_file():
            continue
        campos, corpo = separar_frontmatter(ler(arquivo), arquivo)
        if campos.get("name") != pasta.name:
            sys.exit(f"erro: {arquivo} tem name '{campos.get('name')}', diferente da pasta")
        if len(campos.get("description", "")) > 1024:
            sys.exit(f"erro: descrição de {arquivo} passa de 1024 caracteres (limite do padrão Agent Skills)")
        extras = {}
        for caminho in sorted(pasta.rglob("*")):
            relativo = caminho.relative_to(pasta)
            if caminho.is_dir() or relativo == Path("SKILL.md"):
                continue
            if any(p in IGNORAR_NOMES for p in relativo.parts) or caminho.suffix in IGNORAR_SUFIXOS:
                continue
            extras[relativo.as_posix()] = ler(caminho)
        lista.append({"nome": pasta.name, "campos": campos, "corpo": corpo, "extras": extras})
    if not lista:
        sys.exit("erro: nenhuma skill em skills/")
    return lista


def agentes():
    lista = []
    for arquivo in sorted((RAIZ / "agents").glob("*.md")):
        campos, corpo = separar_frontmatter(ler(arquivo), arquivo)
        descricao = campos["description"]
        for antes, depois in TROCAS_AGENTE_DESCRICAO:
            descricao = descricao.replace(antes, depois)
        lista.append({"nome": campos["name"], "descricao": descricao, "corpo": corpo.strip() + "\n"})
    return lista


# ---------------------------------------------------------------- montagem de cada embalagem

def skill_portavel(skill):
    corpo = trocar(skill["corpo"], TROCAS_SKILL, f"skills/{skill['nome']}/SKILL.md")
    cabecalho = {"name": skill["campos"]["name"], "description": skill["campos"]["description"]}
    texto = frontmatter(cabecalho) + f"\n<!-- {AVISO} -->\n\n> {NOTA_PASTA}\n" + corpo
    return texto


def colocar_skills(arquivos, base, lista):
    for skill in lista:
        arquivos[f"{base}/{skill['nome']}/SKILL.md"] = skill_portavel(skill)
        for relativo, conteudo in skill["extras"].items():
            arquivos[f"{base}/{skill['nome']}/{relativo}"] = conteudo


def agente_md(agente, extra=None):
    campos = {"name": agente["nome"], "description": agente["descricao"]}
    campos.update(extra or {})
    return frontmatter(campos) + f"\n<!-- {AVISO} -->\n\n" + agente["corpo"]


def agente_toml(agente):
    if "'''" in agente["corpo"]:
        sys.exit(f"erro: o corpo de {agente['nome']} tem ''' e não cabe numa string literal TOML")
    return (
        f"# {AVISO}\n"
        f"name = {json.dumps(agente['nome'], ensure_ascii=False)}\n"
        f"description = {json.dumps(agente['descricao'], ensure_ascii=False)}\n"
        f"developer_instructions = '''\n{agente['corpo']}'''\n"
    )


def lista_skills_md(lista):
    return "\n".join(f"- `{s['nome']}`: {s['campos']['description'].split(':')[0]}." for s in lista)


def instrucao_resumo(lista):
    return (
        f"# {NOME}\n\n"
        "Auditoria de site, API ou aplicativo antes de ir ao ar, em três skills:\n\n"
        f"{lista_skills_md(lista)}\n\n"
        "Quando o pedido for auditar segurança, risco jurídico no Brasil ou se o site está pronto pra lançar, "
        "carregue a skill certa e siga o SKILL.md dela, incluindo o `regras-locais.md` da pasta se existir. "
        "Pra \"auditoria completa\", rode as três, na ordem segurança, legal, site.\n\n"
        "A parte braçal (Lighthouse, script de checagem passiva, buscas no código, navegador) vai pro subagente "
        "`auditoria-executor` quando a ferramenta tiver subagente. Se não tiver, ou se ele estiver desligado, "
        "o agente principal faz essa parte com as mesmas regras: só o alvo pedido, teste ativo só em localhost, "
        "nada que grave em produção, segredo com só 4 caracteres à mostra.\n"
    )


def embalagem_codex(arquivos, lista_skills, lista_agentes):
    colocar_skills(arquivos, "codex/.agents/skills", lista_skills)
    for agente in lista_agentes:
        arquivos[f"codex/.codex/agents/{agente['nome']}.toml"] = agente_toml(agente)


def embalagem_gemini(arquivos, lista_skills, lista_agentes):
    manifesto = {
        "name": NOME,
        "version": VERSAO,
        "description": DESCRICAO,
        "contextFileName": "GEMINI.md",
    }
    arquivos["gemini/gemini-extension.json"] = json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n"
    arquivos["gemini/GEMINI.md"] = f"<!-- {AVISO} -->\n\n" + instrucao_resumo(lista_skills)
    colocar_skills(arquivos, "gemini/skills", lista_skills)
    for agente in lista_agentes:
        arquivos[f"gemini/agents/{agente['nome']}.md"] = agente_md(agente)


def embalagem_cursor(arquivos, lista_skills, lista_agentes):
    colocar_skills(arquivos, "cursor/.cursor/skills", lista_skills)
    for agente in lista_agentes:
        arquivos[f"cursor/.cursor/agents/{agente['nome']}.md"] = agente_md(agente, {"model": "inherit"})
    regra = frontmatter({
        "description": "Auditoria de segurança, risco jurídico no Brasil ou prontidão de lançamento de site, API ou aplicativo",
        "alwaysApply": "false",
    })
    arquivos[f"cursor/.cursor/rules/{NOME}.mdc"] = regra + f"\n<!-- {AVISO} -->\n\n" + instrucao_resumo(lista_skills)


def embalagem_copilot(arquivos, lista_skills, lista_agentes):
    colocar_skills(arquivos, "copilot/.github/skills", lista_skills)
    for agente in lista_agentes:
        arquivos[f"copilot/.github/agents/{agente['nome']}.agent.md"] = agente_md(agente)
    instrucoes = frontmatter({"applyTo": "**", "excludeAgent": "code-review"})
    arquivos[f"copilot/.github/instructions/{NOME}.instructions.md"] = (
        instrucoes + f"\n<!-- {AVISO} -->\n\n" + instrucao_resumo(lista_skills)
    )


LEIAME = """<!-- {aviso} -->

# Embalagens

Cópias das skills de `skills/` e do subagente de `agents/` no formato de cada ferramenta. Tudo aqui é gerado por `python ferramentas/gerar_embalagens.py`: pra mudar, edite a fonte e rode o script.

O Claude Code não tem pasta aqui: ele usa a fonte direto, como plugin (ver o README da raiz).

Nas cópias, `${{CLAUDE_SKILL_DIR}}` vira `<pasta-desta-skill>`, a parte braçal diz o que fazer quando não há subagente e a descrição do frontmatter vai entre aspas. O `regras-locais.md` de cada skill nunca entra.

| Pasta | Ferramenta | O que tem | Onde colocar |
|---|---|---|---|
| `codex/` | OpenAI Codex | `.agents/skills/<skill>/` e `.codex/agents/<agente>.toml` | No projeto, as duas pastas na raiz. Pra todos os projetos, as skills em `~/.agents/skills/` e o agente em `~/.codex/agents/` |
| `gemini/` | Gemini CLI | Extensão: `gemini-extension.json`, `GEMINI.md`, `skills/`, `agents/` | `gemini extensions install <clone>/embalagens/gemini` (ou `gemini extensions link` pra acompanhar o clone). Subagente de extensão ainda é prévia no Gemini CLI |
| `cursor/` | Cursor | `.cursor/skills/`, `.cursor/agents/` e uma regra `.cursor/rules/{nome}.mdc` pedida pelo agente | A pasta `.cursor/` na raiz do projeto, ou skills e agente em `~/.cursor/skills/` e `~/.cursor/agents/` |
| `copilot/` | GitHub Copilot | `.github/skills/`, `.github/agents/<agente>.agent.md` e `.github/instructions/{nome}.instructions.md` | A pasta `.github/` na raiz do repositório. No Copilot CLI, skills e agente também valem em `~/.copilot/skills/` e `~/.copilot/agents/` |

Copie as três skills juntas, lado a lado: as skills legal e site usam o script da skill de segurança pela pasta vizinha.

Cursor sem MCP: as skills não têm servidor, o script roda pelo terminal do agente.

Nenhuma dessas embalagens foi testada na ferramenta ainda. O teste de cada uma é a issue #14.
"""


def montar():
    lista_skills = skills()
    lista_agentes = agentes()
    arquivos = {}
    embalagem_codex(arquivos, lista_skills, lista_agentes)
    embalagem_gemini(arquivos, lista_skills, lista_agentes)
    embalagem_cursor(arquivos, lista_skills, lista_agentes)
    embalagem_copilot(arquivos, lista_skills, lista_agentes)
    arquivos["README.md"] = LEIAME.format(aviso=AVISO, nome=NOME)
    return arquivos


def existentes():
    if not SAIDA.exists():
        return {}
    return {
        c.relative_to(SAIDA).as_posix(): ler(c)
        for c in SAIDA.rglob("*")
        if c.is_file()
    }


def main():
    parser = argparse.ArgumentParser(description="Gera as embalagens de cada ferramenta a partir de skills/ e agents/.")
    parser.add_argument("--conferir", action="store_true", help="só confere se embalagens/ está em dia (sai com 1 se não)")
    args = parser.parse_args()

    novos = montar()
    if args.conferir:
        atuais = existentes()
        diferentes = sorted(
            set(novos) ^ set(atuais) | {k for k in set(novos) & set(atuais) if novos[k] != atuais[k]}
        )
        if diferentes:
            print("embalagens/ desatualizada. Rode python ferramentas/gerar_embalagens.py. Diferenças:")
            for caminho in diferentes:
                print(f"  {caminho}")
            return 1
        print(f"embalagens/ em dia ({len(novos)} arquivos)")
        return 0

    if SAIDA.exists():
        shutil.rmtree(SAIDA)
    for relativo, conteudo in novos.items():
        destino = SAIDA / relativo
        destino.parent.mkdir(parents=True, exist_ok=True)
        with open(destino, "w", encoding="utf-8", newline="\n") as f:
            f.write(conteudo)
    print(f"{len(novos)} arquivos gerados em {SAIDA.relative_to(RAIZ).as_posix()}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
