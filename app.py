import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# --- CONFIGURATION ---
DB_FILE = "streamlit_db.db"  # Change this to your actual .db filename

def run_query(query):
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query(query, conn)
        # FORCE ALL COLUMN NAMES TO UPPERCASE
        df.columns = [str(x).upper() for x in df.columns]
        return df

st.set_page_config(page_title="Legal Faculty Data Explorer", layout="wide")

st.title("⚖️ Legal Faculty Research Dashboard")
st.markdown("Use the sidebar to switch between different data insights.")

# --- SIDEBAR NAVIGATION ---
# Replace your sidebar selectbox with this:
choice = st.sidebar.radio(
    "Navigation Menu", 
    options=[
        "Professor Alumni Finder",
        "Degree Analysis by School",
        "Course Distribution",
        "School Subject Catalog",
        "Raw Search (James H. Barnett Jr. Style)"
    ]
)

# --- MODULE 1: DEGREE AND TEACHING IN SAME SCHOOL ---
if choice == "Professor Alumni Finder":
    st.header("🎓 The 'In-House' Talent Tracker")
    st.markdown("""
        This module identifies faculty members who are teaching at the same institution where they earned at least one of their degrees.
        In academia, this is often referred to as **'Institutional Retention'** or **'Academic Inbreeding.'**
    """)
    
    # 1. Fetch the data
    query = """
    SELECT DISTINCT PROFESSOR_KEY, DEGREE_SCHOOL_STD, TITLE
    FROM Biography
    WHERE Title LIKE '%' || DEGREE_SCHOOL || '%'
    ORDER BY DEGREE_SCHOOL_STD;
    """
    df = run_query(query)

    if not df.empty:
        # 2. Top-Level Metrics
        total_alumni_profs = len(df['PROFESSOR_KEY'].unique())
        top_school = df['DEGREE_SCHOOL_STD'].value_counts().idxmax()
        top_count = df['DEGREE_SCHOOL_STD'].value_counts().max()

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Alumni Faculty", total_alumni_profs)
        col2.metric("Leading Institution", top_school)
        col3.metric("Max Alumni at One School", top_count)

        st.divider()

        # 3. Visual Analysis: Which schools hire their own the most?
        st.subheader("📊 Schools with the Highest Alumni Retention")
        chart_data = df['DEGREE_SCHOOL_STD'].value_counts().reset_index()
        chart_data.columns = ['SCHOOL', 'ALUMNI_COUNT']
        
        fig = px.bar(
            chart_data.head(10), 
            x='ALUMNI_COUNT', 
            y='SCHOOL', 
            orientation='h',
            title="Top 10 Schools Hiring Their Own Graduates",
            labels={'ALUMNI_COUNT': 'Number of Alumni Professors', 'SCHOOL': 'University'},
            color='ALUMNI_COUNT',
            color_continuous_scale='Blues'
        )
        # Invert y-axis so the highest is on top
        fig.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, width="stretch")

        # 4. Detailed Searchable List
        st.subheader("🔍 Detailed Alumni List")
        with st.expander("Click to browse individual professor records"):
            # Clean up column names for display
            display_df = df.copy()
            display_df.columns = ['Professor Name', 'Alma Mater', 'Current Appointment']
            st.dataframe(display_df, width="stretch")
            
            # Add a download button for the professor
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Alumni List as CSV",
                data=csv,
                file_name='university_alumni_faculty.csv',
                mime='text/csv',
            )
    else:
        st.info("No records found where the professor's degree school matches their current title.")

# --- MODULE 2: PHD PERCENT GROUPED BY SCHOOL ---
elif choice == "Degree Analysis by School":
    st.header("Advanced Degree Penetration")
    
    degree_interest = st.text_input("Search for Degree Type (e.g., Ph.D., J.D.)", value="Ph.D.")
    
    # I've added double quotes around column aliases to ensure they stay exactly as written
    query = f"""
    SELECT 
        DEGREE_SCHOOL_STD as "degree_school_std",
        COUNT(DISTINCT CASE WHEN DEGREE LIKE '%{degree_interest}%' THEN PROFESSOR_KEY END) AS "no_with_degree",
        COUNT(DISTINCT PROFESSOR_KEY) AS "total_professors",
        ROUND(COUNT(DISTINCT CASE WHEN DEGREE LIKE '%{degree_interest}%' THEN PROFESSOR_KEY END) * 100.0 / COUNT(DISTINCT PROFESSOR_KEY), 2) AS "percentage"
    FROM Biography
    GROUP BY DEGREE_SCHOOL_STD
    HAVING percentage > 0
    ORDER BY percentage DESC;
    """
    df = run_query(query)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.write(f"Schools ranked by % of faculty with: **{degree_interest}**")
        st.dataframe(df)
    with col2:
        # UPDATED: Using lowercase names to match the error message's 'Expected' list
        fig = px.bar(
            df.head(10), 
            x='DEGREE_SCHOOL_STD',  # Matches our forced uppercase
            y='PERCENTAGE',         # Matches our forced uppercase
            title=f"Top 10 Schools: {degree_interest} %"
        )
        st.plotly_chart(fig)

