import pandas as pd
import re
from sqlalchemy import create_engine

def generate_fingerprint(last_name, first_name, degree_year):
    """Generates the [LASTNAME]_[FIRSTNAME]_[YEAR] fingerprint."""
    ln = re.sub(r'[^A-Z]', '', str(last_name).upper()) if pd.notna(last_name) else "UNKNOWN"
    fn = re.sub(r'[^A-Z]', '', str(first_name).upper()) if pd.notna(first_name) else ""
    try:
        year = str(int(float(degree_year))) if pd.notna(degree_year) else "0000"
    except:
        year = "0000"
    return f"{ln}_{fn}_{year}"

def extract_subjects(summary):
    """Parses the Summary string into subject and experience."""
    if pd.isna(summary): return []
    pattern = r'([^()]+)\s*\(([^()]+)\)'
    matches = re.findall(pattern, summary)
    return [{'subject': s.strip(), 'experience': e.strip()} for s, e in matches]

def main():
    # 1. Setup
    excel_file = input("Enter the Excel filename (e.g., 1947 Teachers.xlsx): ")
    source_yr = input("Enter the Directory Year (e.g., 1947): ")
    engine = create_engine('sqlite:///trial.db')

    # Load General sheet
    df_gen = pd.read_excel(excel_file, sheet_name='General', header=1)
    if 'ID' in df_gen.columns: df_gen.drop('ID', axis=1, inplace=True)

    # 2. Process Identification
    df_gen['fingerprint'] = df_gen.apply(
        lambda x: generate_fingerprint(x['Last Name'], x['First Name'], x.get('Year of Degree 1', 0)), axis=1
    )
    df_gen['source_year'] = int(source_yr)

    # --- PART 1: CLEAN SCHOOL/GENERAL TABLE ---
    # Identify non-subject columns to keep. 
    # We exclude any column that contains "Years Taught" to avoid schema errors.
    base_cols = [col for col in df_gen.columns if "Years Taught" not in col and col != 'Summary']
    df_school_clean = df_gen[base_cols].copy()
    
    # Save the cleaned general record (snap-shot of where they are and their rank)
    df_school_clean.to_sql('School_Full_Records', engine, if_exists='append', index=False)

    # --- PART 2: SUBJECTS (The Long-Form Solution) ---
    # All subject information is extracted from the 'Summary' column here.
    df_gen['parsed'] = df_gen['Summary'].apply(extract_subjects)
    df_subj = df_gen.explode('parsed')
    df_subj['subject'] = df_subj['parsed'].apply(lambda x: x['subject'] if isinstance(x, dict) else None)
    df_subj['experience'] = df_subj['parsed'].apply(lambda x: x['experience'] if isinstance(x, dict) else None)
    
    final_subj = df_subj[['fingerprint', 'source_year', 'subject', 'experience']].dropna()
    final_subj.to_sql('Subject', engine, if_exists='append', index=False)

    # --- PART 3: MASTER INDEX (For R Analysis) ---
    # Professor Andy wants a standard set of variables for his R scripts.
    master_cols = ['fingerprint', 'source_year', 'Year of Birth', 'First Name', 'MI', 'Last Name', 'Rank', 'School']
    # Filter only if columns exist in current sheet
    available_master_cols = [c for c in master_cols if c in df_gen.columns]
    
    master_df = df_gen[available_master_cols].copy()
    if 'Year of Birth' in master_df.columns:
        master_df['Year of Birth'] = pd.to_numeric(master_df['Year of Birth'], errors='coerce').astype('Int64')
    
    master_df.to_sql('Master_Faculty_Index', engine, if_exists='append', index=False)

    print(f"\n[SUCCESS] Data for {source_yr} added to trial.db.")

    # --- PART 4: AUTOMATED COMPARISON REPORTS ---
    # Check if we have at least two years of data to compare
    all_data = pd.read_sql('SELECT * FROM Master_Faculty_Index', engine)
    years = sorted(all_data['source_year'].unique())

    if len(years) >= 2:
        y1, y2 = years[0], years[-1] # Comparing the earliest vs latest found
        print(f"Generating comparison report between {y1} and {y2}...")
        
        df1 = all_data[all_data['source_year'] == y1]
        df2 = all_data[all_data['source_year'] == y2]

        comparison = pd.merge(df1, df2, on='fingerprint', how='outer', suffixes=(f'_{y1}', f'_{y2}'))

        # Movers: In both years, but different schools
        movers = comparison[
            (comparison[f'School_{y1}'].notna()) & 
            (comparison[f'School_{y2}'].notna()) & 
            (comparison[f'School_{y1}'] != comparison[f'School_{y2}'])
        ]
        
        # Leavers: In Y1 but not Y2
        leavers = comparison[(comparison[f'School_{y1}'].notna()) & (comparison[f'School_{y2}'].isna())]

        # Save Reports
        if not movers.empty:
            movers.to_csv(f'movers_{y1}_to_{y2}.csv', index=False)
            print(f"-> Created 'movers_{y1}_to_{y2}.csv'")
        if not leavers.empty:
            leavers.to_csv(f'leavers_{y1}_to_{y2}.csv', index=False)
            print(f"-> Created 'leavers_{y1}_to_{y2}.csv'")

if __name__ == "__main__":
    main()