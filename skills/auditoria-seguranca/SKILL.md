---
name: auditoria-seguranca
description: Audita a segurança real de um site, API ou aplicativo do usuário: descobre o perfil do projeto, decide quais proteções fazem sentido (e quais seriam exagero), varre o código e a configuração atrás de segredo exposto, falha de controle de acesso (IDOR/BOLA), injeção (SQL, XSS, prompt), SSRF, CSRF, CORS, autenticação e sessão fracas, upload sem validação, erro que vaza código, rota de debug, falta de rate limit e anti-bot, dependência vulnerável ou inventada, e operação (logs, backup, rollback, alerta). Testa de forma ativa só no local, e em produção só de forma passiva. Use quando o usuário pedir "o projeto tá seguro?", "auditoria de segurança", "valida a segurança", "pentest", "tem brecha?", "checa se vaza env", "precisa de WAF / rate limit / 2FA?", "antes de lançar", ou mandar um repo/URL pra revisar a segurança.
---

# Auditoria de segurança

**Regras locais:** se existir `regras-locais.md` nesta pasta, leia antes de tudo. Ele guarda as regras de quem usa a skill (alvos proibidos, onde salvar o relatório, qual navegador usar, como abrir issue) e vale acima do padrão daqui.

Objetivo: dizer **com evidência** se o projeto está seguro, o que falta, e **o que não precisa**. Proteção sem ameaça correspondente é custo; ameaça sem proteção é brecha. A auditoria entrega as duas listas.

Regra de ouro: **nada de chute**. Cada achado tem arquivo:linha, requisição ou saída de comando. Se não deu pra provar, vai como "não verificado" e diz o que falta pra verificar.

## 0. Escopo e autorização (antes de qualquer comando)

| Alvo | Pode |
|---|---|
| Código e config no disco | Tudo: ler, grep, scanners estáticos |
| `localhost` / container local | Teste ativo dos controles: acesso entre dois usuários, rate limit, validação de upload |
| Staging/preview do usuário | Ativo leve, só depois de o usuário confirmar a URL |
| Produção | **Só passivo**: headers, TLS, DNS, arquivos públicos (`/.env`, `/.git/`, sourcemap), 1 requisição por rota. Sem fuzzing, sem força bruta, sem payload que grava |
| Site de terceiro / da empresa | Não. Só com autorização por escrito do dono |

Regras fixas:
- Segredo encontrado **nunca** é escrito por inteiro no relatório, no chat ou em commit: mostrar só os 4 primeiros caracteres e onde está.
- Achou segredo vazado de verdade (no git, no bundle, em produção): **avisar na hora**, antes de terminar a auditoria. A correção é revogar e gerar outro; apagar do código não basta, ele já está no histórico.

## 1. Perfil do projeto (decide o que se aplica)

Descubra lendo o código, não perguntando. Pergunte só o que o código não responde.

1. **Tipo**: site estático / landing; site com formulário; SaaS com login; e-commerce/pagamento; API pública; app mobile; app com LLM; jogo com backend.
2. **Stack**: framework, onde roda (Vercel, VPS, Supabase, Firebase...), banco, auth (própria, NextAuth, Supabase Auth, Clerk...).
3. **Dados**: que dado pessoal guarda? Senha? Documento? Pagamento? Dado de criança? Token de terceiro (Spotify, Google)?
4. **Superfície**: liste as rotas/páginas e endpoints. Marque cada um como **público** (sem login), **logado** ou **admin**.
5. **Quem ataca e por quê**: bot genérico (todo site), spam de formulário, scraping, conta roubada, fraude em pagamento, abuso de API paga (LLM, SMS, e-mail custam dinheiro).

**Checklist por stack:** com a stack descoberta no item 2, leia só o arquivo de `references/stacks/` de cada tecnologia que o projeto usa de fato: `vercel.md`, `astro.md`, `pwa.md` (service worker ou manifesto), `supabase.md`, `firebase.md`, `aspnet.md`. Stack sem arquivo segue só o checklist geral. Cada item desses arquivos já diz quando não se aplica: isso entra na parte "o que não precisa" do relatório.

Com isso, preencha a matriz (ela vai no relatório):

| Proteção | Estático | Formulário | Login | Pagamento | API pública | LLM |
|---|---|---|---|---|---|---|
| Headers + HTTPS + HSTS | sim | sim | sim | sim | sim | sim |
| Segredo fora do front/git | sim | sim | sim | sim | sim | sim |
| Validação no back + anti-spam | - | sim | sim | sim | sim | sim |
| Rate limit | - | sim | sim | sim | sim | sim (custo) |
| CSRF | - | se cookie | se cookie | sim | se cookie | - |
| Controle de acesso por objeto (IDOR/BOLA) | - | - | sim | sim | sim | sim |
| Senha com hash forte, sessão, bloqueio | - | - | sim | sim | se tiver | se tiver |
| 2FA | - | - | admin | admin + oferecer | admin | admin |
| WAF / proteção de bot gerenciada | opcional | recomendado | recomendado | sim | sim | sim |
| Prompt injection / limite de custo | - | - | - | - | - | sim |
| Backup + restore testado + rollback | - | se grava | sim | sim | sim | se grava |
| Logs de segurança + alerta | - | básico | sim | sim | sim | sim |

