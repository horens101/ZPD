import pandas as pd
import pingouin as pg
import os
import warnings

warnings.filterwarnings("ignore")

DATA_EDITED_DIR = "data_edited"

def save_icc_per_user():
    print("--- ICC aprēķins ---")
    
    # Atrodam visas lietotāju mapes
    users = [d for d in os.listdir(DATA_EDITED_DIR) if os.path.isdir(os.path.join(DATA_EDITED_DIR, d))]
    
    for user_folder in users:
        user_path = os.path.join(DATA_EDITED_DIR, user_folder)
        try:
            user_id = user_folder.split('_')[1]
        except:
            continue
        
        # Saraksts, kur glabāsim lietotāja rezultātus
        user_icc_results = []

        all_attempts = []
        files = [f for f in os.listdir(user_path) if f.endswith(".csv") and not f.startswith("icc_")]
        
        if len(files) < 2:
            print(f"User {user_id}: Nepietiek failu (atrasti {len(files)}). Nepieciešami vismaz 2.")
            continue

        print(f"--- Rēķina ICC lietotājam {user_id} (faili: {len(files)}) ---")

        for fname in files:
            file_path = os.path.join(user_path, fname)
            try:
                df = pd.read_csv(file_path)
                df['Session'] = fname
                all_attempts.append(df)
            except Exception as e:
                print(f"Kļūda lasot {fname}: {e}")

        if not all_attempts:
            continue

        # Apvienojam visus datus vienā DataFrame
        full_data = pd.concat(all_attempts, ignore_index=True)

        # Izveidojam unikālu ID katram nospiedienam: Key + Press_ID
        full_data['Target_ID'] = full_data['Key'] + "_" + full_data['Press_ID'].astype(str)

        # Pazīmes, kurām rēķināt ICC
        features_to_test = [
            'Press_Duration', 'Max_Depth', 'Max_Velocity', 
            'Max_Acceleration', 'Area', 'Time_to_Peak', 'Release_Time'
        ]

        for feature in features_to_test:
            if feature not in full_data.columns:
                continue

            try:
                pivot = full_data.pivot(index='Target_ID', columns='Session', values=feature)
                
                # Ja vienā failā 20 nospiedieni, otrā 19, tiek izmantoti 19.
                valid_data = pivot.dropna()

                if valid_data.empty or len(valid_data) < 2:
                    # Ja ir pārāk maza datu sakritība
                    continue

                icc_data = valid_data.reset_index().melt(id_vars='Target_ID', var_name='Session', value_name='Score')

                # ICC aprēķini
                icc = pg.intraclass_corr(data=icc_data, targets='Target_ID', raters='Session', ratings='Score')
                
                icc_val = icc.set_index('Type').loc['ICC3k']['ICC']

                user_icc_results.append({
                    "Feature": feature,
                    "ICC_Score": icc_val,
                    "N_Samples": len(valid_data) # cik nospiedieni tika salīdzināti
                })
            except Exception as e:
                pass

        if user_icc_results:
            results_df = pd.DataFrame(user_icc_results)
            
            # Sakārtojam no labākā uz sliktāko
            results_df = results_df.sort_values(by="ICC_Score", ascending=False)
            
            # Saglabājam
            save_path = os.path.join(user_path, "icc_results_individual.csv")
            results_df.to_csv(save_path, index=False)
            
            print(f"-> Saglabāts: {save_path}")
            print(results_df[['Feature', 'ICC_Score', 'N_Samples']].to_string(index=False))
            print("-" * 30)
        else:
            print(f"User {user_id}: Nav izdevies aprēķināt ICC nevienai pazīmei.")

if __name__ == "__main__":
    save_icc_per_user()
