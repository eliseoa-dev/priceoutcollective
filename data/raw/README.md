# data/raw/ — source files, unmodified

Do not edit these. `../build_dataset.py` reads from here.

| file | what it is |
|---|---|
| `san_diego_ca_hlb_hackathon_2024.csv.gz` | The dataset. 1,171,123 synthetic households, 25 columns, 2024 dollars. 16.7 MB gzipped, 175 MB decompressed. |
| `San_Diego_HLB_Hackathon_Data_Dictionary.docx` | The organizers' full dictionary. **Read this before doing analysis.** |
| `data_dictionary_2024.csv` | Column-by-column summary of the same. |

## Working with the big file

Read the gzip directly — pandas handles it, and there is no reason to unpack
175 MB onto disk:

```python
df = pd.read_csv("san_diego_ca_hlb_hackathon_2024.csv.gz", dtype={"geoid": str, "puma": str})
```

**Do not open it in Excel or Google Sheets.** Both cap out around a million
rows and will truncate it silently, which is a good way to present a number
that is quietly wrong.

## Where it came from

A Google Drive folder shared by the organizers (`Affordability`, owned by
adir@datasciencealliance.org).

**A permissions gotcha worth knowing:** the folder was shared, but the files
inside it were not shared individually. Tools that connect to Drive
programmatically therefore see the folder as empty — not as an error, just
zero results. If you are scripting against Drive and getting nothing back,
that is why, and no amount of retrying fixes it. Download through the browser,
or ask the organizers to share the files themselves rather than the folder.

The files are committed here so nobody on the team has to fight that twice.
