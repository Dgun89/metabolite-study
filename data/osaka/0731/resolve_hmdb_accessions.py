"""
Resolve HMDB accessions -> InChIKey (+ KEGG/ChEBI/name/source) from the local
HMDB XML. One-off helper for the osaka(1) dataset: entry key is an HMDB
accession, not an InChIKey, so build_hmdb_index.py's InChIKey filter cannot be
used as-is.

Matches on primary accession AND secondary_accessions (retired ids remap).
Zero API calls. Writes interim JSON keyed by accession.
"""
import sys, json
from pathlib import Path
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from pipeline import config as C

NS = "{http://www.hmdb.ca}"
HERE = Path(__file__).resolve().parent
SEED = HERE / "osaka1_seed.csv"
OUT = HERE / "hmdb_resolved.json"


def tag(e):
    return e.tag.replace(NS, "")


def main(targets):
    targets = set(targets)
    found = {}
    n_seen = 0
    ctx = etree.iterparse(str(C.HMDB_XML), events=("end",), tag=f"{NS}metabolite")
    for _, elem in ctx:
        n_seen += 1
        acc = None
        secondary = []
        for child in elem:
            t = tag(child)
            if t == "accession" and acc is None:
                acc = child.text
            elif t == "secondary_accessions":
                secondary = [s.text for s in child if s.text]
        hits = {a for a in ([acc] + secondary) if a in targets}
        if hits:
            rec = {"accession": acc, "secondary_accessions": secondary,
                   "inchikey": None, "kegg_id": None, "chebi_id": None,
                   "name": None, "formula": None, "smiles": None,
                   "cas": None, "hmdb_source": []}
            for child in elem:
                t = tag(child)
                if t == "inchikey":   rec["inchikey"] = child.text
                elif t == "kegg_id":  rec["kegg_id"] = child.text
                elif t == "chebi_id": rec["chebi_id"] = child.text
                elif t == "name":     rec["name"] = child.text
                elif t == "chemical_formula": rec["formula"] = child.text
                elif t == "smiles":   rec["smiles"] = child.text
                elif t == "cas_registry_number": rec["cas"] = child.text
                elif t == "ontology":
                    srcs = []
                    for term_el in child.iter(f"{NS}term"):
                        if term_el.text == "Source":
                            parent = term_el.getparent()
                            if parent is not None:
                                for sub in parent.iter(f"{NS}term"):
                                    if sub.text and sub.text != "Source":
                                        srcs.append(sub.text)
                    rec["hmdb_source"] = sorted(set(srcs))
            rec["source"] = "HMDB"
            rec["source_version"] = C.hmdb_version()
            rec["retrieved_at"] = C.now_iso()
            for q in hits:
                rec2 = dict(rec)
                rec2["matched_via"] = "primary" if q == acc else "secondary"
                found[q] = rec2
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]
        if n_seen % 50000 == 0:
            print(f"  scanned {n_seen}, matched {len(found)}/{len(targets)}", flush=True)
    OUT.write_text(json.dumps(found, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"done. scanned {n_seen} | matched {len(found)}/{len(targets)} -> {OUT.name}", flush=True)
    return found


if __name__ == "__main__":
    import pandas as pd
    seed = pd.read_csv(SEED)
    accs = sorted(seed["hmdb_id"].dropna().unique())
    print(f"targets: {len(accs)} unique HMDB accessions", flush=True)
    main(accs)
