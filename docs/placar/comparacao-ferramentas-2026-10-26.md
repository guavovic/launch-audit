# Comparação com OWASP ZAP, semgrep e Lighthouse

Mesmo alvo, mesma data e mesmo gabarito da [rodada do Juice Shop](juice-shop-2026-10-26.md): o que cada ferramenta acha sozinha, o que a skill `auditoria-seguranca` achou, o que só aparece juntando as duas e quanto cada uma custa.

## A rodada

| Campo | Valor |
|---|---|
| Data | 26/10/2026 |
| Alvo | OWASP Juice Shop 20.3.0, Docker, só no local (`http://127.0.0.1:3000`) |
| Gabarito | os 116 desafios oficiais, os mesmos da rodada da skill |
| Skill | resultado da rodada de 26/10 (57 acertos), sem repetir a rodada |
| ZAP | `ghcr.io/zaproxy/zaproxy:stable`, `zap-baseline.py` (só passivo, sem active scan), container com `--memory 1g` |
| semgrep | imagem oficial `semgrep/semgrep`, container com `--memory 1g`, sobre o código-fonte tirado do `juice-shop` (cópia só leitura, a mesma da rodada da skill) |
| Lighthouse | 13.5.0, mobile (padrão), Chrome headless |

Cada ferramenta rodou sozinha, uma por vez, com a RAM da máquina apertada. Os containers e as imagens do ZAP e do semgrep foram removidos no fim.

Observações de método:

- O `semgrep --config auto` se recusa a rodar com métricas desligadas. Em vez de ligar a telemetria, usei quatro conjuntos do registro público: `p/owasp-top-ten`, `p/javascript`, `p/typescript` e `p/nodejs` (169 regras, 825 arquivos, `node_modules` fora).
- O baseline do ZAP é um rastreio passivo curto: o Juice Shop é uma SPA e o baseline não usa o spider de AJAX, então ele viu poucas páginas de verdade (5 URLs com alertas, 116 URLs na contagem do rastreio).
- Pra decidir se uma ferramenta "acertou" um desafio usei o mesmo critério da rodada da skill: apontar o controle que falta, com evidência observável. Regra que casa com o ponto de código conta como acerto; ferramenta que aponta só o terreno geral não conta.
- O relatório não traz a saída bruta das ferramentas, porque ela contém URLs e trechos de código de ataque. Cada achado está descrito por regra, arquivo, cabeçalho e código HTTP.

## Resultado por ferramenta

| | OWASP ZAP baseline | semgrep | Lighthouse | Skill (rodada de 26/10) |
|---|---|---|---|---|
| Tempo de relógio | 63 s | 133 s (sem contar o download da imagem) | 77 s (inclui o download do pacote pelo `npx`) | cerca de 40 min |
| RAM | limite de 1 GB no container; RAM livre da máquina: 0,54 GB antes, 1,71 GB depois | limite de 1 GB; livre 1,51 GB antes | Chrome headless; livre 2,28 GB antes, 2,50 GB depois | contexto do modelo, sem processo pesado |
| Custo em tokens | zero | zero | zero | da ordem de 120 a 160 mil (estimativa do placar, não medição) |
| Achados | 9 alertas em 7 regras; 61 regras passaram; 0 falhas | 24 achados | 4 categorias com nota abaixo de 100 e 28 auditorias reprovadas ou com nota baixa | 57 acertos, 1 não achado, 2 falsos positivos |
| Desafios do gabarito | 1 de 116 | 16 de 116 (cerca de 14%) | 0 de 116 | 57 de 116 (49%) |

Aviso sobre a RAM do ZAP: a leitura de RAM livre logo antes da execução deu 0,54 GB, abaixo do corte de 0,8 GB que eu tinha definido, e ele rodou mesmo assim (a leitura anterior, antes do download da imagem, tinha dado 1,08 GB). Terminou sem erro, mas fica registrado como folga ruim. O pico real de cada processo não foi medido, só o limite do container e a RAM livre da máquina antes e depois.

### OWASP ZAP baseline

63 s. Regras que dispararam:

| Regra | Risco | URLs |
|---|---|---|
| Content Security Policy (CSP) Header Not Set | médio | 5 |
| Cross-Domain Misconfiguration (`Access-Control-Allow-Origin` com curinga) | médio | 5 |
| Cross-Origin-Embedder-Policy ausente | baixo | 5 |
| Cross-Origin-Opener-Policy ausente | baixo | 5 |
| Deprecated Feature Policy Header Set | baixo | 5 |
| Dangerous JS Functions (em `main.js` e num chunk do front) | baixo | 2 |
| Modern Web Application | info | 5 |
| Storable and Cacheable Content / Storable but Non-Cacheable | info | 6 |

