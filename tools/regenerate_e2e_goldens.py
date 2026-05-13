# tools/regenerate_e2e_goldens.py

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tests.e2e.helpers import (  # noqa: E402
    ensure_golden_dir,
    fixture_ids,
    scenario_outputs,
    write_text_atomic,
)


def main() -> None:
    for fixture_id in fixture_ids():
        outputs = scenario_outputs(fixture_id=fixture_id)
        golden = ensure_golden_dir(fixture_id)

        for filename, content in outputs.items():
            write_text_atomic(golden / filename, content)

        print(f"Regenerated: {fixture_id}")

    print("All golden files regenerated.")


if __name__ == "__main__":
    main()