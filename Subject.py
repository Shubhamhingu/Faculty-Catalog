import pandas as pd
import re

df = pd.read_excel("1934 Teachers.xlsx", sheet_name='By Subject', header=2)
df.drop('ID', axis=1, inplace=True)  # Remove the 'ID' column if it exists

# -----------------------------
# Step 1: Clean faculty name
# -----------------------------
def clean_name(name):
    if pd.isna(name):
        return None
    parts = name.split(',')
    if len(parts) == 3:
        last = parts[0].strip()
        first = parts[1].strip()
        title = parts[2].strip()
        return f"{first} {last} {title}"
    if len(parts) == 2:
        last = parts[0].strip()
        rest = parts[1].strip()
        return f"{rest} {last}"
    return name.strip()

df['professor_key'] = df['Faculty Name'].apply(clean_name)

# -----------------------------
# Step 2: Extract subject + experience
# -----------------------------
def extract_subjects(summary):
    if pd.isna(summary):
        return []
    
    # Pattern: Subject (Experience)
    pattern = r'([^()]+)\s*\(([^()]+)\)'
    matches = re.findall(pattern, summary)
    
    result = []
    for subject, exp in matches:
        result.append({
            'subject': subject.strip(),
            'experience': exp.strip()
        })
    
    return result

df['parsed'] = df['Summary'].apply(extract_subjects)

# -----------------------------
# Step 3: Explode into rows
# -----------------------------
df_exploded = df.explode('parsed')

# -----------------------------
# Step 4: Normalize columns
# -----------------------------
df_exploded['subject'] = df_exploded['parsed'].apply(lambda x: x['subject'] if isinstance(x, dict) else None)
df_exploded['experience'] = df_exploded['parsed'].apply(lambda x: x['experience'] if isinstance(x, dict) else None)

# -----------------------------
# Step 5: Final cleaned table
# -----------------------------
final_df = df_exploded[['professor_key', 'subject', 'experience']].dropna()

final_df.to_sql('Subject', 'sqlite:///clean_teachers_1934_new.db', if_exists='replace', index=False)
# print(final_df.head())