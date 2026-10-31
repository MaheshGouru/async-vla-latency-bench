#!/usr/bin/env python3
"""Run Object-Layout Generalization through the audited Held-Out OOD–Delay Horizon Confirmation execution engine."""
import sys
from async_vla_benchmark.scripts.run_stage3 import main
if __name__=="__main__":
 if "--stage-label" not in sys.argv: sys.argv.extend(["--stage-label","experiment_a"])
 raise SystemExit(main())