# --- MODULE 3: COURSE DISTRIBUTION ---
elif choice == "Course Distribution":
    st.header("📊 Curriculum Prevalence Dashboard")
    st.markdown("""
        This analysis shows the 'Market Share' of each subject. 
        **Higher percentages** indicate core foundational courses taught at almost every law school, 
        while **lower percentages** indicate niche or specialized legal fields.
    """)
    
    # 1. Fetch the data
    # We use COUNT(DISTINCT SC.SCHOOL) to ensure we are counting unique institutions
    query = """
    SELECT SU.SUBJECT,
    ROUND((COUNT(DISTINCT SC.SCHOOL) * 100.0) /(SELECT COUNT(DISTINCT SCHOOL) FROM SCHOOL), 2) AS PERCENT_OF_SCHOOLS
    FROM SCHOOL SC 
    JOIN SUBJECT SU ON SC.PROFESSOR_KEY = SU.PROFESSOR_KEY
    GROUP BY SU.SUBJECT
    ORDER BY PERCENT_OF_SCHOOLS DESC;
    """
    df = run_query(query)

    if not df.empty:
        # 2. Key Metrics (Top Level)
        total_subjects = len(df)
        most_common = df.iloc[0]['SUBJECT']
        highest_pct = df.iloc[0]['PERCENT_OF_SCHOOLS']

        m1, m2, m3 = st.columns(3)
        m1.metric("Unique Subjects Tracked", total_subjects)
        m2.metric("Most Common Course", most_common)
        m3.metric("Highest Prevalence", f"{highest_pct}%")

        st.divider()

        # 3. Visual Chart: Top 20 Most Prevalent Courses
        st.subheader("🔝 Top 20 Most Widely Offered Courses")
        
        fig = px.bar(
            df.head(20), 
            x='PERCENT_OF_SCHOOLS', 
            y='SUBJECT', 
            orientation='h',
            color='PERCENT_OF_SCHOOLS',
            color_continuous_scale='Viridis',
            labels={'PERCENT_OF_SCHOOLS': 'Percentage of Schools Offering (%)', 'SUBJECT': 'Legal Subject'},
            text_auto=True # Shows the percentage number inside the bar
        )
        
        # Invert axis so 100% is at the top
        fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=600)
        st.plotly_chart(fig, width="stretch")

        # 4. Filterable Search Table
        st.subheader("🔍 Search Full Curriculum List")
        search_term = st.text_input("Filter subjects by name (e.g., 'Tax' or 'Criminal'):")
        
        if search_term:
            filtered_df = df[df['SUBJECT'].str.contains(search_term, case=False, na=False)]
        else:
            filtered_df = df

        st.dataframe(
            filtered_df, 
            column_config={
                "SUBJECT": "Legal Subject",
                "PERCENT_OF_SCHOOLS": st.column_config.ProgressColumn(
                    "Prevalence %",
                    help="Percentage of universities offering this course",
                    format="%.2f%%",
                    min_value=0,
                    max_value=100,
                ),
            },
            width="stretch",
            hide_index=True
        )
    else:
        st.info("No course distribution data available.")

# --- MODULE 4: SCHOOL SUBJECT CATALOG ---
elif choice == "School Subject Catalog":
    st.header("🏫 School Subject Catalog")
    st.markdown("Select a school to see all subjects offered in a condensed, easy-to-read grid.")
    
    # 1. Fetch the list of schools for the dropdown
    schools_df = run_query("SELECT DISTINCT SCHOOL FROM SCHOOL ORDER BY SCHOOL")
    schools_list = schools_df['SCHOOL'].tolist()
    
    selected_school = st.selectbox("Select a School:", schools_list)
    
    # 2. Fetch subjects for that specific school
    query = f"""
    SELECT DISTINCT SU.SUBJECT
    FROM SCHOOL SC 
    JOIN SUBJECT SU ON SC.PROFESSOR_KEY = SU.PROFESSOR_KEY
    WHERE SC.SCHOOL = '{selected_school}'
    ORDER BY SU.SUBJECT;
    """
    df = run_query(query)
    
    if not df.empty:
        st.write(f"### Subjects taught at **{selected_school}**")
        
        # 3. Create a multi-column grid (3 columns) to avoid long scrolling
        subjects = df['SUBJECT'].tolist()
        cols = st.columns(3) # Splits the screen into 3 equal parts
        
        # This loop distributes the subjects evenly across the 3 columns
        for index, subject in enumerate(subjects):
            with cols[index % 3]:
                # Using a 'border=True' container for a clean "Card" look
                with st.container(border=True):
                    st.markdown(f"📖 **{subject}**")
    else:
        st.info("No subject data available for this school.")

