import pandas as pd
import re
from sqlalchemy import create_engine

def generate_fingerprint(last_name, first_name, degree_year):
    """Generates the [LASTNAME]_[FIRSTINITIAL]_[YEAR] fingerprint."""
    ln = re.sub(r'[^A-Z]', '', str(last_name).upper()) if pd.notna(last_name) else "UNKNOWN"
    fn = re.sub(r'[^A-Z]', '', str(first_name).upper()) if pd.notna(first_name) else ""

    try:
        # Convert to float then int to handle cases like '1934.0'
        year = str(int(float(degree_year))) if pd.notna(degree_year) else "0000"
    except:
        year = "0000"
        
    return f"{ln}_{fn}_{year}"

def extract_subjects(summary):
    """Matches 'Subject (Experience)' patterns from your Subject.py logic."""
    if pd.isna(summary):
        return []
    pattern = r'([^()]+)\s*\(([^()]+)\)'
    summaryvar = summary.replace('\r', ' ').replace("_x000D_", "\n")
    matches = re.findall(pattern, summaryvar)
    return [{'subject': s.strip(), 'experience': e.strip()} for s, e in matches]

def main():
    # 1. Setup & Metadata
    excel_file = input("Enter the Excel filename (e.g., 1947 Teachers.xlsx): ")
    source_yr = input("Enter the Directory Year (e.g., 1947): ")
    engine = create_engine('sqlite:///consol.db')

    # --- PART 1: EDUCATION TABLE (From 'General' Sheet) ---
    print("Processing Education data...")
    df_education = pd.read_excel(excel_file, sheet_name='Biography', header=0)  # Using 'General' for basic info, adjust if needed
    
    df_education.drop('ID', axis=1, inplace=True)  # Remove 'ID' if it exists
    
    # Explode degrees into multiple rows
    education_rows = []
    for idx, row in df_education.iterrows():
        # Generate fingerprint using Year of Degree 1 (or first available)
        fingerprint = generate_fingerprint(row['Last Name'], row['First Name'], row['Year of Degree 1'])
        for i in range(1, 20):  # Assuming up to Degree 19
            deg_col = f'Degree {i}'
            yr_col = f'Year of Degree {i}'
            sch_col  = f'School of Degree (Standard) {i}'
            if pd.notna(row.get(deg_col)):
                education_rows.append({
                    'fingerprint': fingerprint,
                    'source_year': source_yr,
                    'degree': row[deg_col],
                    'year': row.get(yr_col) if pd.notna(row.get(yr_col)) else None,
                    'school': row.get(sch_col) if pd.notna(row.get(sch_col)) else None
                })
    
    df_education = pd.DataFrame(education_rows)
    df_education['year'] = pd.to_numeric(df_education['year'], errors='coerce').astype('Int64')
    df_education.to_sql('Education', engine, if_exists='append', index=False)

    # --- PART 2: SUBJECT & EXPERIENCE (From 'General' Sheet) ---
    print("Processing Subject data...")
    # header=1 because your Subject.py used header=1
    df_gen = pd.read_excel(excel_file, sheet_name='General', header=1)
    
    # Create the Fingerprint
    df_gen['fingerprint'] = df_gen.apply(
        lambda x: generate_fingerprint(x['Last Name'], x['First Name'], x['Year of Degree 1']), axis=1
    )
    df_gen['source_year'] = source_yr
    # Parse and Explode Subjects
    df_gen['parsed'] = df_gen['Summary'].apply(extract_subjects)
    df_courses = df_gen.explode('parsed')
    
    # Expand the dict into columns
    df_courses['subject'] = df_courses['parsed'].apply(lambda x: x['subject'] if isinstance(x, dict) else None)
    df_courses['experience'] = df_courses['parsed'].apply(lambda x: x['experience'] if isinstance(x, dict) else None)
    
    # Final Subjects table with Fingerprint and Source Year
    final_subj = df_courses[['fingerprint', 'source_year', 'subject', 'experience']].dropna()
    final_subj.to_sql('Courses', engine, if_exists='append', index=False)

    # --- PART 3: MASTER EXPORT (For R Systems) ---
    # Andy wants a flat file. We'll join the basic info into one master view.
    master_df = df_gen[['fingerprint', 'source_year','Year of Birth' , 'First Name', 'MI', 'Last Name', 'Rank', 'School','Dean (Y/N)', 'Title']].copy()
    master_df['Year of Birth'] = pd.to_numeric(master_df['Year of Birth'], errors='coerce').astype('Int64')
    master_df.to_sql('Biography', engine, if_exists='append', index=False)

    print(f"Done! Database updated for year {source_yr}.")
    export_for_professor(engine)
    # print('Export for Professor Andy created successfully.')



def export_for_professor(engine):
    # 1. Get the base biography
    bio = pd.read_sql('SELECT * FROM Biography', engine)
    
    # 2. Aggregate Courses: "Subject A (Exp); Subject B (Exp)"
    courses = pd.read_sql('SELECT * FROM Courses', engine)
    courses['course_combined'] = courses['subject'] + " (" + courses['experience'] + ")"
    agg_courses = courses.groupby(['fingerprint', 'source_year'])['course_combined'].apply(lambda x: '; '.join(x)).reset_index()
    
    # 3. Aggregate Education: "Degree (Year); Degree (Year)"
    edu = pd.read_sql('SELECT * FROM Education', engine)
    is_phd_mask = edu['degree'].str.replace(r'[^a-zA-Z0-9]', '', regex=True).str.lower() == 'phd'
    edu['PHD'] = is_phd_mask.map({True: 'Y', False: 'N'})
    edu = edu.merge(bio[['fingerprint', 'School']], on='fingerprint', how='left')
    def is_alumni(row):
        edu_s = str(row['school']).lower().strip()
        curr_s = str(row['School']).lower().strip()
        if not edu_s or edu_s == 'none' or not curr_s or curr_s == 'none':
            return 'N'
        return 'Y' if edu_s in curr_s else 'N'
    edu['Is_Alumni'] = edu.apply(is_alumni, axis=1)
    edu['edu_combined'] = edu['degree'] + " (" + edu['year'].astype(str) + ", " + edu['school'].fillna('Unknown') + ")"
    agg_edu = edu.groupby(['fingerprint', 'source_year']).agg({
        'edu_combined': lambda x: '; '.join(x),
        'PHD': lambda x: 'Y' if (x == 'Y').any() else 'N',
        'Is_Alumni': lambda x: 'Y' if (x == 'Y').any() else 'N'
    }).reset_index()
    
    # 4. Merge them all into one "Flat" table
    flat_df = bio.merge(agg_courses, on=['fingerprint', 'source_year'], how='left')
    flat_df = flat_df.merge(agg_edu, on=['fingerprint', 'source_year'], how='left')
    flat_df['Manual_Check'] = flat_df['fingerprint'].str.contains('_0000', na=False).map({True: 'Y', False: 'N'})
    
    # 5. Save as a special export table
    flat_df.to_sql('R_Master_Export', engine, if_exists='replace', index=False)
    print("Export table 'R_Master_Export' created. One row per professor per year.")

if __name__ == "__main__":
    main()