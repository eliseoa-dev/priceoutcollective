# Sources

Primary sources only unless marked. Every external figure in the product traces to a row
here. Retrieved 2026-08-20 unless noted.

## The dataset

| what | source |
|---|---|
| San Diego County HLB microdata, 2024 | Building for Good organizers (Data Science Alliance @ UC San Diego). Committed at `data/raw/`, unmodified. |
| Data dictionary | `data/raw/San_Diego_HLB_Hackathon_Data_Dictionary.docx` — read this before any analysis; the READMEs are not a substitute. |

## Housing policy definitions `[EXTERNAL POLICY DEFINITION]`

| what | value | source |
|---|---|---|
| Cost burden | housing >30% of income | HUD — huduser.gov / hud.gov |
| Severe cost burden | housing >50% of income | HUD |
| Lineage of the 30% rule | Brooke Amendment (1969) → National Housing Act | HUD |
| Voucher tenant contribution | ~30% of **adjusted** income (not gross) | HUD HCV program rules |
| SDHC "Path to Success" | elderly/disabled 32% of adjusted income; work-able the greater of 40% or a minimum family contribution of $580 / $1,155 / $1,735 per month. HUD-approved 2026-03-10. | SDHC MTW plan amendment, sdhc.org |
| SDHC waiting list | closed 2026-02-01, 82,848 applicants, none selected since Aug 2022 | sdhc.org |
| HACSD waiting list | closed 2026-02-20 | sandiegocounty.gov |
| SDHC coverage | ~15,600 households of ~1,185,000 countywide (**1.3%**) | sdhc.org |
| AMI income limits | **use the published table, never arithmetic multiples** — San Diego's "50%" limit is 66.8% of AMI ($87,450 vs $130,900); its "80%" limit ($139,900) exceeds the 4-person AMI | HUD income limits + California HCD. Table at `.audit/scratch/ami_limits_sandiego.csv` |
| HCD guidance | "table data should be the only method used to determine program eligibility" | hcd.ca.gov |
| LIHTC "% of AMI" | a different scale — 60% AMI = $104,940 for a family of four, not 0.6 × published AMI | CTCAC |
| Housing + transportation 45% | **research benchmark, not law.** HUD's Location Affordability Index contains no threshold. | CNT (nonprofit) — attribute to CNT only |
| FMR / Small Area FMR | the dataset prices **FY2024 SAFMR**, verified against HUD's published table (0-BR 970/3,090; 4-BR 2,360/6,960). FY2024 San Diego 2-BR traces to a **November 2021** local rent survey trended forward. Re-priced to FY2026 the county median moves $2,590 → $2,816 (**+7.97%**). | huduser.gov |
| ADU law | renumbered to Gov. Code §§66310–66342 | leginfo.legislature.ca.gov |
| SB 35 | San Diego is a **50%** jurisdiction | HCD determination |

## Market and labour context `[EXTERNAL MARKET CONTEXT]`

| what | value | source |
|---|---|---|
| Occupational wages | 45 occupations, SD MSA 41740, employment + p10/p25/median/p75/p90 + mean | BLS OEWS **May 2025**, pulled via the BLS public API; cross-checked against the published news release ($38.01 hourly mean matches). `.audit/scratch/sd_occupation_wages.csv` |
| All-occupations median wage | $58,690 (nominal); $56,586 CPI-deflated to 2024 | BLS OEWS May 2025 + San Diego CPI-U (×0.96415) |
| City of San Diego minimum wage | $16.85/hr (2024) → $35,048 at 2,080 hrs | City of San Diego |
| Renter cost burden | 55.8% cost-burdened, 28.5% severely | ACS 2024 1-year, vintage-aligned with the dataset |
| Owner cost burden | 31.5% / 14.5% | ACS 2024 1-year |
| Households below ALICE threshold | 44.8% (2024) | United For ALICE |
| Cost-burdened households | 44.6% | HUD CHAS |
| Paid housing cost burden ≥30% | 43.6% — **uses no imputed rent** | ACS 2024 |
| Self-sufficiency budget, family of four | $8,155/mo | San Diego County HHSA |
| PUMA names, all 22 | official 2020 names, 22/22 exact code match | Census TIGER `tl_2023_06_puma20` (`NAMELSAD20`) |

## Notes on retrieval

- BLS blocks non-browser clients (403); OEWS and CPI were pulled through the BLS public
  API, not scraped.
- `api.census.gov` now requires a key; the `data.census.gov` table endpoint does not.
- HUD Exchange's Location Affordability Index pages currently 404, so the "30 + 15"
  provenance of the 45% figure is **unverified** and is attributed to CNT only.
- Six housing authorities operate in this county with different payment-standard
  vintages (City on 2024, County on FY2026 at 90%). Do not blend them.
- A full list of what could **not** be verified from a primary source is in
  `.audit/04_housing_policy.md` §9.
