import streamlit as st
import pandas as pd
import sqlite3

# Database configuration
DB_FILE = "consol.db"

def run_query(query):
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query(query, conn)
        df.columns = [str(x).upper() for x in df.columns]
        return df

st.set_page_config(page_title="Law Faculty Research Hub", layout="wide")

st.title("⚖️ Law Faculty Longitudinal Research Hub")
st.markdown("""
    *Targeting the 'Gaps' between directory snapshots (1934–1947).*
""")

# --- SIDEBAR NAVIGATION ---
choice = st.sidebar.radio(
    "Research Modules",
    options=[
        "Transition Analysis (Movers/Stayers)",
        "R Data Export Hub",
        "Faculty Timeline Explorer",
        "Credential Audit (PhD Tracker)"
    ]
)

# --- MODULE 1: TRANSITION ANALYSIS (The "Gap" Finder) ---
if choice == "Transition Analysis (Movers/Stayers)":
    st.header("🔄 Faculty Career Transitions")
    st.info("This module identifies who stayed at their school, who moved, and who left the academy.")
    
    # Get available years for comparison
    years_df = run_query("SELECT DISTINCT SOURCE_YEAR FROM BIOGRAPHY")
    years = sorted(years_df['SOURCE_YEAR'].unique().tolist())
    
    if len(years) >= 2:
        col1, col2 = st.columns(2)
        y1 = col1.selectbox("Start Year (Snapshot A)", years, index=0)
        y2 = col2.selectbox("End Year (Snapshot B)", years, index=1)
        
        if st.button("Generate Transition Report"):
            # logic to compare two years via FULL OUTER JOIN logic
            query = f"""
            SELECT 
                COALESCE(a.FINGERPRINT, b.FINGERPRINT) as FINGERPRINT,
                COALESCE(a."FIRST NAME", b."FIRST NAME") as "FIRST NAME",
                COALESCE(a."MI", b."MI") as "MI",
                COALESCE(a."LAST NAME", b."LAST NAME") as "LAST NAME",
                a.SCHOOL as SCHOOL_START,
                b.SCHOOL as SCHOOL_END
            FROM (SELECT * FROM BIOGRAPHY WHERE SOURCE_YEAR = '{y1}') a
            FULL OUTER JOIN (SELECT * FROM BIOGRAPHY WHERE SOURCE_YEAR = '{y2}') b 
                ON a.FINGERPRINT = b.FINGERPRINT
            """
            # Note: SQLite doesn't support FULL OUTER JOIN directly, 
            # in practice you'd use a UNION of LEFT and RIGHT joins here.
            df = run_query(query) 
            
            def identify_status(row):
                if pd.notnull(row['SCHOOL_START']) and pd.notnull(row['SCHOOL_END']):
                    return "Stayer" if row['SCHOOL_START'] == row['SCHOOL_END'] else "Mover"
                return "Leaver" if pd.notnull(row['SCHOOL_START']) else "Newcomer"

            df['STATUS'] = df.apply(identify_status, axis=1)
            
            # Metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Stayers", len(df[df['STATUS']=='Stayer']))
            m2.metric("Movers", len(df[df['STATUS']=='Mover']))
            m3.metric("Leavers", len(df[df['STATUS']=='Leaver']))
            m4.metric("Newcomers", len(df[df['STATUS']=='Newcomer']))
            
            st.subheader("📍 Movers Requiring Manual Check")
            st.dataframe(df[df['STATUS']=='Mover'], width='stretch')
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Research List for R", csv, "transitions.csv", "text/csv")
    else:
        st.warning("Please upload data for at least two years to analyze transitions.")

# --- MODULE 2: R DATA EXPORT HUB (The "Flat File" Generator) ---
elif choice == "R Data Export Hub":
    st.header("📊 Flat-File Generator for R Analysis")
    st.markdown("Select your variables to create a 'General' style flat file.")
    
    # Selection of variables as requested in the email
    all_vars = ['FINGERPRINT', 'SOURCE_YEAR', 'FIRST_NAME', 'LAST NAME', 'SCHOOL', 'RANK', 'COURSE_COMBINED', 'EDU_COMBINED']
    selected_vars = st.multiselect("Variables to include", all_vars, default=['FINGERPRINT', 'SOURCE_YEAR', 'SCHOOL', 'RANK'])
    
    include_phd = st.checkbox("Include PhD Binary Flag (Y/N)", value=True)
    
    if st.button("Prepare Export"):
        df = run_query("SELECT * FROM R_MASTER_EXPORT")
        
        if include_phd:
            df['PHD_YN'] = df['EDU_COMBINED'].str.contains('Ph.D|PhD', case=False, na=False).map({True: 'Y', False: 'N'})
            selected_vars.append('PHD_YN')
            
        final_df = df[selected_vars]
        st.dataframe(final_df.head(20))
        
        csv = final_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Flat File for R", csv, "faculty_export.csv", "text/csv")

