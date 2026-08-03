# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

An InChIKey-normalized compound database and endogenous/exogenous classification pipeline for metabolite
datasets (human serum, mouse serum, mouse feces, and an incoming `osaka(1)` panel). Every compound is keyed
on its full 27-character InChIKey (structure identity), never on a source-specific id like a COCONUT CNP id.
The pipeline is rebuilt from original source files rather than reusing the hand-curated `legacy/` database, so
an independent reproduction doubles as a reliability audit of that earlier DB. Full schema, pipeline-stage
docs, and progress log live in `README.md` (English + Korean) — read it before making non-trivial changes,
it is the source of truth for the data model.

## Commands

No test framework or linter is configured (`pipeline/mmmdb/test_sample.py` is a one-off script, not a pytest
test — run it directly with `python`, not `pytest`).

Set `PYTHONPATH=.` before running anything under `pipeline/` (scripts do `from pipeline.config import ...`).

```bash
export PYTHONPATH=.
pip install -r requirements.txt      # requirements.txt is UTF-16LE encoded — do not rewrite it as UTF-8
```

### Reproducing the deterministic stages (no network needed)

The collection stages (COCONUT join, UniChem/ChEBI/PubChem, HMDB, BRENDA) need large local reference files
and network access; their outputs are cached under `.work/interim/` (gitignored, but the classified parquet
checkpoints and identifier caches are force-tracked so a clone can reproduce without re-collecting). From
those caches, the deterministic downstream can be re-run with no network:

```bash
export PYTHONPATH=.
python pipeline/04_classify_run.py   # optional: re-derive classification from step2 + caches
python pipeline/normalize.py         # rebuild data/normalized/*.parquet (6 tables)
python pipeline/export_view.py       # rebuild data/export/*.xlsx
python verify_reproduction.py        # compare against REPRODUCE_reference_fingerprints.json
```

`verify_reproduction.py` is the correctness check for this repo: it compares row counts and a sort-invariant,
platform-independent SHA-256 of each normalized table against the committed baseline
(`REPRODUCE_reference_fingerprints.json`). Volatile provenance timestamp columns (`created_at`,
`classified_at`, `retrieved_at`) are excluded from the hash by design — don't "fix" a mismatch by touching
those columns. A genuine mismatch means the pipeline output changed; regenerate the baseline only when that
change is intentional.

### Running a single pipeline stage

Every stage script is species-agnostic and driven by `SPECIES=human_serum|mouse_serum|mouse_feces|osaka(1)`
(see `pipeline/config.get_paths(species)`); there is no CLI flag — scripts read `SPECIES` from the
environment or a hardcoded loop, check the bottom of the file for the actual invocation pattern before
running one in isolation.

## Architecture

### Long-format normalized schema (`data/normalized/*.parquet`, gitignored — rebuilt by `normalize.py`)

Primary key throughout is `inchikey` (full 27-char); `inchikey14` (14-char skeleton) is a secondary join axis
for stereoisomer-collapsed matching. Multi-valued facts are one row per fact, each carrying provenance
(`source`, `source_version`, `retrieved_at`):

| Table | Grain |
|---|---|
| `compounds` | one per unique InChIKey (structure, formula, `db_support_level`, MMMDB flags) |
| `compound_external_ids` | one per (compound, DB, id) — COCONUT/PubChem/ChEBI/HMDB/DrugBank/etc. |
| `compound_origins` | one per (compound, origin fact) — includes HMDB `origin_category`/`origin_level` roll-up |
| `compound_classification` | one per compound — `drug_food` flag, `classification` (per-DB verdicts), conflict flags |
| `compound_enzymes` | one per (compound, EC) |
| `compound_species` | one per (compound, dataset) |

### Pipeline stage order (`pipeline/`)

Numbered scripts are meant to run in order; each writes to `.work/interim/{slug}/`:

0. `00_make_seeds.py` — extract CNP/PEP ids + name from original xlsx → seed CSV.
0b. `00b_resolve_pep.py` — resolve peptide (`PEP…`) entries to structures.
1. `01_coconut_join.py` — join seed CNP ids against the local COCONUT CSV (streamed, 738k rows).
1b. `01b_inchikey_join.py` — sibling of step 1 for datasets that already enter with an InChIKey resolved
    (no CNP id to walk through, e.g. `osaka(1)` enters via HMDB accession). Same output schema as step 1.
