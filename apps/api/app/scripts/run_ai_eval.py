from __future__ import annotations

"""Write AI eval artifact for CI / go-no-go evidence."""

from app.services.eval.runner import run_synthetic_eval, write_eval_artifact


def main() -> None:
    report = run_synthetic_eval()
    path = write_eval_artifact(report)
    print(f"wrote {path}")
    print(f"release_blocked={report.release_blocked} reasons={report.block_reasons}")
    raise SystemExit(1 if report.release_blocked else 0)


if __name__ == "__main__":
    main()