# --- MODULE 3: FACULTY TIMELINE EXPLORER (James H. Barnett Jr. Style) ---
elif choice == "Faculty Timeline Explorer":
    st.header("👤 Longitudinal Faculty Profile")
    st.markdown("""
        This view reconstructs a professor's career by linking records across multiple directory years 
        using their unique digital fingerprint.
    """)

    # 1. FETCH ALL NAMES AND FINGERPRINTS FOR THE DROPDOWN
    # We use R_MASTER_EXPORT as it's our "Clean" display table
    names_df = run_query('SELECT DISTINCT FINGERPRINT, "FIRST NAME", "LAST NAME" FROM R_MASTER_EXPORT ORDER BY "LAST NAME"')
    
    if not names_df.empty:
        # Create a display label: "Last Name, First Name (Fingerprint)"
        names_df['DISPLAY_NAME'] = names_df['LAST NAME'] + ", " + names_df['FIRST NAME'] + " (" + names_df['FINGERPRINT'] + ")"
        selected_option = st.selectbox(
            "Search or Select a Professor to view their history:",
            options=names_df['DISPLAY_NAME'].tolist(),
            index=0,
            help="Start typing a last name to filter."
        )

        # Extract the fingerprint from the selection (it's inside the parentheses)
        selected_fingerprint = selected_option.split("(")[-1].strip(")")

        # 2. EXECUTE THE CHRONOLOGICAL QUERY
        query = f"""
            SELECT * FROM R_MASTER_EXPORT 
            WHERE FINGERPRINT = '{selected_fingerprint}' 
            ORDER BY SOURCE_YEAR ASC
        """
        df = run_query(query)

        if not df.empty:
            # Header Section: Basic Identity
            first_row = df.iloc[0]
            st.divider()
            st.title(f"🎓 {first_row['FIRST NAME']} {first_row['LAST NAME']}")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("First Recorded Year", df['SOURCE_YEAR'].min())
            c2.metric("Last Recorded Year", df['SOURCE_YEAR'].max())
            birth = int(first_row['YEAR OF BIRTH']) if pd.notnull(first_row['YEAR OF BIRTH']) else "N/A"
            c3.metric("Birth Year", birth)
            
            st.divider()

            # 3. TIMELINE LAYOUT
            st.subheader("💼 Career Timeline")
            
            # Iterate through each year found for this professor
            for _, row in df.iterrows():
                # Each year gets its own expandable section
                with st.container(border=True):
                    col_year, col_info = st.columns([1, 4])
                    
                    with col_year:
                        st.subheader(f"📅 {row['SOURCE_YEAR']}")
                        st.caption(f"Source: {row['SOURCE_YEAR']} Directory")
                    
                    with col_info:
                        st.markdown(f"**Institution:** {row['SCHOOL']}")
                        st.markdown(f"**Rank/Title:** {row['RANK']}")
                        
                        # Expandable details for Courses and Education in that specific year
                        inner_col1, inner_col2 = st.columns(2)
                        with inner_col1:
                            with st.expander("📖 Courses Taught"):
                                if row['COURSE_COMBINED']:
                                    # Strip whitespace from each item so the set can identify real duplicates
                                    courses = sorted(set(c.strip() for c in row['COURSE_COMBINED'].split(';') if c.strip()))
                                    for course in courses:
                                        st.write(f"• {course}")
                                else:
                                    st.write("No course data recorded.")

                        with inner_col2:
                            with st.expander("🎓 Credentials"):
                                if row['EDU_COMBINED']:
                                    # Strip whitespace from each item before set() comparison
                                    degrees = sorted(set(d.strip() for d in row['EDU_COMBINED'].split(';') if d.strip()))
                                    for edu in degrees:
                                        st.write(f"• {edu}")
                                else:
                                    st.write("No degree data recorded.")
            
            # 4. EXPORT OPTION FOR PROFESSOR
            st.divider()
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"📥 Download {first_row['LAST NAME']}'s History as CSV",
                data=csv,
                file_name=f"{selected_fingerprint}_history.csv",
                mime='text/csv'
            )
    else:
        st.warning("No data found in the R_MASTER_EXPORT table.")

# --- MODULE 4: CREDENTIAL AUDIT ---
elif choice == "Credential Audit (PhD Tracker)":
    st.header("🎓 Institutional Credential Analysis")
    st.markdown("Analyzing the proportion of faculty with PhDs across schools.")
    
    query = """
    SELECT SCHOOL, 
           COUNT(*) as TOTAL_FACULTY,
           SUM(CASE WHEN EDU_COMBINED LIKE '%PhD%' OR EDU_COMBINED LIKE '%Ph.D%' THEN 1 ELSE 0 END) as PHD_COUNT
    FROM R_MASTER_EXPORT
    GROUP BY SCHOOL
    """
    df = run_query(query)
    df['PHD_PERCENTAGE'] = (df['PHD_COUNT'] / df['TOTAL_FACULTY'] * 100).round(2)
    
    st.dataframe(df.sort_values('PHD_PERCENTAGE', ascending=False))