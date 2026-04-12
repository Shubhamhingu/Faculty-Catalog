import pandas as pd
from sqlalchemy import create_engine

engine = create_engine('sqlite:///consol.db')

def export_for_professor():
    # 1. Get the base biography
    bio = pd.read_sql('SELECT * FROM Biography', engine)
    
    # 2. Aggregate Courses: "Subject A (Exp); Subject B (Exp)"
    courses = pd.read_sql('SELECT * FROM Courses', engine)
    courses['course_combined'] = courses['subject'] + " (" + courses['experience'] + ")"
    agg_courses = courses.groupby(['fingerprint', 'source_year'])['course_combined'].apply(lambda x: '; '.join(x)).reset_index()
    
    # 3. Aggregate Education: "Degree (Year); Degree (Year)"
    edu = pd.read_sql('SELECT * FROM Education', engine)
    edu['edu_combined'] = edu['degree'] + " (" + edu['school'] + ", " + edu['year'].astype(str) + ")"
    agg_edu = edu.groupby(['fingerprint', 'source_year'])['edu_combined'].apply(lambda x: '; '.join(x.astype(str))).reset_index()
    
    # 4. Merge them all into one "Flat" table
    flat_df = bio.merge(agg_courses, on=['fingerprint', 'source_year'], how='left')
    flat_df = flat_df.merge(agg_edu, on=['fingerprint', 'source_year'], how='left')
    
    # 5. Save as a special export table
    flat_df.to_sql('R_Master_Export', engine, if_exists='replace', index=False)
    print("Export table 'R_Master_Export' created. One row per professor per year.")

export_for_professor()