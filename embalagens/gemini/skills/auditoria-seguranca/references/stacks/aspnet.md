# ASP.NET Core: segurança

Carregar quando o projeto tem `*.csproj` com `Microsoft.NET.Sdk.Web`, `Program.cs` com `WebApplication.CreateBuilder`, ou `appsettings*.json`. Vale também pra EF Core (`Microsoft.EntityFrameworkCore*` no `.csproj`).

Primeiro passo: anotar a versão (`<TargetFramework>`) e o tipo de app (MVC/Razor Pages, Minimal API, Blazor, API com controllers), porque o padrão de antiforgery muda entre eles.

```bash
grep -rhoE "<TargetFramework>[^<]+" --include=*.csproj .
grep -nE "Add(Controllers|ControllersWithViews|RazorPages|RazorComponents|Antiforgery|Cors|Authentication)|Use(Antiforgery|Cors|Authentication|Authorization|Routing|Hsts|HttpsRedirection|ExceptionHandler|DeveloperExceptionPage|ForwardedHeaders)|MapOpenApi|UseSwagger" Program.cs Startup.cs 2>/dev/null
```

Cada item: **o que verificar**, **evidência**, **não se aplica**.

## Configuração e segredos

- **Segredo fora do `appsettings*.json`.** Connection string com senha, chave de API e chave de assinatura de JWT ficam em variável de ambiente, cofre (Azure Key Vault ou equivalente) ou, no desenvolvimento, no Secret Manager (`dotnet user-secrets`, que guarda fora do projeto e sem criptografia).
  - *Evidência*: ler `appsettings.json`, `appsettings.Production.json` e afins procurando `Password=`, `Pwd=`, `Key`, `Secret`, `Token`; conferir o histórico do git dos mesmos arquivos (`git log -p -- appsettings*.json`). Mostrar só os 4 primeiros caracteres.
  - *Não se aplica*: nunca.
- **Arquivos de publicação sem segredo.** `*.pubxml`, `*.pubxml.user`, `launchSettings.json` e `web.config` gerado às vezes carregam senha ou connection string.
  - *Evidência*: `git ls-files | grep -iE "pubxml|launchSettings|web\.config"` e leitura deles.
  - *Não se aplica*: projeto sem esses arquivos.
- **Ambiente de produção é Production.** `ASPNETCORE_ENVIRONMENT=Development` em produção liga a página de erro detalhada e o Secret Manager.
  - *Evidência*: variável no host, Dockerfile, `web.config` ou pipeline.
  - *Não se aplica*: nunca.

## Erros, documentação e diagnóstico

- **Página de erro do desenvolvedor só em Development.** `UseDeveloperExceptionPage` (ou o padrão do template) só dentro de `if (app.Environment.IsDevelopment())`; em produção, `UseExceptionHandler` com resposta genérica (`ProblemDetails` sem `exception`).
  - *Evidência*: o bloco condicional em `Program.cs`; no local, com `ASPNETCORE_ENVIRONMENT=Production`, um erro de validação comum devolve corpo genérico.
  - *Não se aplica*: nunca.
- **OpenAPI e Swagger fechados em produção.** `MapOpenApi`, `UseSwagger` e `UseSwaggerUI` dentro do bloco de Development, ou atrás de autorização.
  - *Evidência*: `Program.cs`; passivo, 1 requisição em `/swagger` e `/openapi/v1.json` em produção.
  - *Não se aplica*: API pública documentada de propósito (aí a documentação pode ficar aberta, sem rota interna listada).
- **EF Core sem log de dado sensível em produção.** `EnableSensitiveDataLogging` e `EnableDetailedErrors` só em Development; eles colocam valor de parâmetro no log.
  - *Evidência*: `grep -rn "EnableSensitiveDataLogging\|EnableDetailedErrors" --include=*.cs .` e o condicional em volta.
  - *Não se aplica*: projeto sem EF Core.

## CSRF e antiforgery

