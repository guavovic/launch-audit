# Placar

Como as skills são medidas e onde ficam os resultados de cada versão.

## Alvos

Aplicações vulneráveis de propósito, rodando só na máquina local (Docker), com a lista oficial das falhas que existem:

| Alvo | O que mede |
|---|---|
| [OWASP Juice Shop](https://owasp.org/www-project-juice-shop/) | Loja moderna em Node e Angular, falhas do OWASP Top 10 e de API |
| [DVWA](https://github.com/digininja/DVWA) | PHP clássico, injeção e upload |
| [OWASP crAPI](https://github.com/OWASP/crAPI) | API com falhas de autorização (BOLA, BFLA, mass assignment) |

Pra frente jurídica e de qualidade, os alvos são sites reais do autor, publicados só depois de corrigidos (ver [casos](casos/)).

## Como pontua

Pra cada alvo, a lista oficial vira o gabarito. Cada rodada registra:

- **Acertos:** falhas do gabarito que a skill achou, com evidência.
- **Falsos positivos:** achados que não são falha de verdade.
- **Fora do alcance:** falhas que só aparecem explorando (a skill confirma controles, não ataca), contadas à parte.
- **Custo:** tokens e tempo da rodada.

Mesmo alvo, mesma versão do alvo, mesmo modelo, pra comparar versões da skill entre si e com ferramentas como OWASP ZAP (baseline), semgrep e Lighthouse.

## Resultados

Primeira rodada publicada: Juice Shop em 26/10/2026. Cada rodada entra aqui com a versão da skill, a data e o link pro detalhe. As rodadas em sites reais ficam nos [estudos de caso](casos/), a começar pelo [guavovic-website](casos/guavovic-website.md).

| Versão | Data | Alvo | Acertos | Falsos positivos | Fora do alcance |
|---|---|---|---|---|---|
| v0.2.0 | 26/10/2026 | [Juice Shop 20.3.0](placar/juice-shop-2026-10-26.md) | 57 de 116 | 2 | 58 (1 não achado) |

Comparação com ferramentas no mesmo alvo e na mesma data: [OWASP ZAP baseline, semgrep e Lighthouse](placar/comparacao-ferramentas-2026-10-26.md). Em segundos e sem tokens, o semgrep acerta 16 dos 116 desafios (injeção, redirecionamento, listagem de diretório), o ZAP baseline 1 e o Lighthouse 0; todos eles ficam dentro dos 57 da skill, e o ganho de juntar está em cabeçalhos, CORS e qualidade da página.
