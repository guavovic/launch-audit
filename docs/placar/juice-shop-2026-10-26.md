# OWASP Juice Shop

Primeira rodada de placar da skill `auditoria-seguranca` contra um alvo com gabarito oficial. O objetivo não é ganhar o CTF do Juice Shop: é medir quanto da segurança real a skill enxerga **sem atacar**, confirmando controles por leitura de código e checagem passiva, e deixar claro o que fica fora desse alcance.

## A rodada

| Campo | Valor |
|---|---|
| Data | 26/10/2026 |
| Alvo | OWASP Juice Shop 20.3.0, em Docker, só no local (`http://127.0.0.1:3000`) |
| Gabarito | lista oficial de `GET /api/Challenges` (116 desafios, com nome, categoria e dificuldade) |
| Skill | `auditoria-seguranca` da `main` em 26/10/2026 (commit `e942e0e`) |
| Modelo | orquestração em Claude Opus 5.5 (este relatório); a parte braçal normalmente iria pro subagente `auditoria-executor` em Sonnet, aqui a orquestração fez tudo |
| Fonte do código | tirada do container com `docker cp` (só leitura), porque a imagem é distroless e não tem shell |

O teste ativo foi só nesse alvo local. Nada contra produção ou outro host. Nenhum container foi parado ou removido (o `juice-shop` segue de pé, e o `logz-mongo-database` não foi tocado).

## Como classifiquei cada desafio

- **Acerto:** a skill aponta o controle que falta, com evidência observável (linha de código, código HTTP, cabeçalho, arquivo exposto), sem rodar o ataque.
- **Fora do alcance:** o desafio só aparece explorando (payload, força bruta, OSINT, esteganografia, decodificar conteúdo escondido, corrida de requisição, DoS) ou é um enigma de CTF sem controle por trás. A skill confirma controle, não ataca, então não reivindica esses.
- **Não achado:** controle que a skill deveria cobrir e que esta rodada não trouxe à tona.
- **Falso positivo:** achado que não é falha de verdade.

Vários desafios diferentes nascem do mesmo buraco. Quando isso acontece, está dito na categoria: 7 desafios de injeção SQL saem de 2 pontos de código, 3 desafios de dado exposto saem de uma única listagem de diretório. Contei pelo nome do desafio, como o gabarito faz, mas sem fingir que são achados independentes.

## Placar

| | Quantidade | Do gabarito (116) |
|---|---|---|
| Acertos | 57 | 49% |
| Fora do alcance | 58 | 50% |
| Não achados | 1 | 1% |
| Falsos positivos | 2 | (não contam no gabarito) |

Perto da metade do gabarito é alcançável por uma auditoria que confirma controle sem atacar, e a skill cobriu essa parte. O resto é, por natureza, trabalho de exploração: a leitura honesta é que esses 58 não são "falha da skill", são o limite declarado dela.

## Por categoria

| Categoria | Total | Acertos | Fora do alcance | Não achado |
|---|---|---|---|---|
| Injection | 14 | 14 | 0 | 0 |
| Broken Access Control | 12 | 8 | 3 | 1 |
| Improper Input Validation | 12 | 7 | 5 | 0 |
| Sensitive Data Exposure | 17 | 5 | 12 | 0 |
| Vulnerable Components | 9 | 6 | 3 | 0 |
| XSS | 9 | 6 | 3 | 0 |
| Security Misconfiguration | 5 | 2 | 3 | 0 |
| Observability Failures | 4 | 2 | 2 | 0 |
| Broken Authentication | 9 | 2 | 7 | 0 |
| Unvalidated Redirects | 2 | 2 | 0 | 0 |
| Cryptographic Issues | 5 | 1 | 4 | 0 |
| Broken Anti Automation | 4 | 1 | 3 | 0 |
| XXE | 2 | 1 | 1 | 0 |
| Insecure Deserialization | 3 | 0 | 3 | 0 |
| Miscellaneous | 6 | 0 | 6 | 0 |
| Security through Obscurity | 3 | 0 | 3 | 0 |
| **Total** | **116** | **57** | **58** | **1** |

## Os acertos, pelo controle que falta

Cada item é o controle ausente e a evidência, sem receita de ataque.

**Injection (14).** Dois pontos de montagem de consulta por junção de texto (login e busca de produtos) explicam os 7 desafios de SQL do gabarito (Login Admin, Login Bender, Login Jim, Database Schema, Christmas Special, Ephemeral Accountant, User Credentials): a consulta é montada com o texto do usuário dentro da string, sem parâmetro. Uma consulta de avaliações usa operador que roda expressão com texto concatenado, o que responde pelos 3 desafios NoSQL (NoSQL Manipulation, NoSQL DoS, NoSQL Exfiltration). O perfil de usuário monta um modelo de página por substituição de texto, abrindo injeção de template (SSTi). A integração de IA do chat trata texto do usuário com autoridade de instrução, abrindo as três variações de prompt (Chatbot Prompt Injection, Greedy Chatbot Manipulation, System Prompt Extraction). Evidência: `routes/login.ts`, `routes/search.ts`, `routes/showProductReviews.ts`, `routes/userProfile.ts`, `routes/chat.ts`.

