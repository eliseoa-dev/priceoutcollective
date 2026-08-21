"""
Predictive Vulnerability Risk Model
Predicts economically_vulnerable from information an outreach/eligibility
program would realistically have -- income, household composition, and
general location -- WITHOUT the itemized budget columns that define the
label (see ml_vulnerability_simulator.py, which recomputes the exact
formula from those columns instead).

This is a genuine prediction task: the model has to learn how household
composition and geography drive the (unseen) cost-of-living threshold,
rather than being handed both sides of the comparison directly. Expect a
real, imperfect score -- not the ~99.9% a leaky feature set would produce.
"""

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score, classification_report
import xgboost as xgb

HERE = Path(__file__).parent
# The committed source is the gzip; pandas reads it directly, so there is no
# need for an unpacked 175 MB copy that would not be in the repo anyway.
DATASET_PATH = HERE / ".." / "data" / "raw" / "san_diego_ca_hlb_hackathon_2024.csv.gz"
OUTPUT_DIR = HERE / ".." / "outputs"

NUMERIC_FEATURES = [
    "hh_income", "hh_size", "no_adult", "no_teenager",
    "no_schooler", "no_preschooler", "no_toddler", "no_infant",
]
GEO_COL = "puma"
TARGET_COL = "economically_vulnerable"


def load_data():
    print(f"Loading household records from {DATASET_PATH}...")
    cols = NUMERIC_FEATURES + [GEO_COL, TARGET_COL]
    df = pd.read_csv(DATASET_PATH, usecols=cols, dtype={GEO_COL: str})
    print(f"Loaded {len(df):,} records successfully.")
    return df


def build_features(df):
    geo_dummies = pd.get_dummies(df[GEO_COL], prefix="puma")
    X = pd.concat([df[NUMERIC_FEATURES], geo_dummies], axis=1)
    y = df[TARGET_COL]
    return X, y


def train_model(X, y):
    print("\n--- Training Predictive Risk Classifier (income + household + location only) ---")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train size: {len(X_train):,}, Test size: {len(X_test):,}")

    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        tree_method="hist",
        random_state=42,
        eval_metric="logloss",
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)

    print(f"Accuracy: {acc:.4%}")
    print(f"ROC-AUC: {auc:.4f}")
    print(
        "(No itemized cost columns were used as features -- this score reflects "
        "genuine prediction from income/household/location, not label reconstruction. "
        "Compare to the leaky version's 0.9999 AUC before the earlier fix.)"
    )
    print("\nClassification Report:")
    report = classification_report(y_test, y_pred, digits=4)
    print(report)

    return model, acc, auc, classification_report(y_test, y_pred, digits=4, output_dict=True)


def plot_feature_importance(model, feature_names, out_path):
    importances = model.feature_importances_
    feat_imp = pd.Series(importances, index=feature_names)

    # Collapse the one-hot PUMA columns into a single bar so the chart stays readable.
    puma_cols = [c for c in feat_imp.index if c.startswith("puma_")]
    puma_total = feat_imp[puma_cols].sum()
    feat_imp = feat_imp.drop(index=puma_cols)
    feat_imp["Location (PUMA, combined)"] = puma_total

    display_names = {
        "hh_income": "Household Annual Income",
        "hh_size": "Household Size",
        "no_adult": "No. of Adults",
        "no_teenager": "No. of Teenagers",
        "no_schooler": "No. of Schoolers",
        "no_preschooler": "No. of Preschoolers",
        "no_toddler": "No. of Toddlers",
        "no_infant": "No. of Infants",
    }
    feat_imp.index = [display_names.get(c, c) for c in feat_imp.index]
    feat_imp = feat_imp.sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ['#e74c3c' if 'Income' in x or 'Location' in x else '#3498db' for x in feat_imp.index]
    feat_imp.plot(kind='barh', color=colors, ax=ax)

    ax.set_title("Predictive Risk Model: Feature Importance\n(income + household + location only, no itemized costs)",
                  fontsize=13, fontweight='bold', pad=15)
    ax.set_xlabel("XGBoost Relative Feature Importance", fontsize=12)
    ax.grid(axis='x', linestyle='--', alpha=0.7)

    plt.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    print(f"Saved feature importance plot to {out_path}")


def write_metrics(acc, auc, report_dict, out_path):
    row = {
        "accuracy": round(acc, 4),
        "roc_auc": round(auc, 4),
        "precision_vulnerable": round(report_dict["1"]["precision"], 4),
        "recall_vulnerable": round(report_dict["1"]["recall"], 4),
        "f1_vulnerable": round(report_dict["1"]["f1-score"], 4),
    }
    pd.DataFrame([row]).to_csv(out_path, index=False)
    print(f"Wrote metrics summary to {out_path}")


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    df = load_data()
    X, y = build_features(df)
    model, acc, auc, report_dict = train_model(X, y)

    plot_feature_importance(model, X.columns, OUTPUT_DIR / "predictive_risk_feature_importance.png")
    write_metrics(acc, auc, report_dict, OUTPUT_DIR / "predictive_risk_metrics.csv")


if __name__ == "__main__":
    main()
