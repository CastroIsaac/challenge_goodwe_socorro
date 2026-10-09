"""Avaliação da IA em vários cenários simulados (sementes diferentes).

Roda o mesmo processo do seed (ingestão cronológica + retreino semanal) num
banco SQLite temporário e mede o detector de anomalias contra o gabarito das
anomalias injetadas, além do erro da previsão de demanda.

Uso:  python -m app.avaliacao
"""

import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/avaliacao.db"

from datetime import datetime  # noqa: E402

from app.ia.motor import motor  # noqa: E402
from app.seed import popular  # noqa: E402

SEMENTES = [1, 2, 3, 4, 5]
AGORA = datetime(2026, 10, 1, 8, 0)


def main():
    totais = {"verdadeiros_positivos": 0, "falsos_positivos": 0, "falsos_negativos": 0, "verdadeiros_negativos": 0}
    print("semente | sessões | VP | FP | FN | precisão | recall | MAE demanda (modelo / média)")
    for semente in SEMENTES:
        r = popular(agora=AGORA, semente=semente, verboso=False)
        a = r["avaliacao_anomalias"]
        m = motor.previsor.metricas
        for chave in totais:
            totais[chave] += a[chave]
        print(f"{semente:>7} | {r['sessoes']:>7} | {a['verdadeiros_positivos']:>2} | {a['falsos_positivos']:>2} | "
              f"{a['falsos_negativos']:>2} | {a['precisao']:>8} | {a['recall']:>6} | "
              f"{m['mae_modelo']} / {m['mae_baseline_media']}")

    vp, fp, fn, vn = totais.values()
    print(f"\nTotal: VP={vp} FP={fp} FN={fn} VN={vn}")
    print(f"Precisão = {vp / (vp + fp):.3f} | Recall = {vp / (vp + fn):.3f} | "
          f"Sessões enviadas para revisão = {(vp + fp) / (vp + fp + fn + vn):.1%}")


if __name__ == "__main__":
    main()