- **Antiforgery onde há cookie e formulário.** Razor Pages já protege; MVC precisa de `AddControllersWithViews` (só `AddControllers` não liga antiforgery) e o recomendado é `AutoValidateAntiforgeryTokenAttribute` global; Minimal API com `[FromForm]` exige `AddAntiforgery` + `UseAntiforgery`; Blazor precisa de `UseAntiforgery` no pipeline. No .NET 11 em diante, `CreateBuilder` também registra uma checagem automática de `Sec-Fetch-Site` e `Origin`.
  - *Evidência*: as chamadas acima em `Program.cs`; cada `[IgnoreAntiforgeryToken]` e `.DisableAntiforgery()` com o motivo.
  - *Não se aplica*: API autenticada só por token no header (Bearer), sem cookie de sessão. `DisableAntiforgery` é aceitável ali; em rota chamada pelo navegador com cookie, é achado.
- **O middleware não interrompe sozinho.** O antiforgery middleware marca a falha, mas o endpoint ainda roda; quem bloqueia é a validação do framework (Minimal API com formulário, filtros do MVC). Endpoint escrito à mão que lê o formulário direto do `HttpContext` precisa validar.
  - *Evidência*: endpoints que usam `Request.Form` ou `ReadFormAsync` sem binding.
  - *Não se aplica*: projeto sem formulário.

## XML

- **Leitor de XML sem DTD nem entidade externa.** `XmlReaderSettings` com `DtdProcessing = DtdProcessing.Prohibit` e `XmlResolver = null`; `XmlDocument` sem `XmlResolver`. Vale pra upload, SOAP, SVG e DOCX/XLSX lidos no servidor. Alternativa válida: o endpoint não aceita XML de entrada.
  - *Evidência*: `grep -rnE "XmlDocument|XmlReader|XmlSerializer|XDocument|DtdProcessing|XmlResolver" --include=*.cs .` e a configuração de cada leitor que recebe dado de fora.
  - *Não se aplica*: projeto que não lê XML vindo do usuário nem de sistema externo.

## CORS

- **Origem específica, nunca qualquer origem com credenciais.** `AllowAnyOrigin` junto de `AllowCredentials` é recusado pelo próprio CORS; `SetIsOriginAllowed(_ => true)` com `AllowCredentials` contorna essa trava e é inseguro. Curinga de subdomínio (`SetIsOriginAllowedToAllowWildcardSubdomains`) só se todos os subdomínios são confiáveis.
  - *Evidência*: cada `AddCors`/`WithOrigins`/`SetIsOriginAllowed` e de onde vem a lista (config de produção).
  - *Não se aplica*: API usada só pelo próprio domínio (sem CORS configurado é o certo, e o relatório diz que não precisa).
- **Ordem do pipeline.** `UseCors` depois de `UseRouting` e antes de `UseAuthorization`. CORS não é proteção: só relaxa a regra do navegador; a autorização tem que estar no endpoint.
  - *Evidência*: ordem das chamadas em `Program.cs`.
  - *Não se aplica*: projeto sem CORS.

## Autenticação e autorização

- **Negar por padrão.** `FallbackPolicy` exigindo usuário autenticado, ou `[Authorize]` no controller base, com `[AllowAnonymous]` explícito nas rotas públicas.
  - *Evidência*: `AddAuthorization(o => o.FallbackPolicy = ...)` ou a lista de controllers e endpoints sem `[Authorize]`/`RequireAuthorization`.
  - *Não se aplica*: API inteiramente pública (sem login).
- **JWT validado por inteiro.** `TokenValidationParameters` com emissor, audiência, tempo de vida e chave de assinatura conferidos; `RequireHttpsMetadata` só desligado no local.
  - *Evidência*: o bloco `AddJwtBearer`.
  - *Não se aplica*: projeto sem JWT.
- **Cookie de autenticação com atributos.** `HttpOnly`, `SecurePolicy = Always`, `SameSite` Lax ou Strict, expiração.
  - *Evidência*: `ConfigureApplicationCookie` ou `AddCookie`.
  - *Não se aplica*: projeto sem cookie de sessão.
- **Chaves do Data Protection persistidas.** Em mais de uma instância ou em container que reinicia, as chaves (que assinam cookie e antiforgery) precisam de armazenamento comum e protegido (`PersistKeysTo...` + `ProtectKeysWith...`), senão o login cai a cada deploy; e a pasta das chaves não pode ficar pública.
  - *Evidência*: `AddDataProtection()` em `Program.cs`.
  - *Não se aplica*: uma instância única em máquina com disco persistente.