# --- MODULE 5: RAW SEARCH ---
elif choice == "Raw Search (James H. Barnett Jr. Style)":
    st.header("👤 Professor Profile View")
    st.markdown("Search for a professor to see their education and teaching history in a clean, resume-style format.")

    # 1. FETCH ALL NAMES FOR THE DROPDOWN
    # This pre-loads the names so the professor can just start typing
    names_df = run_query("SELECT DISTINCT PROFESSOR_KEY FROM Biography ORDER BY PROFESSOR_KEY")
    all_names = names_df['PROFESSOR_KEY'].tolist()

    # 2. AUTOCOMPLETE SEARCH WIDGET
    selected_prof = st.selectbox(
        "Search or Select a Professor:",
        options=all_names,
        # Default to James Barnett if he exists, otherwise pick the first name in the list
        index=all_names.index("James H. Barnett Jr.") if "James H. Barnett Jr." in all_names else 0,
        help="Type a name (e.g., 'Barnett') to filter the list."
    )

    # 3. EXECUTE THE PROFILE QUERY
    query = f"""
    SELECT 
        B.FIRST_NAME, B.MI, B.LAST_NAME, B.RANK, B.BIRTH_YEAR, 
        B.TITLE, B.DEGREE_YEAR, B.DEGREE, B.DEGREE_SCHOOL_STD, 
        SJ.SUBJECT, SJ.EXPERIENCE
    FROM Biography B 
    JOIN subject SJ ON SJ.professor_key = B.professor_key
    WHERE B.professor_key = '{selected_prof}';
    """
    
    df = run_query(query)

    if not df.empty:
        # DATA PROCESSING: Get the static info from the first row
        first_row = df.iloc[0]
        full_name = f"{first_row['FIRST_NAME']} {first_row['MI']} {first_row['LAST_NAME']}".replace("  ", " ")
        
        st.divider()
        
        # HEADER SECTION: Name and Rank
        st.title(f"{full_name}")
        col_hdr1, col_hdr2 = st.columns(2)
        with col_hdr1:
            st.write(f"**Rank:** {first_row['RANK']}")
        with col_hdr2:
            birth = int(first_row['BIRTH_YEAR']) if pd.notnull(first_row['BIRTH_YEAR']) else "N/A"
            st.write(f"**Birth Year:** {birth}")

        st.divider()

        # TWO-COLUMN LAYOUT (EXPERIENCE VS EDUCATION)
        col_main, col_side = st.columns([2, 1])

        with col_main:
            st.subheader("💼 Professional Experience")
            with st.container(border=True):
                st.markdown(f"**Current Title/Appointment:**")
                st.info(first_row['TITLE'])

            st.markdown("#### 📖 Subjects Taught")
            # Drop duplicates to prevent repeating subjects
            teaching_df = df[['SUBJECT', 'EXPERIENCE']].drop_duplicates()
            
            # Create a clean, one-line-per-subject layout
            with st.container(border=True):
                for _, row in teaching_df.iterrows():
                    # This puts everything on one line: Subject - Experience
                    st.markdown(f"• **{row['SUBJECT']}** — *{row['EXPERIENCE']}*")

        with col_side:
            st.subheader("🎓 Education")
            # Get unique degrees and sort by year (newest first)
            edu_df = df[['DEGREE', 'DEGREE_YEAR', 'DEGREE_SCHOOL_STD']].drop_duplicates().sort_values('DEGREE_YEAR', ascending=False)
            
            for _, row in edu_df.iterrows():
                degree_name = str(row['DEGREE']) if pd.notnull(row['DEGREE']) else "Degree N/A"
                year = int(row['DEGREE_YEAR']) if pd.notnull(row['DEGREE_YEAR']) else "Year N/A"
                with st.container(border=True):
                    st.markdown(f"**{degree_name}**")
                    st.write(f"**{row['DEGREE_SCHOOL_STD']}**")
                    st.caption(f"Class of {year}")

        # OPTIONAL: Keep the raw table hidden at the bottom for verification
        st.divider()
        with st.expander("View Raw Database Records (Technical Details)"):
            st.dataframe(df)

    else:
        st.warning("No data found for the selected professor.")