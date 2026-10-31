#!/usr/bin/env python3
import argparse, json
from pathlib import Path
from async_vla_benchmark.benchmark.logging import read_csv


def main():
    p=argparse.ArgumentParser(); p.add_argument("--manifest",type=Path,required=True); p.add_argument("--output-dir",type=Path,required=True); a=p.parse_args(); rows=read_csv(a.manifest); results=read_csv(a.output_dir/"stage4_episode_results.csv")
    ids={r["run_id"] for r in rows}; matched=[r for r in results if r["run_id"] in ids]
    errors=[]
    if len(rows)!=4 or len(matched)!=4: errors.append(f"expected four smoke episodes, got manifest={len(rows)} results={len(matched)}")
    for row in matched:
        if row["seed"]!="999" or row["analysis_status"]!="nonanalysis_smoke": errors.append(f"{row['run_id']}: smoke provenance mismatch")
        if not row["status"].startswith("ok"): errors.append(f"{row['run_id']}: invalid smoke result")
        for folder,ext in (("episodes","json"),("requests","parquet"),("actions","parquet")):
            if not (a.output_dir/folder/f"{row['run_id']}.{ext}").exists(): errors.append(f"{row['run_id']}: missing {folder}")
    report={"status":"fail" if errors else "pass","smoke_rows":len(matched),"analysis_seeds_used":sorted({r["seed"] for r in matched if r["seed"]!="999"}),"errors":errors}
    (a.output_dir/"stage4_smoke_validation.json").write_text(json.dumps(report,indent=2)+"\n")
    if errors: print(*(f"ERROR: {e}" for e in errors),sep="\n"); return 1
    print("PASS: four seed-999 OpenVLA-OFT smoke episodes; no analysis seeds used"); return 0


if __name__=="__main__": raise SystemExit(main())
