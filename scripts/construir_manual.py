"""Constrói o Manual de Contabilização a partir do histórico do Livro Razão (dados FICTÍCIOS).

1. gera (ou lê) data/razao_historico.csv
2. aprende, por fornecedor, a conta mais usada e o grau de consistência
3. combina com o plano de contas comentado (data/plano_contas.json)
4. grava data/manual.json, consumido pelo index.html

Uso: python scripts/construir_manual.py [--regerar]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "data"

# fornecedor -> (conta correta, complemento do histórico)
FORNECEDORES = {
    "ENERGIA CENTRO-OESTE S.A.": ("8.1.7.03.00.01", "ENERGIA ELÉTRICA"),
    "SANEAMENTO ESTADUAL S.A.": ("8.1.7.03.00.01", "ÁGUA E ESGOTO"),
    "LIMPA BEM SERVIÇOS LTDA": ("8.1.7.36.00.01", "LIMPEZA E CONSERVAÇÃO"),
    "PROTEGE VIGILÂNCIA LTDA": ("8.1.7.33.00.01", "VIGILÂNCIA"),
    "TRANSVALOR LTDA": ("8.1.7.33.00.02", "TRANSPORTE DE VALORES"),
    "PAPELARIA TOTAL LTDA": ("8.1.7.48.00.01", "MATERIAL DE EXPEDIENTE"),
    "MANUTENÇÃO ÔMEGA LTDA": ("8.1.7.18.00.02", "MANUTENÇÃO PREDIAL"),
    "SILVA & SOUZA ADVOGADOS": ("8.1.7.63.00.02", "HONORÁRIOS ADVOCATÍCIOS"),
    "CONSULTORIA ÁGIL ME": ("8.1.7.63.00.04", "CONSULTORIA"),
    "FIBRA NET TELECOM LTDA": ("8.1.7.03.00.05", "LINK DE DADOS"),
    "IMOBILIÁRIA CENTRAL LTDA": ("8.1.7.12.00.01", "ALUGUEL"),
    "CORREIOS EXPRESSO S.A.": ("8.1.7.03.00.07", "POSTAGENS"),
}


def gerar_historico(seed: int = 21) -> None:
    rng = random.Random(seed)
    contas = sorted({c for c, _ in FORNECEDORES.values()})
    linhas = []
    for i in range(1800):
        forn = rng.choice(list(FORNECEDORES))
        conta, comp = FORNECEDORES[forn]
        if rng.random() < 0.06:                              # classificação inconsistente (ruído real)
            conta = rng.choice(contas)
        d = date(2025, 1, 2) + timedelta(days=rng.randint(0, 660))
        pa = f"{rng.randint(1, 15):02d}"
        nf = rng.randint(1000, 99999)
        estilo = rng.random()
        if estilo < 0.5:
            hist = f"PAGTO NF {nf} - {forn} - {comp} PA {pa} - REF {d:%m/%Y}"
        elif estilo < 0.8:
            hist = f"NF {nf} {forn} {comp.lower()} pa{pa} {d:%m/%Y}"
        else:
            hist = f"{forn} - NF{nf} - {comp}"
        linhas.append([i + 1, d, conta, hist, round(rng.lognormvariate(7, 0.8), 2)])
    with (DADOS / "razao_historico.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["lancamento_id", "data", "conta", "historico", "valor"])
        w.writerows(linhas)


def identificar_fornecedor(hist: str) -> str | None:
    h = hist.upper()
    return next((f for f in FORNECEDORES if f in h), None)


def construir() -> dict:
    plano = json.loads((DADOS / "plano_contas.json").read_text(encoding="utf-8"))
    por_forn: dict[str, Counter] = defaultdict(Counter)
    padrao_historico = re.compile(r"^PAGTO NF \d+ - .+ - .+ PA \d{2} - REF \d{2}/\d{4}$")
    fora_do_padrao = 0
    with (DADOS / "razao_historico.csv").open(encoding="utf-8") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))
    for l in linhas:
        forn = identificar_fornecedor(l["historico"])
        if forn:
            por_forn[forn][l["conta"]] += 1
        if not padrao_historico.match(l["historico"]):
            fora_do_padrao += 1

    fornecedores = []
    for forn, cont in sorted(por_forn.items()):
        total = sum(cont.values())
        conta, n = cont.most_common(1)[0]
        fornecedores.append({
            "fornecedor": forn, "conta_sugerida": conta, "lancamentos": total,
            "consistencia": round(n / total, 3),
            "outras_contas": [{"conta": c, "qtd": q} for c, q in cont.most_common()[1:]],
            "modelo_historico": f"PAGTO NF {{NF}} - {forn} - {FORNECEDORES[forn][1]} PA {{PA}} - REF {{MM/AAAA}}",
        })
    manual = {
        "titulo": "Manual de Contabilização - Contas a Pagar",
        "fonte": f"{len(linhas)} lançamentos fictícios do Livro Razão (2025-2026)",
        "padrao_historico": "PAGTO NF {NF} - {FORNECEDOR} - {DESCRIÇÃO} PA {PA} - REF {MM/AAAA}",
        "pct_historicos_fora_do_padrao": round(fora_do_padrao / len(linhas), 3),
        "contas": plano["contas"], "regras_gerais": plano["regras_gerais"], "fornecedores": fornecedores,
    }
    (DADOS / "manual.json").write_text(json.dumps(manual, ensure_ascii=False, indent=1), encoding="utf-8")
    return manual


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--regerar", action="store_true")
    a = ap.parse_args()
    if a.regerar or not (DADOS / "razao_historico.csv").exists():
        gerar_historico()
    m = construir()
    print(f"{len(m['fornecedores'])} fornecedores, {len(m['contas'])} contas | "
          f"históricos fora do padrão: {m['pct_historicos_fora_do_padrao']:.0%}")
