"""
Aggregates the 1.17M synthetic household microdata dataset into ZIP-code level metrics.
Generates an updated data/zips.csv file with real San Diego County metrics.
"""

from pathlib import Path
import pandas as pd
import numpy as np

HERE = Path(__file__).parent
DATASET_PATH = HERE / "san_diego_ca_hlb_hackathon_2024_20260811.csv"
OUTPUT_CSV = HERE / "zips.csv"

# PUMA to representative San Diego ZIP code mapping approximation for SD County (073xx PUMAs)
PUMA_TO_ZIP = {
    "07301": "92028", # Fallbrook / Bonsall
    "07302": "92054", # Oceanside
    "07303": "92084", # Vista / San Marcos
    "07304": "92025", # Escondido
    "07305": "92064", # Poway / Ramona
    "07306": "92037", # La Jolla / University City
    "07307": "92109", # Pacific Beach / Mission Beach
    "07308": "92101", # Downtown San Diego / Balboa Park
    "07309": "92105", # City Heights / Mid-City
    "07310": "92115", # College Area / Encanto
    "07311": "92120", # San Carlos / Allied Gardens
    "07312": "92126", # Mira Mesa / Sorrento Valley
    "07313": "92129", # Rancho Penasquitos
    "07314": "92071", # Santee / El Cajon North
    "07315": "92020", # El Cajon South / Spring Valley
    "07316": "92102", # Southeastern San Diego
    "07317": "92113", # Barrio Logan / Logan Heights
    "07318": "92154", # Otay Mesa / San Ysidro
    "07319": "92173", # San Ysidro / Border
    "07320": "92118", # Coronado / Imperial Beach
    "07321": "92114", # Encanto / Skyline
    "07322": "92014", # Del Mar / Solana Beach
}

def main():
    print(f"Loading dataset from {DATASET_PATH}...")
    cols = [
        "puma", "geoid", "hh_income", "housing_cost_month", 
        "food_cost_month", "childcare_cost_month", "transp_cost_month",
        "healthcare_cost_month", "economically_vulnerable"
    ]
    df = pd.read_csv(DATASET_PATH, usecols=cols)
    print(f"Loaded {len(df):,} household records.")

    # Convert PUMA to string padded to 5 digits
    df["puma"] = df["puma"].astype(str).str.zfill(5)
    
    # Calculate household rent burden: (housing_cost_month * 12) / hh_income
    df["annual_housing_cost"] = df["housing_cost_month"] * 12
    df["rent_burden_pct"] = np.where(df["hh_income"] > 0, df["annual_housing_cost"] / df["hh_income"], 1.0)
    df["rent_burden_pct"] = np.clip(df["rent_burden_pct"], 0, 1.0)

    # Map PUMA to ZIP code
    df["zip"] = df["puma"].map(PUMA_TO_ZIP).fillna("92101")

    # Group by ZIP code to compute real aggregate metrics
    grouped = df.groupby("zip").agg(
        median_income=("hh_income", "median"),
        median_rent=("housing_cost_month", "median"),
        rent_burden_pct=("rent_burden_pct", "median"),
        vulnerable_pct=("economically_vulnerable", "mean"),
        household_count=("hh_income", "count")
    ).reset_index()

    # Derived metrics for schema compatibility
    grouped["rent_growth_rate"] = 0.055   # ~5.5% annual rent growth baseline
    grouped["income_growth_rate"] = 0.025 # ~2.5% annual income growth baseline
    
    CRISIS_BURDEN = 0.50
    ratio = (1 + grouped["rent_growth_rate"]) / (1 + grouped["income_growth_rate"])
    
    runway_list = []
    for _, row in grouped.iterrows():
        b0 = row["rent_burden_pct"]
        r_growth = row["rent_growth_rate"]
        i_growth = row["income_growth_rate"]
        ratio = (1 + r_growth) / (1 + i_growth)
        if b0 >= CRISIS_BURDEN:
            runway = 0.0
        elif ratio <= 1.0:
            runway = 120.0
        else:
            runway = 12 * np.log(CRISIS_BURDEN / b0) / np.log(ratio)
        runway_list.append(round(max(0.0, runway), 1))
    
    grouped["runway_months"] = runway_list
    grouped["featured"] = grouped["vulnerable_pct"] > 0.40  # Top vulnerable ZIPs featured

    # Reorder to match data/zips.csv schema
    out_df = grouped[[
        "zip", "median_income", "median_rent", "rent_burden_pct",
        "rent_growth_rate", "income_growth_rate", "runway_months", "featured"
    ]]

    # Round numerical metrics
    out_df["median_income"] = out_df["median_income"].round(0)
    out_df["median_rent"] = out_df["median_rent"].round(0)
    out_df["rent_burden_pct"] = out_df["rent_burden_pct"].round(4)

    # Save to zips.csv
    out_df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSuccessfully generated {OUTPUT_CSV} with {len(out_df)} San Diego ZIP codes!")
    print(out_df.head(10).to_string(index=False))

if __name__ == "__main__":
    main()
