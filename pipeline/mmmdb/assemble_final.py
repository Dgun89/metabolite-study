"""Assemble mouse_final_curated.xlsx — DarkMet step30 layout (3 sheets:
Sheet1 / Legend / Summary), with MMMDB bridge + MSI grade columns appended.
Original 18 columns and their order are preserved; curation columns follow."""
import pandas as pd
from datetime import date

m=pd.read_parquet("mouse_msi.parquet")

ORIG=["Database ID","compound_name","InChIKey","SMILES","PubChem","KEGG","HMDB",
      "ChEBI","classification","hmdb_origin","coconut_organisms","chebi_roles",
      "coconut_match_key","classification_basis","kegg_enzymes","hmdb_enzymes",
      "reactome_catalysts","brenda_enzymes"]
CUR=["classification_original","classification_basis_original","mmmdb_reclassified",
     "mmmdb_match","mmmdb_name","mmmdb_n_tissues","mmmdb_tissues","mmmdb_match_basis",
     "msi_level","msi_evidence"]
sheet1=m[[c for c in ORIG if c in m.columns]+CUR].copy()
# tidy: blank instead of NaN in curation string cols
for c in ["mmmdb_tissues","mmmdb_match_basis","mmmdb_name"]:
    sheet1[c]=sheet1[c].fillna("")
sheet1["mmmdb_n_tissues"]=sheet1["mmmdb_n_tissues"].fillna(0).astype(int)

# ---- Legend (extend original) ----
legend_rows=[
 ["Group","Color","Column","Description","Source"],
 ["Basic Identifiers","","Database ID","COCONUT compound ID","COCONUT"],
 ["Basic Identifiers","","compound_name","Compound name","COCONUT"],
 ["Basic Identifiers","","InChIKey","Chemical structure key (27-char)","PubChem"],
 ["Basic Identifiers","","SMILES","Chemical structure in text format","PubChem"],
 ["External DB IDs","","PubChem","PubChem Compound ID (CID)","PubChem"],
 ["External DB IDs","","KEGG","KEGG Compound ID","KEGG"],
 ["External DB IDs","","HMDB","Human Metabolome Database ID","HMDB"],
 ["External DB IDs","","ChEBI","Chemical Entities of Biological Interest ID","ChEBI"],
 ["Classification","","classification","Final (MMMDB-aware) classification: endogenous / exogenous / unverified","ChEBI+HMDB+COCONUT+MMMDB"],
 ["Classification Sources","","hmdb_origin","HMDB origin field (Endogenous / Food / Drug etc.)","HMDB"],
 ["Classification Sources","","coconut_organisms","Organisms associated with compound in COCONUT","COCONUT"],
 ["Classification Sources","","chebi_roles","Role classification from ChEBI (semicolon-separated)","ChEBI"],
 ["Classification Metadata","","coconut_match_key","COCONUT match method: inchikey / inchikey_skeleton / cnp_id","COCONUT"],
 ["Classification Metadata","","classification_basis","Reason behind (MMMDB-aware) classification","ChEBI+COCONUT+MMMDB"],
 ["Enzyme Information","","kegg_enzymes","EC numbers from KEGG (semicolon-separated)","KEGG"],
 ["Enzyme Information","","hmdb_enzymes","Enzyme gene names from HMDB (semicolon-separated)","HMDB"],
 ["Enzyme Information","","reactome_catalysts","Catalyst activity names from Reactome","Reactome"],
 ["Enzyme Information","","brenda_enzymes","EC numbers from BRENDA (semicolon-separated)","BRENDA"],
 ["MMMDB Bridge","","classification_original","Classification BEFORE MMMDB reclassification","(pipeline)"],
 ["MMMDB Bridge","","classification_basis_original","Classification basis before MMMDB","(pipeline)"],
 ["MMMDB Bridge","","mmmdb_reclassified","Whether MMMDB evidence changed the label (Yes/No)","MMMDB"],
 ["MMMDB Bridge","","mmmdb_match","Compound found in MMMDB mouse-tissue data (Yes/No)","MMMDB"],
 ["MMMDB Bridge","","mmmdb_name","Matched MMMDB compound name","MMMDB"],
 ["MMMDB Bridge","","mmmdb_n_tissues","Number of mouse tissues (of 11) detecting the compound","MMMDB"],
 ["MMMDB Bridge","","mmmdb_tissues","Comma-separated list of detecting tissues","MMMDB"],
 ["MMMDB Bridge","","mmmdb_match_basis","Match key: InChIKey (stereo-exact) / InChIKey14 (skeleton) / KEGG / ChEBI","MMMDB"],
 ["MSI Confidence","","msi_level","MSI-style annotation confidence: L2 probable / L3 tentative / L4 formula / L5 unknown (L1 not assignable for non-targeted data)","(pipeline)"],
 ["MSI Confidence","","msi_evidence","Supporting evidence keys for the MSI level","(pipeline)"],
 ["","","","",""],
 ["Note","","","MMMDB = Mouse Multiple Tissue Metabolome Database (Sugimoto et al., NAR 2012; CE-TOFMS, 11 tissues, 219 metabolites). Used as a mouse-specific cross-validation layer to correct human-centric (HMDB/ChEBI) misclassification.",""],
]
legend=pd.DataFrame(legend_rows)

m.to_parquet("mouse_msi.parquet")  # ensure latest
print("Sheet1 cols:", len(sheet1.columns), "rows:", len(sheet1))
sheet1.to_parquet("_sheet1.parquet")
legend.to_pickle("_legend.pkl")
print("prepared sheet1 + legend")
