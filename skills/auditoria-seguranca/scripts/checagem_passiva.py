"""Checagem passiva de um site em produção, usada pelas skills auditoria-seguranca, auditoria-legal e auditoria-site.

Faz só GETs simples (uma requisição por item) e consultas DNS públicas. Nada de fuzzing, força bruta ou escrita.

Uso:
    python -I checagem_passiva.py https://site.com [--saida resultado.json] [--comparar anterior.json] [--rota /rota/real]

Alvo local (localhost, 127.0.0.0/8, ::1, nomes .localhost, .local e .test) pode ir em http://. Alvo remoto exige https://.
"""

import argparse
import ipaddress
import json
import re
import socket
import ssl
import sys
import time
import warnings
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

TIMEOUT = 15
PAUSA = 0.7  # segundos entre requisições, pra não parecer varredura

warnings.filterwarnings("ignore", category=DeprecationWarning)
UA = "auditoria-passiva/1.0 (dono do site)"

HEADERS_SEGURANCA = {
    "strict-transport-security": "HSTS",
    "content-security-policy": "CSP",
    "x-content-type-options": "nosniff",
    "referrer-policy": "Referrer-Policy",
    "permissions-policy": "Permissions-Policy",
}
HEADERS_QUE_VAZAM = ["server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version"]

# Arquivos que nunca deveriam estar públicos. Cada um com um teste de conteúdo,
# porque site estático/SPA costuma devolver 200 com o HTML da home pra qualquer caminho.
ARQUIVOS_SENSIVEIS = {
    "/.env": lambda t: re.search(r"^[A-Z0-9_]+=", t, re.M),
    "/.env.local": lambda t: re.search(r"^[A-Z0-9_]+=", t, re.M),
    "/.env.production": lambda t: re.search(r"^[A-Z0-9_]+=", t, re.M),
    "/.git/HEAD": lambda t: t.startswith("ref:"),
    "/.git/config": lambda t: "[core]" in t,
    "/.DS_Store": lambda t: "Bud1" in t,
    "/.vscode/settings.json": lambda t: t.lstrip().startswith("{"),
    "/docker-compose.yml": lambda t: "services:" in t,
}

SUFIXOS_LOCAIS = (".localhost", ".local", ".test")

resultados = []
HOME = {"corpo": ""}
ALVO = {"local": False}


def e_host_local(host):
    host = (host or "").lower()
    if host == "localhost" or host.endswith(SUFIXOS_LOCAIS):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def e_fallback(corpo):
    """SPA que devolve a home com 200 pra qualquer caminho."""
    return bool(HOME["corpo"].strip()) and corpo.strip() == HOME["corpo"].strip()


def detalhe_status(status, corpo):
    return f"{status} com a home (fallback de SPA)" if status == 200 and e_fallback(corpo) else str(status)


def desafiado(status, headers):
    """Resposta de anti-bot (Vercel, Cloudflare): o item não foi verificado."""
    if (headers.get("x-vercel-mitigated") or headers.get("cf-mitigated")):
        return True
    return status in (403, 429, 503) and (headers.get("server") or "").lower() == "cloudflare"


def registrar(id_, status, detalhe, grupo):
    """status: ok | aviso | falha | info | bloqueado"""
    resultados.append({"id": id_, "grupo": grupo, "status": status, "detalhe": detalhe})


class Bloqueado(Exception):
    pass


class SemRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def buscar(url, seguir=True, limite=600_000):
    abridor = urllib.request.build_opener() if seguir else urllib.request.build_opener(SemRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "br, gzip"})
    try:
        resp = abridor.open(req, timeout=TIMEOUT)
    except urllib.error.HTTPError as e:
        resp = e
    corpo = resp.read(limite)
    return resp.status if hasattr(resp, "status") else resp.code, resp.headers, corpo, resp.geturl()


