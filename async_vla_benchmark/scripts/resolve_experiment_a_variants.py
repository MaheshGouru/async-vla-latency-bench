#!/usr/bin/env python3
"""Deterministically freeze three new Experiment A object-layout variants."""
import argparse, csv, json, os, sys
from pathlib import Path

from async_vla_benchmark.benchmark.experiment_a import (
    BASE_TASK_ID, BASE_TASK_NAME, EXCLUDED_CLASSIFICATION_ID, EXCLUDED_VARIANT_NAME,
    SUITE, select_variant_entries,
)
from async_vla_benchmark.benchmark.ood_tasks import find_task_classification_path


def main():
    os.environ["MPLBACKEND"]="Agg"; native=Path.home()/"stage1-native"
    if native.exists() and os.environ.get("EXPERIMENT_A_NATIVE_REEXEC") != str(native):
        env=os.environ.copy(); env.update({"EXPERIMENT_A_NATIVE_REEXEC":str(native),"MAGICK_HOME":str(native),"PATH":str(native/"bin")+os.pathsep+env.get("PATH",""),"LD_LIBRARY_PATH":str(native/"lib")+os.pathsep+env.get("LD_LIBRARY_PATH","")})
        os.execve(sys.executable,[sys.executable,"-m","async_vla_benchmark.scripts.resolve_experiment_a_variants",*sys.argv[1:]],env)
    p=argparse.ArgumentParser(); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    if a.output.exists(): raise FileExistsError(f"refusing to overwrite frozen variants: {a.output}")
    classification_path=find_task_classification_path(); root=classification_path.parent.parent
    config=Path.home()/".libero/config.yaml"; config.parent.mkdir(parents=True,exist_ok=True)
    config.write_text(f"assets: {root/'assets'}\nbddl_files: {root/'bddl_files'}\ndatasets: {root/'../datasets'}\ninit_states: {root/'init_files'}\n")
    from wand.api import library as _wand_library  # noqa: F401
    from lerobot.envs.libero import _get_suite
    entries=json.loads(classification_path.read_text())[SUITE]
    rows=select_variant_entries(entries,_get_suite(SUITE).get_task_names()); a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    import hashlib; digest=hashlib.sha256(a.output.read_bytes()).hexdigest()
    print(*[f"{r['classification_id']},{r['api_task_index']},L{r['difficulty_level']},{r['variant_name']}" for r in rows],sep="\n")
    print("PASS frozen_variants=3 excluded_prior=1941 sha256",digest); return 0
if __name__=="__main__": raise SystemExit(main())
