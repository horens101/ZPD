import pandas as pd
import matplotlib.pyplot as plt
import pingouin as pg
import os

DATA_DIR = "data_edited"

def compare_users():

    all_frames = []

    users = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]
    if len(users) < 2:
        print("Nepieciešami vismaz 2 lietotāji!")
        return

    print(f"Ielasa datus no {len(users)} lietotājiem.")

    for user in sorted(users):
        folder = os.path.join(DATA_DIR, user)
        files = [f for f in os.listdir(folder) if f.endswith(".csv") and not f.startswith("icc")]

        for f in files:
            try:
                df = pd.read_csv(os.path.join(folder, f))
                df["User"] = user

                cols = [
                    "User", "Press_Duration", "Max_Depth", "Max_Velocity",
                    "Max_Acceleration", "Area", "Time_to_Peak", "Release_Time"
                ]
                df = df[[c for c in cols if c in df.columns]]
                all_frames.append(df)

            except:
                pass

    if not all_frames:
        print("Nav datu.")
        return

    df_all = pd.concat(all_frames, ignore_index=True)
    print("Kopējais nospiedienu skaits: ", len(df_all))

    # ANOVA aprēķins
    features = [
        "Press_Duration", "Max_Depth", "Max_Velocity",
        "Max_Acceleration", "Area", "Time_to_Peak", "Release_Time"
    ]

    anova_results = []

    print("\nRēķina ANOVA...")
    for ft in features:
        try:
            aov = pg.anova(data=df_all, dv=ft, between="User")
            anova_results.append({
                "Feature": ft,
                "F": aov["F"].values[0],
                "p": aov["p-unc"].values[0]
            })
        except:
            pass

    res_df = pd.DataFrame(anova_results).sort_values(by="F", ascending=False)
    res_df.to_csv(os.path.join(DATA_DIR, "inter_class_separation.csv"), index=False)

    print("\n=== ANOVA rezultāti ===")
    print(res_df)

    # Vizualizācija labākajam parametram
    top = res_df.iloc[0]["Feature"]

    labels = sorted(df_all["User"].unique())
    groups = [df_all[df_all["User"] == u][top] for u in labels]

    plt.figure(figsize=(12, 6))
    plt.boxplot(groups, labels=labels, showfliers=False)
    plt.ylabel(top)
    plt.xlabel("Lietotājs")
    plt.title(f"Parametra {top} individuālo nospiedienu sadalījums starp lietotājiem (ANOVA)")
    plt.tight_layout()
    plt.savefig(os.path.join(DATA_DIR, "anova_top_feature.png"), dpi=300)
    plt.close()

    print(f"Grafiks saglabāts: {DATA_DIR}/anova_top_feature.png")


if __name__ == "__main__":
    compare_users()
