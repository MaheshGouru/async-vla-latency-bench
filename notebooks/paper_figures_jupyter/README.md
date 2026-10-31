# Exact Exploratory OOD–Delay Screening task gallery

Run `01_render_stage1_task_gallery.ipynb` from top to bottom in the same Jupyter
environment used for Exploratory OOD–Delay Screening. It creates 24 individual agent-view PNGs, a 3×8
paper gallery in PNG/PDF form, provenance CSV/JSON files, and
`~/stage1_task_gallery.tar.gz`.

The columns are the literal Exploratory OOD–Delay Screening `perturbation_key` values. The rows are the
literal `task_key` values. Each caption is the exact language instruction
returned by the evaluated environment and passed to the policy.