## EF Core e dados

- **SQL só parametrizado.** `FromSql`, `FromSqlInterpolated`, `SqlQuery` e `ExecuteSql` parametrizam sozinhos. `FromSqlRaw`, `SqlQueryRaw` e `ExecuteSqlRaw` com string montada (concatenação ou `$"..."` com valor do usuário) são injeção. Nome de coluna ou ordenação vindos do usuário só por lista permitida.
  - *Evidência*: `grep -rnE "FromSqlRaw|SqlQueryRaw|ExecuteSqlRaw|ExecuteSqlCommand" --include=*.cs .` e a origem de cada parte da string.
  - *Não se aplica*: projeto sem SQL escrito à mão.
- **Over-posting.** Endpoint não faz binding direto na entidade do EF; usa DTO com os campos permitidos, pra `IsAdmin`, `TenantId` ou `OwnerId` nunca virem do body.
  - *Evidência*: parâmetros de ação/endpoint com tipo de entidade e chamadas `Update(entity)` vindas do request.
  - *Não se aplica*: API só de leitura.
- **Filtro pelo dono.** Toda consulta por id filtra pelo usuário ou organização da sessão; `HasQueryFilter` global ajuda em sistema multiempresa, e cada `IgnoreQueryFilters` tem motivo.
  - *Evidência*: queries de `Find`/`FirstOrDefault` por id nos endpoints logados.
  - *Não se aplica*: sistema sem dado por usuário.
- **Migrations revisadas e usuário do banco sem privilégio de dono em produção.** `Database.Migrate()` na inicialização exige que a aplicação rode com permissão de alterar o schema; o mais seguro é aplicar migration no deploy com outro usuário.
  - *Evidência*: `Migrate()` em `Program.cs` e o usuário da connection string de produção (nome, não senha).
  - *Não se aplica*: projeto sem EF Core ou ferramenta interna pequena (registrar como baixa).

## HTTPS e proxy

- **HTTPS e HSTS.** `UseHttpsRedirection` e `UseHsts` fora de Development.
  - *Evidência*: `Program.cs` e o header real lido pelo script passivo.
  - *Não se aplica*: quando o proxy na frente já faz os dois (confirmar na resposta real e dizer onde é feito).
- **Forwarded headers só de proxy conhecido.** Atrás de proxy, `UseForwardedHeaders` com `KnownProxies` ou `KnownNetworks`, senão o IP do cliente (usado em rate limit e log) pode ser forjado.
  - *Evidência*: configuração de `ForwardedHeadersOptions`.
  - *Não se aplica*: app exposto direto, sem proxy.
- **Rate limit nativo onde custa.** `AddRateLimiter` + `RequireRateLimiting` em login, cadastro, recuperação de senha e rota que gasta dinheiro.
  - *Evidência*: `Program.cs` e os endpoints marcados.
  - *Não se aplica*: API interna sem exposição pública.

## Fontes

- Microsoft Learn, Prevent Cross-Site Request Forgery (XSRF/CSRF) attacks in ASP.NET Core (versão padrão 10.0, com notas do 11.0): https://learn.microsoft.com/aspnet/core/security/anti-request-forgery
- Microsoft Learn, Enable Cross-Origin Requests (CORS) in ASP.NET Core: https://learn.microsoft.com/aspnet/core/security/cors
- Microsoft Learn, Safe storage of app secrets in development: https://learn.microsoft.com/aspnet/core/security/app-secrets
- Microsoft Learn, Handle errors in ASP.NET Core: https://learn.microsoft.com/aspnet/core/fundamentals/error-handling
- Microsoft Learn, Configure ASP.NET Core to work with proxy servers and load balancers: https://learn.microsoft.com/aspnet/core/host-and-deploy/proxy-load-balancer
- Microsoft Learn, Rate limiting middleware in ASP.NET Core: https://learn.microsoft.com/aspnet/core/performance/rate-limit
- Microsoft Learn, Configure ASP.NET Core Data Protection: https://learn.microsoft.com/aspnet/core/security/data-protection/configuration/overview
- Microsoft Learn, SQL Queries (EF Core): https://learn.microsoft.com/ef/core/querying/sql-queries