def buscar_texto(url, seguir=True):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    abridor = urllib.request.build_opener() if seguir else urllib.request.build_opener(SemRedirect)
    try:
        resp = abridor.open(req, timeout=TIMEOUT)
    except urllib.error.HTTPError as e:
        resp = e
    status = resp.status if hasattr(resp, "status") else resp.code
    time.sleep(PAUSA)
    if desafiado(status, resp.headers):
        raise Bloqueado(status)
    return status, resp.headers, resp.read(600_000).decode("utf-8", errors="replace"), resp.geturl()


class Cabeca(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lang = None
        self.titulo = ""
        self.no_titulo = False
        self.metas = {}
        self.links = []
        self.scripts = []
        self.imgs = []
        self.h1 = 0
        self.http_inseguro = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for v in a.values():
            if v and v.startswith("http://") and tag in ("script", "img", "link", "iframe", "source"):
                self.http_inseguro.append(v)
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "title":
            self.no_titulo = True
        elif tag == "meta":
            chave = a.get("name") or a.get("property")
            if chave:
                self.metas[chave.lower()] = a.get("content", "")
        elif tag == "link":
            self.links.append(a)
        elif tag == "script" and a.get("src"):
            self.scripts.append(a["src"])
        elif tag == "img":
            self.imgs.append(a)
        elif tag == "h1":
            self.h1 += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self.no_titulo = False

    def handle_data(self, data):
        if self.no_titulo:
            self.titulo += data


def doh(nome, tipo):
    url = f"https://cloudflare-dns.com/dns-query?name={urllib.parse.quote(nome)}&type={tipo}"
    req = urllib.request.Request(url, headers={"Accept": "application/dns-json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        dados = json.load(r)
    return [x.get("data", "").strip('"') for x in dados.get("Answer", []) if x.get("type") in (16, 257, 15, 1, 5)]


def checar_https(base):
    host = urllib.parse.urlparse(base).hostname
    if ALVO["local"]:
        for id_ in ("https-redirect", "tls"):
            registrar(id_, "info", "alvo local: não se aplica (sem TLS nem redirecionamento pra HTTPS)", "seguranca")
        return
    try:
        status, headers, _, _ = buscar_texto(f"http://{host}/", seguir=False)
        destino = headers.get("location", "")
        if status in (301, 308) and destino.startswith("https://"):
            registrar("https-redirect", "ok", f"HTTP redireciona com {status} pra HTTPS", "seguranca")
        elif destino.startswith("https://"):
            registrar("https-redirect", "aviso", f"redireciona pra HTTPS mas com {status} (preferir 301/308)", "seguranca")
        else:
            registrar("https-redirect", "falha", f"HTTP respondeu {status} sem ir pra HTTPS", "seguranca")
    except Bloqueado as b:
        registrar("https-redirect", "bloqueado", f"anti-bot respondeu {b}: não verificado", "seguranca")
    except Exception as e:
        registrar("https-redirect", "info", f"não deu pra testar HTTP: {e}", "seguranca")

    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=TIMEOUT) as s:
            with ctx.wrap_socket(s, server_hostname=host) as t:
                versao = t.version()
                cert = t.getpeercert()
        vence = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        dias = (vence - datetime.now(timezone.utc)).days
        registrar("tls-versao", "ok" if versao in ("TLSv1.3", "TLSv1.2") else "falha", versao, "seguranca")
        registrar("tls-certificado", "ok" if dias > 14 else "aviso", f"vence em {dias} dias ({vence:%d/%m/%Y})", "site")
    except Exception as e:
        registrar("tls", "falha", f"erro no TLS: {e}", "seguranca")

    try:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.maximum_version = ssl.TLSVersion.TLSv1_1
        ctx.minimum_version = ssl.TLSVersion.TLSv1
        with socket.create_connection((host, 443), timeout=TIMEOUT) as s:
            with ctx.wrap_socket(s, server_hostname=host):
                registrar("tls-antigo", "falha", "servidor ainda aceita TLS 1.0/1.1 (risco de downgrade)", "seguranca")
    except (ssl.SSLError, ValueError, OSError):
        registrar("tls-antigo", "ok", "TLS 1.0/1.1 recusados (ou não suportados pelo cliente local)", "seguranca")


def checar_headers(headers):
    # Em resposta JSON (API), CSP, Permissions-Policy e iframe pesam pouco; nosniff e HSTS continuam valendo.
    api = "json" in (headers.get("content-type") or "")
    so_html = ("content-security-policy", "permissions-policy")
    for h, nome in HEADERS_SEGURANCA.items():
        valor = headers.get(h)
        falta = "info" if api and h in so_html else "falha"
        if ALVO["local"] and h == "strict-transport-security":
            registrar(f"header-{nome}", "ok" if valor else "info",
                      valor or "ausente (alvo local: HSTS só vale em HTTPS)", "seguranca")
            continue
        registrar(f"header-{nome}", "ok" if valor else falta,
                  valor or ("ausente (resposta JSON: opcional)" if falta == "info" else "ausente"), "seguranca")
    if not (headers.get("x-frame-options") or "frame-ancestors" in (headers.get("content-security-policy") or "")):
        registrar("header-clickjacking", "info" if api else "falha",
                  "sem X-Frame-Options nem frame-ancestors" + (" (resposta JSON: opcional)" if api else ""), "seguranca")
    else:
        registrar("header-clickjacking", "ok", "protegido", "seguranca")
    csp = headers.get("content-security-policy") or ""
    if "'unsafe-inline'" in csp or "'unsafe-eval'" in csp:
        registrar("csp-unsafe", "aviso", "CSP com unsafe-inline/unsafe-eval", "seguranca")
    vazam = {h: headers.get(h) for h in HEADERS_QUE_VAZAM if headers.get(h)}
    if vazam:
        registrar("header-versao", "aviso" if any(re.search(r"\d", v) for v in vazam.values()) else "info",
                  f"revela tecnologia: {vazam}", "seguranca")
    for c in headers.get_all("set-cookie") or []:
        nome = c.split("=", 1)[0]
        exigidos = ("httponly", "samesite") if ALVO["local"] else ("secure", "httponly", "samesite")
        faltando = [f for f in exigidos if f not in c.lower()]
        registrar(f"cookie-{nome}", "aviso" if faltando else "ok",
                  f"faltando {faltando}" if faltando else "Secure, HttpOnly e SameSite", "seguranca")
    if (headers.get("content-encoding") or "") in ("br", "gzip"):
        registrar("compressao", "ok", headers.get("content-encoding"), "site")
    else:
        registrar("compressao", "aviso", "HTML sem br/gzip", "site")


def checar_cabeca(base, html):
    p = Cabeca()
    p.feed(html)
    host = urllib.parse.urlparse(base).hostname
    registrar("lang", "ok" if p.lang else "falha", p.lang or "sem lang no <html>", "site")
    t = p.titulo.strip()
    registrar("title", "ok" if 10 <= len(t) <= 65 else "aviso", f"{len(t)} caracteres: {t[:80]}", "site")
    d = p.metas.get("description", "")
    registrar("meta-description", "ok" if 50 <= len(d) <= 160 else "aviso", f"{len(d)} caracteres", "site")
    registrar("viewport", "ok" if "viewport" in p.metas else "falha", p.metas.get("viewport", "ausente"), "site")
    registrar("h1", "ok" if p.h1 == 1 else "aviso", f"{p.h1} h1 na página", "site")
    rels = {(l.get("rel") or "").lower(): l.get("href") for l in p.links}
    registrar("canonical", "ok" if rels.get("canonical") else "aviso", rels.get("canonical") or "ausente", "site")
    registrar("favicon", "ok" if any("icon" in r for r in rels) else "falha", "link rel=icon" if any("icon" in r for r in rels) else "ausente", "site")
    registrar("apple-touch-icon", "ok" if "apple-touch-icon" in rels else "aviso", rels.get("apple-touch-icon") or "ausente", "site")
    registrar("manifest", "ok" if "manifest" in rels else "info", rels.get("manifest") or "ausente", "site")
    for og in ("og:title", "og:description", "og:image", "og:url", "twitter:card"):
        valor = p.metas.get(og)
        registrar(og, "ok" if valor else "falha", valor or "ausente", "site")
    img = p.metas.get("og:image")
    if img and not img.startswith("https://"):
        registrar("og:image-absoluta", "falha", "og:image precisa de URL absoluta https", "site")
    sem_alt = [i.get("src") for i in p.imgs if "alt" not in i]
    registrar("img-alt", "ok" if not sem_alt else "falha",
              f"{len(sem_alt)} de {len(p.imgs)} imagens sem alt (no HTML inicial): {sem_alt[:5]}", "legal")
    sem_dim = [i.get("src") for i in p.imgs if not (i.get("width") and i.get("height"))]
    if sem_dim:
        registrar("img-dimensoes", "aviso", f"{len(sem_dim)} imagens sem width/height (CLS): {sem_dim[:5]}", "site")
    terceiros = sorted({urllib.parse.urlparse(urllib.parse.urljoin(base, s)).hostname for s in p.scripts} - {host})
    registrar("scripts-terceiros", "info" if terceiros else "ok",
              f"scripts de fora: {terceiros}" if terceiros else "nenhum script de terceiro no HTML inicial", "legal")
    rastreio = re.findall(r"googletagmanager|google-analytics|gtag\(|fbq\(|clarity\.ms|hotjar|connect\.facebook", html)
    registrar("rastreamento", "aviso" if rastreio else "ok",
              f"rastreio no HTML: {sorted(set(rastreio))} (conferir consentimento)" if rastreio else "nenhum rastreador conhecido no HTML", "legal")
    if p.http_inseguro:
        registrar("mixed-content", "falha", f"recursos em http://: {p.http_inseguro[:5]}", "seguranca")
    for nome, padrao in (("politica-privacidade", r"privacidade|privacy"), ("termos", r"termos|terms"), ("cookies", r"cookies")):
        registrar(f"link-{nome}", "ok" if re.search(padrao, html, re.I) else "info",
                  "menção encontrada no HTML" if re.search(padrao, html, re.I) else "nada encontrado (ver se o projeto precisa)", "legal")
    return p


def checar_arquivos(base):
    for caminho, parece in ARQUIVOS_SENSIVEIS.items():
        try:
            status, _, corpo, _ = buscar_texto(base + caminho, seguir=False)
            exposto = status == 200 and parece(corpo)
            registrar(f"exposto{caminho}", "falha" if exposto else "ok",
                      f"{status}: CONTEÚDO REAL PÚBLICO" if exposto else detalhe_status(status, corpo), "seguranca")
        except Bloqueado as b:
            registrar(f"exposto{caminho}", "bloqueado", f"anti-bot respondeu {b}: não verificado", "seguranca")
        except Exception as e:
            registrar(f"exposto{caminho}", "info", f"erro: {e}", "seguranca")


def checar_sourcemaps(base, p):
    js = [urllib.parse.urljoin(base, s) for s in p.scripts if urllib.parse.urlparse(urllib.parse.urljoin(base, s)).hostname == urllib.parse.urlparse(base).hostname]
    for url in js[:3]:
        try:
            status, _, corpo, _ = buscar_texto(url + ".map", seguir=False)
            exposto = status == 200 and '"mappings"' in corpo
            registrar(f"sourcemap:{urllib.parse.urlparse(url).path}", "aviso" if exposto else "ok",
                      "sourcemap público (expõe o código-fonte)" if exposto else detalhe_status(status, corpo), "seguranca")
        except Bloqueado as b:
            registrar("sourcemap", "bloqueado", f"anti-bot respondeu {b}: não verificado", "seguranca")
        except Exception as e:
            registrar("sourcemap", "info", f"erro: {e}", "seguranca")


def checar_seo(base, so_erro=False):
    host = urllib.parse.urlparse(base).hostname
    if not so_erro:
        checar_robots_sitemap(base, host)
    try:
        status, _, corpo, _ = buscar_texto(base + "/esta-pagina-nao-existe-auditoria", seguir=True)
        registrar("pagina-404", "ok" if status == 404 else "falha",
                  "rota inexistente responde 200 com a home (fallback de SPA: o servidor não sabe quais rotas existem)"
                  if status == 200 and e_fallback(corpo) else f"rota inexistente responde {status}", "site")
        if re.search(r"(stack|traceback|exception|at [\w.]+\(|node_modules|\.cs:line)", corpo, re.I):
            registrar("404-vaza", "aviso", "página de erro parece mostrar detalhe técnico", "seguranca")
    except Bloqueado as b:
        registrar("pagina-404", "bloqueado", f"anti-bot respondeu {b}: não verificado", "site")
    except Exception as e:
        registrar("pagina-404", "info", f"erro: {e}", "site")
    try:
        status, _, _, _ = buscar_texto(base + "/.well-known/security.txt")
        registrar("security.txt", "ok" if status == 200 else "info", f"{status} (opcional)", "seguranca")
    except Exception:
        pass


def checar_robots_sitemap(base, host):
    try:
        status, _, robots, _ = buscar_texto(base + "/robots.txt")
        if status != 200:
            registrar("robots.txt", "falha", f"{status}", "site")
        else:
            bloqueia_tudo = re.search(r"^disallow:\s*/\s*$", robots, re.I | re.M)
            registrar("robots.txt", "falha" if bloqueia_tudo else "ok",
                      "Disallow: / bloqueia o site inteiro" if bloqueia_tudo else "ok", "site")
            sm = re.findall(r"^sitemap:\s*(\S+)", robots, re.I | re.M)
            registrar("robots-sitemap", "ok" if sm else "aviso", sm[0] if sm else "robots sem linha Sitemap", "site")
            internas = re.findall(r"^disallow:\s*(\S*(admin|debug|internal|interno|painel|backup|staging)\S*)", robots, re.I | re.M)
            if internas:
                registrar("robots-revela", "aviso", f"robots lista rota interna: {[i[0] for i in internas]}", "seguranca")
    except Bloqueado as b:
        registrar("robots.txt", "bloqueado", f"anti-bot respondeu {b}: não verificado", "site")
    except Exception as e:
        registrar("robots.txt", "info", f"erro: {e}", "site")
    try:
        status, _, sm, _ = buscar_texto(base + "/sitemap.xml")
        urls = re.findall(r"<loc>([^<]+)</loc>", sm)
        de_fora = [u for u in urls if urllib.parse.urlparse(u).hostname != host]
        if status == 200 and e_fallback(sm):
            registrar("sitemap.xml", "falha", "não existe: /sitemap.xml devolve a home (fallback de SPA)", "site")
        elif status != 200 or not urls:
            registrar("sitemap.xml", "falha", f"{status}, {len(urls)} URLs", "site")
        else:
            registrar("sitemap.xml", "aviso" if de_fora else "ok",
                      f"{len(urls)} URLs" + (f"; {len(de_fora)} de outro domínio: {de_fora[:3]}" if de_fora else ""), "site")
    except Bloqueado as b:
        registrar("sitemap.xml", "bloqueado", f"anti-bot respondeu {b}: não verificado", "site")
    except Exception as e:
        registrar("sitemap.xml", "info", f"erro: {e}", "site")


def checar_dns(base):
    host = urllib.parse.urlparse(base).hostname
    partes = host.split(".")
    if host.endswith((".vercel.app", ".netlify.app", ".github.io", ".pages.dev", ".onrender.com", ".fly.dev",
                      ".up.railway.app", ".herokuapp.com", ".azurewebsites.net", ".web.app", ".firebaseapp.com")):
        registrar("dns", "info", f"{host} é subdomínio da plataforma: SPF/DMARC/CAA não se aplicam até ter domínio próprio", "site")
        return
    dominio = ".".join(partes[-2:]) if not host.endswith(".com.br") else ".".join(partes[-3:])
    try:
        txt = doh(dominio, "TXT")
        spf = [t for t in txt if t.startswith("v=spf1")]
        registrar("spf", "ok" if spf else "aviso", spf[0] if spf else "sem SPF (e-mail do domínio pode ser falsificado)", "site")
        dmarc = [t for t in doh(f"_dmarc.{dominio}", "TXT") if t.startswith("v=DMARC1")]
        if not dmarc:
            registrar("dmarc", "aviso", "sem DMARC", "site")
        else:
            politica = re.search(r"p=(\w+)", dmarc[0])
            registrar("dmarc", "ok" if politica and politica.group(1) in ("quarantine", "reject") else "aviso", dmarc[0], "site")
        caa = doh(dominio, "CAA")
        registrar("caa", "ok" if caa else "info", str(caa) if caa else "sem CAA (opcional, limita quem emite certificado)", "seguranca")
        mx = doh(dominio, "MX")
        registrar("mx", "info", str(mx) if mx else "sem MX: domínio não recebe e-mail (então SPF -all e DMARC reject ajudam contra falsificação)", "site")
    except Bloqueado as b:
        registrar("dns", "bloqueado", f"anti-bot respondeu {b}: não verificado", "site")
    except Exception as e:
        registrar("dns", "info", f"erro no DNS: {e}", "site")


def comparar(anterior_path):
    with open(anterior_path, encoding="utf-8") as f:
        antes = {r["id"]: r["status"] for r in json.load(f)["resultados"]}
    agora = {r["id"]: r["status"] for r in resultados}
    mudou = []
    for id_ in sorted(set(antes) | set(agora)):
        if antes.get(id_) != agora.get(id_):
            mudou.append({"id": id_, "antes": antes.get(id_, "-"), "agora": agora.get(id_, "-")})
    return mudou


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--saida")
    ap.add_argument("--comparar")
    ap.add_argument("--rota", default="/", help="rota real de onde ler os headers (API sem página na raiz)")
    args = ap.parse_args()
    base = args.url.rstrip("/")
    partes = urllib.parse.urlparse(base)
    if partes.scheme not in ("http", "https") or not partes.hostname:
        sys.exit("passe a URL completa, com http:// (só alvo local) ou https://")
    ALVO["local"] = e_host_local(partes.hostname)
    if partes.scheme == "http" and not ALVO["local"]:
        sys.exit("alvo remoto exige https://: http:// só vale pra localhost, 127.0.0.0/8, ::1 e nomes .localhost, .local ou .test")

    checar_https(base)
    try:
        status, headers, html, final = buscar_texto(base + "/")
    except Bloqueado as b:
        sys.exit(f"o anti-bot do site bloqueou até a home ({b}); espere uns minutos ou rode de outra rede")
    HOME["corpo"] = html if status == 200 else ""
    api = "json" in (headers.get("content-type") or "") or status == 404 and args.rota != "/"
    registrar("home", "ok" if status == 200 else "info" if api else "falha",
              f"{status} em {final}" + (" (API sem página na raiz)" if status != 200 and api else ""), "site")
    _, headers_comp, _, _ = buscar(base + "/" + args.rota.lstrip("/"))
    checar_headers(headers_comp)
    if status != 200 and api:
        registrar("pagina", "info", "API sem página na raiz: head, SEO, robots e sitemap não se aplicam", "site")
        p = Cabeca()
    else:
        p = checar_cabeca(base, html)
    checar_seo(base, so_erro=status != 200 and api)
    if ALVO["local"]:
        registrar("dns", "info", "alvo local: SPF/DMARC/CAA não se aplicam", "site")
    else:
        checar_dns(base)
    checar_sourcemaps(base, p)
    checar_arquivos(base)

    saida = {
        "url": base,
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "resumo": {s: sum(1 for r in resultados if r["status"] == s) for s in ("falha", "aviso", "bloqueado", "ok", "info")},
        "resultados": resultados,
    }
    if args.comparar:
        saida["mudancas"] = comparar(args.comparar)
    texto_json = json.dumps(saida, ensure_ascii=False, indent=2)
    if args.saida:
        with open(args.saida, "w", encoding="utf-8") as f:
            f.write(texto_json)
    print(texto_json)


if __name__ == "__main__":
    main()
