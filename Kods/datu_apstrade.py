import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
import os

DATA_DIR = "data"
OUT_DIR = "data_edited"

# Slieksnis, lai noteiktu, kad taustiņš ir nospiests (0.0 - 1.0)
PRESS_THRESHOLD = 0.05 

def process_all():
    for root, dirs, files in os.walk(DATA_DIR):
        for fname in files:
            if not fname.endswith(".csv"):
                continue
            
            # Atrodam user_id no mapes nosaukuma (piem., data/user_1/...)
            try:
                folder_name = os.path.basename(root)
                user_id = int(folder_name.split('_')[1])
            except:
                print(f"Izlaista mape (nepareizs formāts): {root}")
                continue

            filepath = os.path.join(root, fname)
            
            # Mēģinām nolasīt failu
            try:
                df = pd.read_csv(filepath)
            except Exception as e:
                print(f"Kļūda lasot failu {fname}: {e}")
                continue

            # Saraksts konkrētajam mēģinājumam
            current_file_features = []

            # Pārveidojam laiku uz sekundēm
            if "Time_us" not in df.columns:
                print(f"Kolonna 'Time_us' nav atrasta failā {fname}")
                continue

            t_us = df["Time_us"].values
            t_s = (t_us - t_us[0]) / 1_000_000.0

            # Apstrādājam katru taustiņu (K1, K2, K3)
            for key_col in ["K1", "K2", "K3"]:
                if key_col not in df.columns:
                    continue

                raw_signal = df[key_col].values
                
                # Meklējam nospiedienu intervālus
                active_indices = np.where(raw_signal > PRESS_THRESHOLD)[0]
                
                if len(active_indices) == 0:
                    continue

                splits = np.where(np.diff(active_indices) > 5)[0] + 1
                presses = np.split(active_indices, splits)

                for i, press_idx in enumerate(presses):
                    if len(press_idx) < 10:
                        continue

                    # Izgūstam datus
                    t_segment = t_s[press_idx]
                    y_segment = raw_signal[press_idx]
                    t_segment = t_segment - t_segment[0] # Normalizējam laiku

                    # Izlīdzināšana ar Savitzky-Golay filtru
                    if len(y_segment) >= 7:
                        window = min(11, len(y_segment) if len(y_segment) % 2 != 0 else len(y_segment)-1)
                        if window > 3:
                            y_segment = savgol_filter(y_segment, window, 2)

                    # Atvasinājumi
                    v = np.gradient(y_segment, t_segment)
                    a = np.gradient(v, t_segment)

                    area = np.trapezoid(y_segment, t_segment)

                    metrics = {
                        "User": user_id,
                        "Key": key_col,
                        "Attempt_File": fname,
                        "Press_ID": i + 1,
                        "Press_Duration": t_segment[-1],
                        "Max_Depth": np.max(y_segment),
                        "Max_Velocity": np.max(np.abs(v)),
                        "Max_Acceleration": np.max(np.abs(a)),
                        "Area": area,
                        "Time_to_Peak": t_segment[np.argmax(y_segment)],
                        "Release_Time": t_segment[-1] - t_segment[np.argmax(y_segment)]
                    }
                    current_file_features.append(metrics)
            
            # Saglabājam apstrādātos datus
            if current_file_features:
                # Izveidojam lietotāja mapi data_edited/user_X
                user_out_dir = os.path.join(OUT_DIR, f"user_{user_id}")
                os.makedirs(user_out_dir, exist_ok=True)

                # data_edited/user_x/features_attempt_y.csv
                new_fname = f"features_{fname}"
                out_path = os.path.join(user_out_dir, new_fname)

                final_df = pd.DataFrame(current_file_features)
                final_df.to_csv(out_path, index=False)
                
                print(f"Saglabāts: {out_path}")
            else:
                print(f"Failā {fname} netika atrasti derīgi nospiedieni.")

    print("\n--- Apstrāde pabeigta! ---")

if __name__ == "__main__":
    process_all()