"-" = não precisa, e o relatório diz isso explicitamente (é a parte "o que não faz sentido").

## 2. Varredura estática

Parte braçal (Lighthouse, script passivo, npm audit, buscas no código, axe no navegador): delegue ao subagente `auditoria-executor` (Sonnet), passando o alvo, o que verificar, onde salvar e o caminho completo do script e de `references/comandos.md` da skill `auditoria-seguranca` (ele não tem como descobrir sozinho onde as skills foram instaladas). Eu fico com perfil, análise, severidade e relatório.

Siga `references/comandos.md` (comandos prontos). Em resumo, nesta ordem:

1. **Segredos**: no código, no **histórico do git**, nos arquivos `.env*` versionados, no **bundle do front** (`NEXT_PUBLIC_`, `VITE_`, `REACT_APP_`, `EXPO_PUBLIC_` são públicos por definição) e em sourcemaps.
2. **Arquivo sensível no projeto**: dump `.sql`, backup, `.pem`, `.key`, `id_rsa`, `.p12`, `credentials.json`, `service-account*.json`, `.npmrc` com token, `*.log`, planilha com dado de cliente.
3. **Dependências** (não aplicar `npm audit fix --force` às cegas: ele pode sugerir **downgrade** de versão major, como já aconteceu com `@astrojs/vercel` 11 → 8 por causa de um `path-to-regexp` usado só no build; avaliar se a falha roda em produção antes de classificar): `npm audit` / `pnpm audit` / `pip-audit` / `dotnet list package --vulnerable`; lockfile presente; **pacote inventado** (nome que não existe no registro ou foi publicado há dias com poucos downloads, típico de sugestão de IA); script `postinstall` estranho.
4. **Código**, domínio por domínio, seguindo `references/checklist.md`. O que mais rende, em ordem:
   - Toda rota/handler que lê `id`, `userId`, `orgId` da URL, body ou query: **filtra pelo dono da sessão?**
   - Toda query montada com concatenação ou template string.
   - Todo HTML injetado (`dangerouslySetInnerHTML`, `v-html`, `innerHTML`, `{@html}`, `set:html`, markdown renderizado).
   - Todo `fetch`/`axios`/`HttpClient` do servidor com URL vinda do usuário (SSRF).
   - Todo escape feito à mão: **teste que ele funciona** em vez de confiar no comentário. Ex.: em JS/TS, trocar `<` pela string com barra simples seguida de u003c não faz nada, porque essa string já é o próprio `<`; o certo é barra dupla (o texto literal de seis caracteres). Rode `node -e` com a mesma linha pra conferir.
   - Toda resposta de erro: devolve `stack`, `message` cru, query, caminho de arquivo?
   - Rotas de debug, seed, admin, `/api/test`, `/health` verboso, GraphQL introspection, Swagger aberto em produção.
   - Regras de banco gerenciado: **RLS do Supabase**, **Firebase Rules**, chave `service_role` no cliente.
5. Se houver, rode `semgrep --config auto` e `gitleaks`. Ferramenta que não está instalada: instale do meu lado se for leve (npx/pipx), senão anote como "não rodado".

## 3. Confirmar que as proteções funcionam

O objetivo aqui é **confirmar o controle**, não explorar. Basta uma evidência por item.

**No local**, com o app rodando:
- **Controle de acesso**: com dois usuários de teste, confira se o recurso de um aparece pra sessão do outro. A correção vem do código (filtro pelo dono na query), não do teste.
- **Rate limit e bloqueio de login**: algumas tentativas seguidas devem receber 429 ou bloqueio temporário. Use números pequenos, só o bastante pra ver o limite atuar.
- **CSRF, CORS e cookies**: veja os headers e os atributos do cookie de sessão nas respostas reais.
- **Upload**: confira no código e numa resposta real que tipo, tamanho e nome são validados no servidor e que o arquivo não é servido como executável.
- **Erros**: force um 404 e um erro de validação comum e veja se a resposta é genérica.
- Pra varredura automática no local, prefira as ferramentas prontas listadas em `references/comandos.md`, sempre apontadas pro localhost.

**Em produção (passivo)**: rode o script, que faz uma requisição por item com pausa entre elas e devolve JSON:

```bash
python -I "${CLAUDE_SKILL_DIR}/scripts/checagem_passiva.py" https://SITE --saida <pasta-temporaria>/passiva.json [--comparar <relatorio-anterior>.json] [--rota /uma/rota/real]
```

Pra **API sem página na raiz**, passe `--rota` com uma rota real: os headers são lidos dela, e as checagens de página (head, SEO, robots, sitemap) são puladas. Em resposta JSON, CSP, Permissions-Policy e proteção contra iframe saem como `info`; `nosniff` e HSTS continuam contando. No Git Bash, rode com `MSYS_NO_PATHCONV=1`, senão ele transforma `/rota` em caminho do Windows.

Contra **alvo local** (`localhost`, `127.0.0.0/8`, `::1` e nomes `.localhost`, `.local` ou `.test`) o script aceita `http://`, por exemplo `http://127.0.0.1:3000`. TLS, redirecionamento pra HTTPS, HSTS, o atributo `Secure` do cookie e DNS saem como `info` (não se aplica no local) e o resto das checagens roda normal. Alvo remoto continua exigindo `https://`: com `http://` o script encerra com a explicação.

Se o Python local não validar a cadeia de certificados de um site (`CERTIFICATE_VERIFY_FAILED`), o script não desliga a verificação: usa o armazenamento do sistema quando `truststore` está instalado (ou soma o `certifi`, se houver), registra a falha de TLS como achado dizendo se o certificado do alvo é inválido ou se a cadeia local está incompleta e, sem a home, encerra com mensagem e código 1 (o JSON sai igual). Nenhum dos dois pacotes é obrigatório: `pip install truststore` resolve.

Site com **fallback de SPA** (qualquer caminho devolve a home com 200) aparece marcado no detalhe: sitemap que não existe, 404 que não existe e arquivos que só parecem estar lá.

Ele cobre HTTPS e HSTS, TLS (versão, validade, TLS antigo), headers, CSP, cookies, compressão, `<head>` (title, description, og, favicon, lang, alt), scripts de terceiros e rastreadores, robots, sitemap, 404, sourcemap, arquivos sensíveis expostos e DNS (SPF, DMARC, CAA, MX). Guarde o JSON junto do relatório pra comparar na próxima revisão.

**Anti-bot (aprendido na primeira rodada real, 21/10/2026):** a Vercel (e a Cloudflare) passam a desafiar o IP depois que ele consulta `/.env` e `/.git`, e o bloqueio dura vários minutos, inclusive pra home e pro Lighthouse. Por isso:
- o script consulta os caminhos sensíveis **por último** e marca resposta de anti-bot como `bloqueado` (não verificado), nunca como falha;
- na auditoria completa, rode o **Lighthouse antes** do script de segurança;
- se bloquear, espere (verificar a home a cada minuto em segundo plano) ou siga com a parte de código.
O bloqueio é um ponto positivo do site (tem proteção contra varredura), e vale registrar.

## 4. Relatório

Salve em `auditorias/<projeto>-seguranca-AAAA-MM-DD.md` (na raiz do projeto auditado, ou onde as regras locais mandarem), com o JSON da checagem passiva ao lado. Sem valor de segredo no arquivo.

Estrutura:
1. **Veredito em uma linha**: "pode lançar", "pode lançar depois de X", ou "não lançar".
2. **Perfil e matriz** da etapa 1, com o "não precisa" explicado.
3. **Achados**, do mais grave pro menos grave:

| Severidade | Quando usar |
|---|---|
| Crítica | Segredo válido exposto, banco aberto, acesso a dado de outro usuário, execução remota, RLS desligado |
| Alta | Injeção possível, auth contornável, sem rate limit em login ou rota que custa dinheiro, upload sem validação |
| Média | Header faltando, CORS amplo com credenciais, erro vazando stack, sessão sem expiração |
| Baixa | Boa prática ausente sem caminho de ataque claro |
| Info | Recomendação de maturidade (WAF, 2FA opcional, monitoramento) |

Cada achado: **o quê**, **evidência** (arquivo:linha ou resposta), **impacto real**, **correção** concreta no padrão do projeto.

4. **Não verificado** e por quê.
5. **Próxima revisão** sugerida (padrão: a cada 3 a 6 meses ou antes de cada lançamento grande).

## 5. Depois do relatório

- Ofereça transformar cada achado Crítico ou Alto em issue. Não abra sem ok.
- Correção: só com ok, uma branch por tema. Segredo vazado: primeiro o dono revoga, depois limpa o código.
- Se o usuário quiser revisão recorrente, ofereça agendar (`/schedule` no Claude Code).

Checklist completo por tema: `references/checklist.md`. Detalhe por stack: `references/stacks/`.
