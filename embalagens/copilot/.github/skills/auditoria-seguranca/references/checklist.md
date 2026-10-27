# Checklist de segurança por tema

Mapeado no OWASP Top 10:2025 (A01 a A10), OWASP API Security Top 10 e OWASP Top 10 pra LLM. Cada item: **o que conferir** e **como deve estar**.

## A01 Controle de acesso (inclui IDOR, BOLA e SSRF)

- **IDOR / BOLA**: toda leitura e escrita por id filtra pelo dono ou pela organização da sessão (`where id = ? and user_id = <usuário da sessão>`). Nunca confiar em `userId` vindo do cliente.
- **BFLA** (função de admin): rota admin checa papel no servidor, não só esconde o botão.
- **Mass assignment**: o handler escolhe os campos permitidos (DTO, `pick`, schema); `role`, `plan`, `credits`, `isAdmin` nunca vêm do body.
- **Negar por padrão**: middleware de auth cobre todas as rotas e a exceção (rota pública) é explícita.
- **Supabase**: RLS ligado em **todas** as tabelas expostas, com policy por `auth.uid()`; `service_role` só no servidor.
- **Firebase**: Rules sem `allow read, write: if true`; Storage idem.
- **SSRF**: URL vinda do usuário só é buscada pelo servidor com lista de domínios permitidos, sem IP interno, sem endereço de metadata da nuvem, sem seguir redirect pra fora.
- **Tudo o que o usuário não logado alcança**: listar rotas públicas e conferir que cada uma expõe só o que deve (inclui página estática com dado embutido e `__NEXT_DATA__`).

## A02 Configuração

- HTTPS em tudo, redirecionamento 301 e **HSTS** (`max-age` alto, `includeSubDomains`).
- Headers: `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`, `frame-ancestors` (ou `X-Frame-Options`).
- **CORS**: origem específica; nunca refletir qualquer origem junto com `credentials`.
- **Cookies** de sessão: `HttpOnly`, `Secure`, `SameSite=Lax` ou `Strict`, prefixo `__Host-` quando der.
- **Modo debug desligado** em produção; sem rota de debug, seed ou teste, Swagger e GraphQL introspection fechados, painel admin com proteção extra.
- **Banco** sem porta aberta pra internet, sem senha padrão, usuário da aplicação sem privilégio de dono.
- Bucket de arquivos privado por padrão; URL assinada pra download.
- Sourcemap de produção não publicado (ou só enviado pro Sentry).
- **Versão antiga ou alternativa da API** (`/v1`, `/legacy`, subdomínio esquecido) com as mesmas proteções da atual, ou desligada.
- TLS 1.2 ou mais novo; protocolo e cifra antigos desligados (evita downgrade).

## A03 Cadeia de suprimentos

- Lockfile versionado; `npm ci` no build.
- `npm audit` / `pip-audit` / `dotnet list package --vulnerable` sem Crítica ou Alta sem justificativa.
- **Pacote inventado** (slopsquatting): todo pacote existe no registro oficial e tem histórico, mantenedor e downloads coerentes. Desconfiar de nome parecido com um famoso, típico de sugestão de IA.
- Scripts `postinstall` de dependência conferidos; Dependabot ou Renovate só em projeto que vai durar.
- Script de CDN com versão fixa e, quando der, `integrity` (SRI).
- GitHub Actions com versão fixa e `permissions` mínimas.

## A04 Criptografia e segredos

- **Senha**: Argon2id, bcrypt ou scrypt. Nunca MD5 ou SHA puro, texto puro ou criptografia reversível.
- **Segredo** só em variável de ambiente do servidor ou cofre; `.env` no `.gitignore`; `.env.example` sem valor real.
- Nada de segredo em variável pública de front (`NEXT_PUBLIC_`, `VITE_`, `REACT_APP_`, `EXPO_PUBLIC_`), app mobile ou repositório público.
- Chave de API de terceiro com escopo mínimo e limite de gasto.
- Dado sensível (documento, token OAuth de terceiro) cifrado em repouso.

## A05 Injeção

- **SQL**: só query parametrizada ou ORM. Atenção a métodos "raw" com concatenação e a ordenação ou nome de coluna vindos do usuário (usar lista permitida).
- **NoSQL**: objeto do body não vai direto pro filtro.
- **XSS**: framework escapa por padrão; revisar todo HTML injetado à mão e todo markdown renderizado (sanitizar com DOMPurify ou equivalente); CSP como segunda barreira.
- **Comando do sistema**: texto do usuário nunca vira comando.
- **Template**: texto do usuário não vira template.
- **XML (XXE)**: em todo ponto que lê XML (upload, SOAP, SVG, DOCX/XLSX, importação, feed), o parser está com DTD e entidade externa desligados, ou o endpoint não aceita XML de entrada. Confirmar a configuração do leitor no código; a opção muda por biblioteca: Java (`disallow-doctype-decl` e `FEATURE_SECURE_PROCESSING` na fábrica do parser), .NET (`DtdProcessing.Prohibit` e `XmlResolver` nulo), PHP (não usar `LIBXML_NOENT`; libxml recente já vem seguro), Python (`defusedxml`, ou `resolve_entities=False` e `no_network=True` no lxml), Node (`noent` não ligado em `libxmljs`; preferir leitores que não resolvem entidade externa).
- **Caminho de arquivo**: nome vindo do usuário nunca monta caminho no disco.
- **Validação no back** com schema (Zod, Joi, FluentValidation, Pydantic) em todo endpoint. Validação no front é só UX, nunca segurança.