2. `collect_identifiers.py` — UniChem/ChEBI/PubChem cross-collection, keyed on unique InChIKeys.
3. `build_hmdb_index.py` — streams the 6.1 GB HMDB XML with `iterparse` (do not load it into memory whole).
4. `04_classify_run.py` + `classify.py` — endogenous/exogenous classification.
5. `collect_enzymes.py` / `collect_brenda.py` — KEGG/Reactome EC mapping; BRENDA SOAP (rate-limited to
   ≤1 req/sec, auth via `sha256(password)`, credentials in `.env` as `BRENDA_EMAIL`/`BRENDA_PASSWORD`).
6. `normalize.py` — assembles the 6 normalized tables; this is where classification, DB-support level, and
   MMMDB tissue-origin merges actually get (re)computed for the final output — not in step 4.
7. `export_view.py` — normalized tables → 4-sheet xlsx via `format_excel.py` (color-grouped headers,
   clickable DB-homepage links).
8. `compare_legacy.py` — reliability comparison against `legacy/etc/metabolites_step29.xlsx`.

`pipeline/mmmdb/` is a self-contained sub-pipeline that builds the MMMDB (mouse tissue) reference parquet
consumed by `04_classify_run.py`/`normalize.py`; it's run separately and less frequently than the main stages.

### Classification — read before touching `classify.py` or `normalize.py`

Classification is **v4** (2026-07-27): priority rules were deliberately dropped. `classify_row_v4()` lists
each source DB's verdict in parallel (e.g. `ChEBI:exogenous; HMDB:endogenous; COCONUT:endogenous`) instead of
collapsing to one label, because each DB measures a different axis (ChEBI = produced-by-organism, HMDB =
detected-in-organism, COCONUT = isolated-from-organism, MMMDB = actually tissue-measured). Do not reintroduce
a priority-based single verdict — that was the thing v4 explicitly moved away from at an advisor's request.
`classify_row()`/`_v2()`/`_v3()` are kept frozen in `classify.py` for before/after audit — never modify them,
add a new version instead if the rule changes again. `conflict_flag`/`conflicting_sources` mark endo↔exo
disagreement between sources; they're derived from the parallel verdicts, not a separate rule.

`db_support_level` is a structure-consensus proxy (how many independent DBs support a structure: L2 = ≥2
independent DB IDs, L3 = ≤1, L4 = formula-only, L5 = unknown) — it is **not** a spectral MSI grade. Don't
rename it back toward `msi_level`/`msi_evidence`; that was renamed specifically to stop overstating a
spectral-standard claim that non-target data can't support.

### Dataset labels vs. filesystem slugs

Dataset labels can contain filesystem-unsafe characters (e.g. `osaka(1)`, deliberately numbered so a second
delivery becomes `osaka(2)`). `pipeline.config.dataset_slug()` maps a label to a safe slug; **all** directory
names, interim/step filenames, and export filenames are built from the slug, never the raw label — apply the
same rule if you add a new dataset key. When filtering the `datasets` membership column in exports, use
literal string matching (`str.contains(..., regex=False)`), not regex — labels like `osaka(1)` contain regex
metacharacters.

### Paths and portability

`pipeline/config.py` defines `BASE` (repo root, overridable via `METABO_BASE`) and `WORK` (defaults to
`BASE/.work`, overridable via `METABO_WORK`) — never hardcode absolute paths in pipeline code. Export
filenames carry a `yymmdd` creation-date stamp (e.g. `combined_260731.xlsx`) because exports are regenerated
views, not frozen finals; pin the date with `METABO_STAMP=yymmdd` for cross-machine reproducibility on a
later day. All file text I/O must force UTF-8 explicitly (`Path.read_text(encoding="utf-8")` etc.) —
`Path.read_text()`'s OS-locale default breaks on Windows (cp1252) when reading the UTF-8 JSON caches.

### Data-handling principles (do not violate)

- `data/**` is entirely gitignored except `.py` files and one pinned exception
  (`data/mouse_serum/reference/mmmdb_reference.parquet`) — never add a new `!` exception for a data file
  under `data/`. Data moves between machines out-of-band (not through git); only code goes through git.
- Raw source files under each dataset's `raw/` are preserved as-is and never modified in place.
- `data/normalized/` (6 parquet) and `data/export/` (xlsx) are regenerable outputs, not sources of truth —
  regenerate them from the pipeline rather than hand-editing.
- `legacy/` is the original step1–29 pipeline and the `metabolites_step29.xlsx` baseline, kept only as the
  reliability-comparison target (see `legacy/README.md`) — it is not meant to be extended.