Desafios do gabarito: **1**, o CSP Bypass (a resposta não traz `Content-Security-Policy`, o mesmo controle que a skill registrou). Há um indício vago: a regra de funções perigosas de JS cai no terreno do DOM XSS, mas não aponta o ponto que o desafio explora, então não conta.

Ruído: baixo. Nenhum alerta é falso, mas quase todos são higiene de cabeçalho (COOP, COEP, Feature Policy, cache) que não vira desafio do gabarito.

Um furo digno de nota: a regra de listagem de diretório ("Directory Browsing") **passou**, apesar de o rastreio ter visitado `/ftp` (200). A skill achou esse mesmo controle (autoindex ligado, três desafios). O baseline não pegou o que a listagem expõe.

### semgrep

133 s, 24 achados (7 como ERROR, 17 como WARNING). Em arquivos da aplicação (14 achados):

| Regra | Arquivo | O que casa |
|---|---|---|
| `express-sequelize-injection` | `routes/login.ts`, `routes/search.ts` | consulta montada por concatenação com texto do usuário |
| `code-string-concat` | `routes/userProfile.ts` | código montado por concatenação (injeção de template) |
| `express-open-redirect` | `routes/redirect.ts` | redirecionamento com destino vindo da requisição |
| `express-check-directory-listing` | `server.ts` (5 pontos) | listagem de diretório ligada em pastas públicas |
| `express-res-sendfile` | `routes/fileServer.ts`, `keyServer.ts`, `logfileServer.ts`, `quarantineServer.ts` | arquivo servido com nome vindo da requisição |
| `hardcoded-jwt-secret` | `lib/insecurity.ts` | chave embutida usada pra assinar o token |

Os outros 10 achados vêm de `data/static/codefixes/`, que são trechos didáticos do próprio Juice Shop (versões do código "certo" e "errado" de alguns desafios, mais exemplos de Terraform). Quatro repetem o padrão de SQL, seis são regras de infraestrutura em Terraform que não rodam no alvo. Contam como ruído, ou como duplicata do que já saiu em `routes/`.

Desafios do gabarito: **16**, todos pelo ponto de código, na mesma lógica da skill:

- Injeção SQL, 7 desafios (login e busca de produtos: dois pontos de código);
- SSTi, 1;
- Redirecionamentos, 2 (Outdated Allowlist e Allowlist Bypass);
- Listagem de diretório, 3 (Confidential Document, Forgotten Developer Backup, Forgotten Sales Backup);
- Access Log, 1 (rota de log por nome);
- Poison Null Byte, 1 (servir arquivo por nome vindo do usuário);
- Weird Crypto, 1 (chave embutida), só pela chave, sem o MD5.

O semgrep não pegou nada fora disso: sem NoSQL, sem IDOR e BFLA, sem mass assignment, sem SSRF, sem XXE, sem dependência vulnerável, sem upload, sem rate limit com chave controlável, sem hash MD5 de senha, sem validação só no cliente. Ele casa padrão sintático de classes conhecidas, e em Node/Express isso cobre bem injeção e alguns sinks.

### Lighthouse

77 s. Notas (mobile): desempenho 54, acessibilidade 87, boas práticas 100, SEO 91 e a categoria nova de agentes 18. Métricas: FCP 3,6 s, LCP 7,6 s, TBT 300 ms, CLS 0,163, Speed Index 4,1 s.

Auditorias reprovadas de qualidade: botões e diálogo sem nome acessível, contraste insuficiente, nome visível que não bate com o nome acessível, links não rastreáveis (SEO), JavaScript e CSS sem uso, trabalho excessivo da thread principal, mudança de layout, mapas de código-fonte faltando e imagens sem tamanho explícito.

Desafios do gabarito: **0**, como esperado, porque o Lighthouse não é ferramenta de segurança. Uma leitura útil: **boas práticas deu 100** num alvo cheio de falha. Boa nota de Lighthouse não diz nada sobre segurança.

Comparação com a skill de site: a `auditoria-site` não rodou nesta data nem neste alvo (a rodada de 26/10 foi só da skill de segurança). Comparo só o que dá: a skill manda rodar o Lighthouse como parte da auditoria (mobile e desktop), então o Lighthouse é exatamente a fonte das notas e dos Core Web Vitals que ela relataria. Aqui rodei só o mobile. O que a skill de site acrescenta além dele (formulários de ponta a ponta, 404, links quebrados, domínio, SPF/DKIM/DMARC, sitemap, analytics, itens de conversão) não se aplica a uma loja de treino em `127.0.0.1` e não foi medido.

## O que só cada lado acha