**Broken Access Control (8).** Leitura e escrita por identificador sem filtro pelo dono da sessão em cesta, item de cesta, avaliação e feedback (View Basket, Manipulate Basket, Forged Review, Forged Feedback: IDOR). Campo de dono vindo do corpo da requisição em vez da sessão (parte do Forged Feedback: mass assignment). Rota de administração sem checagem de papel no servidor, só escondida no cliente (Admin Section: BFLA). Alteração de produto por requisição direta (Product Tampering). Busca de URL arbitrária pelo servidor, sem lista de domínios permitidos (SSRF). Evidência: `routes/basket.ts`, `routes/basketItems.ts`, `routes/createProductReviews.ts`, `routes/updateProductReviews.ts`, `routes/profileImageUrlUpload.ts` e a ausência de checagem de papel nas rotas de administração.

**Improper Input Validation (7).** Validação só no cliente em cadastro e avaliação (Repetitive Registration, Empty User Registration, Zero Stars). Campo de papel aceito do corpo no cadastro (Admin Registration: mass assignment de privilégio). Tamanho e tipo de arquivo conferidos pela extensão do nome, não pelo conteúdo nem por limite real no servidor (Upload Size, Upload Type). Nome de arquivo vindo do usuário monta caminho no disco (Poison Null Byte: travessia de caminho). Evidência: `routes/fileUpload.ts` (confere `endsWith` da extensão), `routes/fileServer.ts` (`path.resolve('ftp/', file)`), handlers de cadastro.

**Sensitive Data Exposure (5).** Listagem de diretório ligada numa pasta pública expõe arquivos que não deviam estar lá, incluindo documento confidencial e dois backups esquecidos (Confidential Document, Forgotten Developer Backup, Forgotten Sales Backup: um único controle, autoindex ligado, três desafios). Credencial de conta de teste embutida no código do front (Exposed Credentials). Rota do usuário atual devolve os campos que o cliente pedir, sem lista permitida, o que inclui o hash de senha (Password Hash Leak). Evidência: `/ftp/` responde com índice navegável listando `.bak`, `.md` e outros; `src/app/login/login.component.ts`; `routes/currentUser.ts`.

**Vulnerable Components (6).** Dependências fixadas em versões muito antigas e com falha conhecida, mais nomes que imitam pacotes famosos (Vulnerable Library, Legacy Typosquatting, Frontend Typosquatting). Biblioteca de token sem algoritmo fixo no verificador, o que permite token sem assinatura e confusão de algoritmo (Unsigned JWT, Forged Signed JWT). Descompactação de arquivo enviado sem proteger o caminho de destino (Arbitrary File Write). Evidência: `package.json` (biblioteca de JWT e de sanitização em versões de muitas versões atrás), `lib/insecurity.ts`, `routes/fileUpload.ts` (uso de descompactador).

**XSS (6).** Falta de política de segurança de conteúdo no cabeçalho (CSP Bypass, confirmado: a resposta não traz `Content-Security-Policy`). Pontos no cliente que marcam HTML como confiável sem sanitizar de verdade (DOM XSS, Reflected XSS, API-only XSS). Biblioteca de sanitização antiga, com contorno conhecido, usada nos dois lados (Client-side e Server-side XSS Protection). Evidência: ausência do cabeçalho na resposta, `bypassSecurityTrustHtml` em componentes do front, versão da biblioteca de sanitização no `package.json`.

**Security Misconfiguration (2).** Middleware de erro de desenvolvimento ligado, devolvendo detalhe técnico ao cliente (Error Handling). Interface B2B marcada como "descontinuada por segurança" que ainda processa o envio (Deprecated Interface). Evidência: `errorhandler()` montado no servidor, `routes/fileUpload.ts`.

**Observability Failures (2).** Endpoint de métricas aberto sem autenticação (Exposed Metrics, confirmado: `/metrics` responde 200 com as séries). Rota que serve arquivo de log pelo nome, sem controle (Access Log). Evidência: `GET /metrics` público, `routes/logfileServer.ts`.

