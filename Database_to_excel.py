import sqlite3
import pandas as pd

def export_db_to_excel(db_path, output_excel_path):
    conn = sqlite3.connect(db_path)
    
    # Get table names
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    # Create Excel writer
    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        for table_name in tables:
            table = table_name[0]
            df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
            df.to_excel(writer, sheet_name=table[:31], index=False)  # Excel sheet name max = 31 chars

    print(f"Exported {len(tables)} tables to {output_excel_path}")
    conn.close()

# Usage
export_db_to_excel('consol.db', 'catalog.xlsx')
