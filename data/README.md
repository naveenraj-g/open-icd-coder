# ICD-10-CM source files

Put the official ICD-10-CM release files here. They are **not** included in the repository — download them from CDC/NCHS (free, no account):

**<https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/ICD10CM/2027/>** (FY2027, effective 2026-10-01)

| File | Needed? | Used for |
|---|---|---|
| `icd10cm-code-descriptions-2027.zip` | **Required** | Every code, billable flag, short + long descriptions, hierarchy (`icd10cm-order-2027.txt` inside) |
| `icd10cm-table-and-index-2027.zip` | **Required** | Inclusion terms + instructional notes (`icd10cm-tabular_-2027.xml`) and the Alphabetic Index (`icd10cm-index-2027.xml`) |
| `ICD-10-CM-October-1-2026-FY27-Guidelines.pdf` | Optional | Official coding guidelines (reference) |
| `icd10cm-addenda-2027.zip` | Optional | Changes since the previous release |

Leave the zips as they are — the loaders read them in place:

```
data/
├── icd10cm-code-descriptions-2027.zip
└── icd10cm-table-and-index-2027.zip
```

For a later release (e.g. FY2028), download from the matching year folder and pass the paths to `just terminology-icd10cm FILE=… TABULAR=…` and `just terminology-index FILE=…`. Releases are stored side by side, keyed by version.