**Broken Authentication (2).** Sem política de força de senha (Password Strength). Troca de senha que só confere a senha atual quando ela é enviada, e recebe as senhas pela URL (Change Bender's Password). Evidência: `routes/changePassword.ts`, ausência de regra de senha no cadastro.

**Unvalidated Redirects (2).** Redirecionamento validado por "começa com" contra uma lista, o que deixa passar URL que contém um endereço permitido como pedaço (Outdated Allowlist, Allowlist Bypass). Evidência: `routes/redirect.ts` e `lib/insecurity.ts` (`startsWith` na lista).

**Cryptographic Issues (1).** Hash fraco (MD5) para senha e chave privada embutida no código (Weird Crypto). Evidência: `lib/insecurity.ts` (`crypto.createHash('md5')`, bloco de chave privada RSA literal e segredo de HMAC fixo). A chave privada no código foi registrada como achado crítico à parte.

**Broken Anti Automation (1).** O limite de tentativas da redefinição de senha existe, mas a chave do limite vem de um cabeçalho que o próprio cliente define, então não segura quem troca o cabeçalho (Reset Morty's Password). Evidência: `server.ts`, `keyGenerator` do `rateLimit` em `/rest/user/reset-password`.

**XXE (1).** Leitor de XML com substituição de entidade e carregamento de entidade externa ligados, no caminho de upload (XXE Data Access). Evidência: `lib/xml.ts` (comentário e configuração declaram entidade externa habilitada), `routes/fileUpload.ts`.

## Fora do alcance (58)

Não são falhas da skill, são o que uma auditoria sem ataque não pode afirmar. Em resumo, por tipo:

- **Enigmas de CTF e descoberta:** achar a Score Board, visitar a política de privacidade, esteganografia, decodificar conteúdo escondido, ovos de páscoa.
- **Segredo fora do código-fonte:** Leaked API Key (a chave não está no código copiado do container; só aparece garimpando outros lugares).
- **OSINT e adivinhação:** redefinir senha por pergunta de segurança de pessoas específicas (Jim, Bender, Bjoern, Morty, Uvogin), descobrir senha por pista fora do sistema (Login Amy, MC SafeSearch), geolocalização por metadado de imagem.
- **Exploração de regra de negócio:** cupom expirado ou forjado, fraude de desconto, quantidade negativa, esvaziar carteira por corrida de requisição.
- **DoS e execução via payload:** as três de desserialização insegura (Memory Bomb, Blocked e Successful RCE DoS) e o XXE DoS. A skill aponta o ponto de código perigoso, mas não dispara o travamento.
- **Web3 e nicho:** sandbox Web3, NFT, blockchain, mint de token.

Em alguns desses a skill chegou a anotar o controle fraco por trás (por exemplo, o ponto de execução de código via dependência de sandbox, que sustenta os desafios de RCE DoS), mas como o desafio só se prova explorando, não entrou como acerto, pra não inflar o placar.

## Não achado (1)

- **AI Debugging (Broken Access Control):** rota de depuração de IA com acesso indevido. A skill lista as rotas e checa papel nas de administração, mas não destacou essa como alvo nesta rodada. Fica como miss honesto.

## Falsos positivos (2)

- **Ruído da busca por segredo.** O padrão de busca de segredo casa com nomes de variável como `password`, `token` e `secret` espalhados pelo código, que são identificadores, não segredos vazados. Esperado nesse tipo de varredura, mas é ruído que o relatório precisa separar do achado real (a chave privada embutida, essa sim verdadeira).
- **Dependências de nome incomum tratadas como suspeitas.** Alguns pacotes legítimos de versão baixa ou nome pouco comum entram na peneira de "pacote inventado / typosquat" e precisam de conferência manual no registro antes de virar achado.

## Custo

- **Tempo de relógio:** aproximadamente 40 minutos, da leitura da skill ao relatório, com o alvo já de pé. A maior parte foi leitura de código e classificação dos 116 desafios, não execução de ferramenta.
- **Tokens (estimativa):** da ordem de 120 a 160 mil tokens na orquestração em Opus 5.5, somando a leitura da skill e do código-fonte, as checagens e a redação. É estimativa, não medição: a conta não foi instrumentada nesta rodada.

Observação de custo: rodar tudo na orquestração (Opus) é mais caro do que o desenho da skill, que manda a parte braçal (buscas, varreduras, checagem passiva) pro subagente em Sonnet. Numa próxima rodada, delegar essa parte deve baixar bastante o custo sem mexer no resultado.

## Buracos na skill que a rodada mostrou

Dois buracos concretos, que a skill deveria cobrir sem atacar e não cobriu. Não foram corrigidos nesta entrega: cada um virou issue.

- **A checagem passiva não roda contra alvo local em HTTP.** O script `checagem_passiva.py` exige `https://` e encerra com qualquer outra coisa, mas a própria tabela de escopo da skill diz que `localhost` e container local são onde o teste ativo acontece. Resultado: contra o Juice Shop em `http://127.0.0.1:3000` toda a camada automática (cabeçalhos, cookies, listagem de arquivos sensíveis, robots, sourcemap) ficou de fora e teve que ser refeita na mão com `curl`. Issue #25.
- **Falta item explícito de XXE no checklist.** O checklist cobre injeção, desserialização, SSRF e upload, mas não tem uma linha pra entidade externa de XML (desligar DTD e entidade externa no leitor). O XXE do Juice Shop só apareceu porque a leitura manual abriu o leitor de XML. Sem essa linha, a skill passa perto e não olha. Issue #26.

## Próxima revisão

Repetir a rodada quando a camada passiva passar a aceitar alvo local (#25) e quando o checklist ganhar a linha de XXE (#26), pra medir o ganho. O mesmo método serve pros outros alvos do placar (crAPI na issue #3, comparação com ferramentas na #4).
