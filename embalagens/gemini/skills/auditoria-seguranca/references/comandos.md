# Comandos da auditoria

Rodar na raiz do repo. Ferramenta ausente: instalar se for leve (npx, pipx); senão anotar "não rodado".

## Segredos

```bash
# padrões comuns no código (fora de dependências e build)
grep -rInE "(api[_-]?key|secret|token|passw(or)?d|private[_-]?key|BEGIN (RSA|OPENSSH|EC) PRIVATE)" \
  --exclude-dir={node_modules,.git,dist,build,.next,out,Library,Temp} . | head -100

# .env versionado agora ou no passado
git ls-files | grep -iE "(^|/)\.env"
git log --all --diff-filter=A --name-only --format= | grep -iE "\.env|\.pem|\.key|id_rsa|credentials|service-account" | sort -u

# varredura com histórico, valores mascarados
gitleaks detect --source . --redact
```

Variáveis públicas do front (tudo aqui vai pro navegador):

```bash
grep -rhoE "(NEXT_PUBLIC|VITE|REACT_APP|EXPO_PUBLIC|PUBLIC)_[A-Z0-9_]+" --exclude-dir={node_modules,.git} . | sort -u
```

Depois do build, conferir se algum prefixo de chave privada conhecido aparece no bundle (`sk_live`, `service_role`, `AKIA`, `ghp_`) dentro de `.next/`, `dist/`, `out/` ou `build/`.

## Arquivos sensíveis

```bash
git ls-files | grep -iE "\.(sql|dump|bak|pem|key|p12|pfx|log|csv|xlsx)$|id_rsa|credentials|service-account|\.npmrc"
```

## Dependências

```bash
npm audit --omit=dev        # ou pnpm audit
npx --yes osv-scanner -r .  # multi-linguagem
pip-audit                   # Python
dotnet list package --vulnerable --include-transitive
```

Pacote suspeito: `npm view <pacote> time.created maintainers repository` e conferir downloads em npmjs.com.

## Análise estática

```bash
semgrep --config auto --error --quiet
```

## Leitores de XML no código

```bash
grep -rInE "DocumentBuilderFactory|SAXParserFactory|XMLInputFactory|TransformerFactory|XmlDocument|XmlReader|XmlSerializer|simplexml_load|DOMDocument|libxml_|libxmljs|xml2js|fast-xml-parser|lxml|etree|xml\.sax|xml\.dom|\.xml"   --exclude-dir={node_modules,.git,dist,build,.next,out,Library,Temp} --include=*.{java,cs,php,py,js,ts} . | head -100
```

Cada ocorrência que recebe dado de fora (upload, corpo de requisição, arquivo importado) tem a configuração do parser conferida contra a linha de XML em A05 do checklist.

## Passivo em produção (uma requisição por item)

```bash
curl -sSI https://SITE | grep -iE "strict-transport|content-security|x-content-type|referrer-policy|permissions-policy|x-frame|set-cookie|server|x-powered-by"
curl -sS -o /dev/null -w "%{http_code}\n" https://SITE/.env
curl -sS -o /dev/null -w "%{http_code}\n" https://SITE/.git/config
curl -sS https://SITE/robots.txt
nslookup -type=TXT SITE ; nslookup -type=TXT _dmarc.SITE ; nslookup -type=CAA SITE
```

Notas externas e passivas: securityheaders.com, ssllabs.com/ssltest, developer.mozilla.org/observatory, internet.nl.

## Varredura automática no local

OWASP ZAP no modo baseline, sempre apontado pro `localhost`. Nunca contra produção ou site de terceiro.
