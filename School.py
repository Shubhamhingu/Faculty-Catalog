import pandas as pd
import sqlite3
import os

# File paths
excel_file = r'1934 Teachers.xlsx'

df = pd.read_excel(excel_file, sheet_name='By School', header=0)
df.drop('ID', axis=1, inplace=True)  # Remove the 'ID' column if it exists
df.rename(columns={'First Name': 'First_Name', 'Last Name': 'Last_Name'}, inplace=True)

def clean_name(name):
    if pd.isna(name):
        return None
    parts = name.split(',')
    if len(parts) == 2:
        last = parts[0].strip()
        rest = parts[1].strip()
        return f"{last} {rest}"
    return name.strip()

df['professor_key'] = (
    df['First_Name'].fillna('') + ' ' +
    df['MI'].fillna('') + ' ' +
    df['Last_Name'].fillna('')
).str.replace(r'\s+', ' ', regex=True).str.strip()
df['professor_key'] = df['professor_key'].apply(clean_name)

df.to_sql('School', 'sqlite:///clean_teachers_1934_new.db', if_exists='replace', index=False)