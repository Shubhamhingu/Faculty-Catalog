import pandas as pd

df = pd.read_excel(r'1934 Teachers.xlsx', sheet_name='Biography', header=0)

df.drop('ID', axis=1, inplace=True)  # Remove the 'ID' column if it exists

degree_nums = range(1, 20)  # since you have up to Degree 19

dfs = []

for i in degree_nums:
    temp = df[[
        'First Name', 'MI', 'Last Name', 'Rank', 'Year of Birth', 'Title', 
        f'Degree {i}',
        f'Year of Degree {i}',
        f'School of Degree {i}',
        f'School of Degree (Standard) {i}'
    ]].copy()
    
    # Rename columns
    temp.columns = [
        'First_Name', 'MI', 'Last_Name', 'rank', 'birth_year', 'Title', 
        'degree', 'degree_year', 'degree_school', 'degree_school_std'
    ]
    
    # Add degree number (optional, useful for debugging)
    temp['degree_num'] = i
    
    dfs.append(temp)

def clean_name(name):
    if pd.isna(name):
        return None
    parts = name.split(',')
    if len(parts) == 2:
        last = parts[0].strip()
        rest = parts[1].strip()
        return f"{last} {rest}"
    return name.strip()


df_long = pd.concat(dfs, ignore_index=True)
df_long = df_long.dropna(subset=['degree'])
df_long['professor_key'] = (
    df_long['First_Name'].fillna('') + ' ' +
    df_long['MI'].fillna('') + ' ' +
    df_long['Last_Name'].fillna('')
).str.replace(r'\s+', ' ', regex=True).str.strip()
df_long['professor_key'] = df_long['professor_key'].apply(clean_name)
df_long['birth_year'] = pd.to_numeric(df_long['birth_year'], errors='coerce').astype('Int64')
df_long['degree_year'] = pd.to_numeric(df_long['degree_year'], errors='coerce').astype('Int64')
# print(df_long.head())

df_long.to_sql('Biography', 'sqlite:///clean_teachers_1934_new.db', if_exists='replace', index=False)

# total = df_long['professor'].nunique()

# phd = df_long[df_long['degree'].str.contains('Ph.D.', case=False, na=False)] \
#         ['professor'].nunique() 

# phd_percentage = (phd / total) * 100

# print(f"Total professors: {total}")
# print(f"Professors with PhD: {phd}")
# print(f"Percentage of professors with PhD: {phd_percentage:.2f}%")