| Quem acha | O que |
|---|---|
| **Só as ferramentas** (a skill não registrou) | ZAP: `Access-Control-Allow-Origin` com curinga ([#32](https://github.com/guavovic/launch-audit-skills/issues/32)), COOP e COEP ausentes, Feature Policy ultrapassado, regras de cache, funções JS perigosas no front. semgrep: `sendFile` com nome vindo da requisição em `keyServer.ts` e `quarantineServer.ts` (a skill citou `fileServer.ts` e a rota de log, no mesmo padrão). Lighthouse: desempenho, acessibilidade, SEO, Core Web Vitals |
| **Só a skill** (nenhuma das três acha) | NoSQL (3), IDOR e BOLA em cesta, avaliação e feedback, mass assignment (papel no cadastro, dono do feedback), BFLA em rota de administração, SSRF, XXE, token sem assinatura e confusão de algoritmo, dependência antiga e typosquatting, upload por extensão e descompactação sem proteção de caminho, rate limit com chave controlada pelo cliente, MD5 em senha, validação só no cliente, injeção de prompt no chat, credencial de teste no front, hash de senha vazando na rota do usuário, `/metrics` aberto, middleware de erro de desenvolvimento ligado, interface B2B descontinuada que ainda processa, troca de senha pela URL |
| **Só juntando as duas** | o retrato completo: a skill traz controle de acesso, lógica e dependências (o que exige ler o código com contexto); o semgrep dá a confirmação determinística, com regra e linha, dos mesmos pontos de injeção, redirecionamento e listagem de diretório; o ZAP cobre o pacote de cabeçalhos e o CORS que a checagem passiva da skill ainda não olha; o Lighthouse cobre desempenho e acessibilidade. Na contagem do gabarito, **a união não passa de 57**: tudo que ZAP e semgrep acertaram já estava nos 57 da skill |
| **Onde a ferramenta é melhor** | tempo e custo: o semgrep achou 16 desafios do gabarito em 2 minutos e sem tokens, contra cerca de 40 minutos e 120 a 160 mil tokens da skill pra chegar nos mesmos pontos de injeção, redirecionamento e listagem. Nessa fatia (injeção por concatenação em Node/Express) o semgrep entrega o mesmo resultado por uma fração do custo, e é reproduzível. Em cabeçalhos de isolamento entre origens (COOP, COEP) e em CORS com curinga, o ZAP também levou vantagem: a skill não checou |
| **Onde a skill é melhor** | tudo que exige entender a regra de negócio, o dono do dado ou a cadeia: 57 contra 16 no gabarito; categorias inteiras (Broken Access Control, componentes vulneráveis, XXE, desserialização, anti-automação) ficam de fora das regras prontas |

Onde a ferramenta e a skill coincidem, o semgrep serve de checagem barata do que a skill diz, não de substituto.

## Custo lado a lado

| | Tempo | Tokens | RAM | Cobertura do gabarito |
|---|---|---|---|---|
| ZAP baseline | 63 s | 0 | 1 GB de limite | 1 |
| semgrep | 133 s | 0 | 1 GB de limite | 16 |
| Lighthouse | 77 s | 0 | Chrome headless | 0 |
| Skill de segurança | cerca de 40 min | 120 a 160 mil (estimativa) | só o contexto | 57 |
| As quatro juntas | cerca de 45 min | o mesmo da skill | ferramentas uma por vez | 57 (o ganho está fora do gabarito) |

Duas ressalvas de honestidade sobre a comparação:

- A skill e as ferramentas atacam coisas diferentes por desenho: a skill lê código e confirma controle, o semgrep casa padrões, o ZAP baseline só lê respostas, o Lighthouse mede a página. Comparar tudo contra o gabarito do Juice Shop favorece quem lê código e desfavorece quem mede a página.
- O ZAP rodou só como baseline, sem active scan. Com o scan ativo ele acharia bem mais, mas aí deixa de ser comparável: a skill não ataca.

## Buracos que a comparação mostrou na skill

- **A checagem passiva não olha `Access-Control-Allow-Origin`.** O ZAP achou o curinga na home do Juice Shop com uma leitura de cabeçalho, e a skill já trata "CORS amplo com credenciais" como risco médio, mas o script só lê CSP, HSTS, nosniff, Referrer-Policy e Permissions-Policy. Issue [#32](https://github.com/guavovic/launch-audit-skills/issues/32).

Os demais itens do ZAP (COOP e COEP, cache, Feature Policy) são higiene de baixo valor pra um site comum e não viraram issue. O `sendFile` extra do semgrep está na mesma família do que a skill já cobre.

## Reprodução

Três comandos no alvo local: o container do ZAP chama `zap-baseline.py` apontando pro host do Docker (`host.docker.internal:3000`); o semgrep roda `semgrep scan` com os quatro conjuntos do registro sobre o código copiado do container; o Lighthouse roda com `npx lighthouse http://127.0.0.1:3000 --output json`. Os relatórios brutos ficaram fora do repositório, de propósito.
