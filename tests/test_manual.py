import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import construir_manual as cm  # noqa: E402


def test_manual_aprende_conta_correta_apesar_do_ruido():
    cm.gerar_historico()
    m = cm.construir()
    for f in m["fornecedores"]:
        assert f["conta_sugerida"] == cm.FORNECEDORES[f["fornecedor"]][0], f["fornecedor"]
        assert 0.8 < f["consistencia"] <= 1


def test_toda_conta_sugerida_existe_no_plano():
    m = json.loads((RAIZ / "data/manual.json").read_text(encoding="utf-8"))
    plano = {c["conta"] for c in m["contas"]}
    assert all(f["conta_sugerida"] in plano for f in m["fornecedores"])


def test_identifica_fornecedor_em_historicos_variados():
    assert cm.identificar_fornecedor("nf 123 limpa bem serviços ltda limpeza pa03") == "LIMPA BEM SERVIÇOS LTDA"
    assert cm.identificar_fornecedor("AJUSTE MANUAL") is None
