import json
import pandas as pd
from pathlib import Path
import argparse

DATA_PATH = Path(".")


# ==========================
# LOAD & VALIDATE DATA
# ==========================
def load_json_files():
    all_data = []

    for file in DATA_PATH.glob("ajax*.json"):
        print("Lecture :", file)

        try:
            with open(file, "r", encoding="utf-8") as f:
                content = json.load(f)
                logs = content.get("data", [])

                for log in logs:
                    # Validation minimale des champs obligatoires
                    if not log.get("request") or not log.get("response"):
                        continue
                    all_data.append(log)

        except Exception as e:
            print(f"Erreur lecture {file}: {e}")
            continue

    return all_data


# ==========================
# CONVERSION SCORE LOGIC
# ==========================
def compute_conversion_score(row):
    score = 0

    if row["total_pax"] and row["total_pax"] >= 3:
        score += 2

    if row["shuttle_available"] == 0:
        score += 3

    if row["lead_time_hours"] and row["lead_time_hours"] > 48:
        score += 1

    return score


# ==========================
# MAIN
# ==========================
if __name__ == "__main__":

    # ===== CLI ARGUMENTS =====
    parser = argparse.ArgumentParser(
        description="Search Log Analytics & Shuttle Optimization Engine"
    )

    parser.add_argument("--route", type=str, help="Filtrer par route (ex: BVA->DIS)")
    parser.add_argument("--from", dest="from_date", type=str, help="Date début YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", type=str, help="Date fin YYYY-MM-DD")

    args = parser.parse_args()

    # ===== LOAD DATA =====
    data = load_json_files()
    print(f"Total logs chargés : {len(data)}")

    df = pd.DataFrame(data)

    if df.empty:
        print("Aucune donnée valide.")
        exit()

    # ==========================
    # EXTRACTION
    # ==========================

    df["route"] = df["path"].str.replace("&gt;", "->")

    df["country"] = df["user"].apply(
        lambda x: x.get("country") if isinstance(x, dict) else None
    )

    df["total_pax"] = df["request"].apply(
        lambda x: x.get("pax", {}).get("total") if isinstance(x, dict) else None
    )

    df["shuttle_available"] = df["response"].apply(
        lambda x: x.get("shuttle", {}).get("available") if isinstance(x, dict) else None
    )

    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

    df["request_time"] = df["request"].apply(
        lambda x: x.get("requestTime") if isinstance(x, dict) else None
    )

    df["request_time"] = pd.to_datetime(df["request_time"], errors="coerce")

    df["request_time"] = df["request_time"].dt.tz_localize(None)
    df["created_at"] = df["created_at"].dt.tz_localize(None)

    df["lead_time_hours"] = (
        df["request_time"] - df["created_at"]
    ).dt.total_seconds() / 3600

    # ==========================
    # FILTERS (CLI)
    # ==========================

    if args.route:
        df = df[df["route"] == args.route]

    if args.from_date:
        df = df[df["created_at"] >= pd.to_datetime(args.from_date)]

    if args.to_date:
        df = df[df["created_at"] <= pd.to_datetime(args.to_date)]

    print(f"Dataset après filtres : {len(df)} lignes")

    if df.empty:
        print("Aucune donnée après filtres.")
        exit()

    # ==========================
    # CONVERSION SCORE
    # ==========================

    df["conversion_score"] = df.apply(compute_conversion_score, axis=1)

    print("\n===== LEAD TIME MOYEN (heures) =====")
    print(round(df["lead_time_hours"].mean(), 2))

    print("\n===== CONVERSION POTENTIAL SCORE (MOYEN) =====")
    print(round(df["conversion_score"].mean(), 2))

    # ==========================
    # ANALYTICS
    # ==========================

    print("\n===== TOP 5 ROUTES =====")
    print(df["route"].value_counts().head(5))

    print("\n===== MOYENNE PASSAGERS =====")
    print(round(df["total_pax"].mean(), 2))

    print("\n===== TAUX DISPONIBILITÉ SHUTTLE =====")
    print(round((df["shuttle_available"] > 0).mean() * 100, 2), "%")

    print("\n===== DEMANDE PAR HEURE =====")
    print(df["requestHour"].value_counts().sort_index())

    print("\n===== RÉPARTITION PAR PAYS =====")
    print(df["country"].value_counts())

    # ==========================
    # EXPORT CSV
    # ==========================

    summary_df = pd.DataFrame({
        "metric": [
            "lead_time_mean_hours",
            "average_passengers",
            "shuttle_availability_rate_percent",
            "conversion_score_mean"
        ],
        "value": [
            round(df["lead_time_hours"].mean(), 2),
            round(df["total_pax"].mean(), 2),
            round((df["shuttle_available"] > 0).mean() * 100, 2),
            round(df["conversion_score"].mean(), 2)
        ]
    })

    summary_df.to_csv("summary_report.csv", index=False)
    print("\n✅ summary_report.csv généré")

    # ==========================
    # EXPORT JSON
    # ==========================

    report = {
        "lead_time_mean_hours": round(df["lead_time_hours"].mean(), 2),
        "average_passengers": round(df["total_pax"].mean(), 2),
        "shuttle_availability_rate_percent": round((df["shuttle_available"] > 0).mean() * 100, 2),
        "conversion_score_mean": round(df["conversion_score"].mean(), 2),
        "top_5_routes": df["route"].value_counts().head(5).to_dict(),
        "top_countries": df["country"].value_counts().head(5).to_dict()
    }

    with open("report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)

    print("✅ report.json généré")

    # ==========================
    # BUSINESS INTELLIGENCE
    # ==========================

    print("\n===== BUSINESS RECOMMENDATIONS =====")

    high_demand_routes = df["route"].value_counts()
    low_shuttle_routes = df[df["shuttle_available"] == 0]["route"].value_counts()

    for route in high_demand_routes.head(3).index:
        if route in low_shuttle_routes.index:
            print(f"⚠️ Ajouter des shuttles sur {route} (forte demande + faible dispo)")
        else:
            print(f"✅ Route {route} performante, maintenir capacité")