## A06 Design

- Regra de negócio no servidor: preço, estoque, cupom, quantidade, crédito.
- Fluxo que custa dinheiro (SMS, e-mail, LLM, upload grande) tem cota por usuário e por IP.
- Formulário: botão bloqueado durante o envio **e** idempotência no servidor (evita registro duplicado).

## A07 Autenticação e sessão

- Política de senha razoável (tamanho mínimo, bloqueio de senha vazada), sem limite máximo baixo.
- **Rate limit e bloqueio progressivo** no login, cadastro, recuperação de senha e verificação de código (contra força bruta).
- Mensagem igual pra "usuário não existe" e "senha errada" (evita enumeração de contas).
- Recuperação de senha com token de uso único e validade curta.
- **Sessão**: expira por inatividade e por tempo absoluto; logout invalida no servidor; troca de senha derruba as outras sessões.
- **JWT**: algoritmo fixo no verificador, expiração curta, refresh token rotativo, preferir cookie HttpOnly a `localStorage`; sem dado sensível no payload.
- **2FA**: obrigatório pra admin; oferecido ao usuário quando há dinheiro ou dado sensível.

## A08 Integridade

- Webhook (Stripe, Mercado Pago, GitHub) com assinatura verificada.
- Deserialização só de formato seguro.
- Pipeline de deploy protegido (branch protegida, segredo do CI com escopo mínimo).

## A09 Logs e alertas

- Log de login, falha de login, troca de senha, ação de admin, erro 5xx.
- Log **sem** senha, token, documento completo ou cartão.
- Alerta pra pico de 5xx, de 401/429 e de custo de API.
- Rastreamento de erro (Sentry ou similar) e monitor de uptime.
- Marco Civil: provedor de aplicação com fins econômicos guarda log de acesso por 6 meses (ver skill auditoria-legal).

## A10 Condições excepcionais

- Resposta de erro genérica pro cliente; detalhe só no log. Sem stack, query, caminho de arquivo ou versão de framework.
- Falha fecha (fail closed): se a checagem de permissão der erro, nega.
- Timeout e limite de tamanho em requisição, upload e chamada externa.

## Upload

- Tipo conferido pelo conteúdo, não só pela extensão; tamanho máximo; nome gerado pelo servidor.
- Guardado fora da raiz pública ou em bucket; servido com `Content-Disposition` e tipo correto.
- Imagem reprocessada (remove metadados); SVG tratado como risco ou proibido.
- Arquivo que é XML por dentro (SVG, DOCX, XLSX) lido com o parser seguro da linha de XML em A05.

## Bots e abuso

- Rate limit por IP **e** por conta, resposta 429.
- Anti-bot proporcional: honeypot e tempo mínimo de preenchimento no formulário simples; Turnstile, hCaptcha ou reCAPTCHA onde há abuso; proteção gerenciada (Cloudflare, Vercel Firewall) pra site com tráfego ou pagamento.
- **WAF**: recomendado quando há login, pagamento ou API pública; não substitui corrigir o código.
- Enumeração de rotas: rota interna não depende de "ninguém sabe a URL".

## LLM (app que usa IA)

- **Prompt injection**: texto do usuário e conteúdo externo (página, PDF, e-mail) nunca têm autoridade de instrução; papel de sistema separado; saída do modelo tratada como entrada não confiável (escapar antes de renderizar, validar antes de executar).
- Ferramentas que o modelo chama com permissão mínima e confirmação humana pra ação destrutiva.
- Prompt de sistema sem segredo.
- Limite de tokens e de gasto por usuário e global.
- Dado de um usuário não entra no contexto de outro.

## Operação

- **Backup** automático, de preferência fora do mesmo provedor, e **restore testado** (backup nunca testado não conta).
- **Migrations** versionadas, revisadas, com plano de volta; nada de alterar banco de produção na mão.
- **Rollback** do deploy rápido e sabendo qual versão voltar.
- **Plano de recuperação**: quem faz o quê se vazar segredo, cair o banco ou houver incidente com dado pessoal (prazo da ANPD na skill auditoria-legal).
- Contas de provedor (domínio, nuvem, GitHub, e-mail) com 2FA e senha única.
