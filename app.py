# app.py
import os
import re
import pandas as pd
import numpy as np
from datetime import datetime
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s:%(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Set page configuration for better aesthetics
st.set_page_config(
    page_title="Patient Dashboard",
    page_icon=":hospital:",
    layout="wide",  # Use the entire screen width
    initial_sidebar_state="expanded",
)

# Apply custom CSS for styling
st.markdown("""
    <style>
        /* Adjust the font sizes */
        h1, h2, h3, h4 {
            color: #2c3e50;
        }
        /* Style the sidebar */
        [data-testid="stSidebar"] {
            background-color: #ecf0f1;
        }
        /* Style the main content area */
        .reportview-container .main .block-container {
            padding-top: 2rem;
        }
        /* Style tables */
        .dataframe th, .dataframe td {
            padding: 0.5rem;
        }
    </style>
""", unsafe_allow_html=True)

# Change the working directory
os.chdir("/Users/laurentelkrief/Desktop/Neuromod/Research/TableaudeBord/")
logging.debug("New working directory: %s", os.getcwd())

# Define data file paths
csv_file = "final_data.csv"

# Function to load data with correct encoding
@st.cache_data
def load_data(csv_file):
    try:
        data = pd.read_csv(csv_file, dtype={'ID': str}, encoding='latin1')
        logging.debug(f"Data loaded successfully from {csv_file}")
        return data
    except Exception as e:
        logging.error(f"Error loading data from {csv_file}: {e}")
        return pd.DataFrame()

# Load data
final_data = load_data(csv_file)
logging.debug("Final Data Columns: %s", final_data.columns.tolist())
logging.debug("Final Data Sample:\n%s", final_data.head())

# MADRS Items Mapping
madrs_items_mapping = {
    1: "Apparent Sadness",
    2: "Reported Sadness",
    3: "Inner Tension",
    4: "Reduced Sleep",
    5: "Reduced Appetite",
    6: "Concentration Difficulties",
    7: "Lassitude",
    8: "Inability to Feel",
    9: "Pessimistic Thoughts",
    10: "Suicidal Thoughts"
}

# PID-5 Dimensions Mapping
pid5_dimensions_mapping = {
    'Negative Affectivity': [8, 9, 10, 11, 15],
    'Detachment': [4, 13, 14, 16, 18],
    'Antagonism': [17, 19, 20, 22, 25],
    'Disinhibition': [1, 2, 3, 5, 6],
    'Psychoticism': [7, 12, 21, 23, 24]
}

# Check for PID-5 and PHQ-9 data availability
has_pid5 = any(col.startswith('pid5_') for col in final_data.columns)
has_phq9 = any(col.startswith('phq9_') for col in final_data.columns)

# Define a safe sort key function for patient IDs
def extract_number(id_str):
    match = re.search(r'\d+', id_str)
    return int(match.group()) if match else float('inf')

# Sidebar layout
with st.sidebar:
    st.title("Patient Dashboard")
    st.markdown("---")
    st.header("Navigation")
    page = st.radio("Go to", ["Patient Dashboard", "Nursing Inputs", "PID-5 Details"])

    st.markdown("---")
    st.header("Select Patient")
    patient_ids = sorted(final_data["ID"].unique(), key=extract_number) if not final_data.empty else []
    selected_patient_id = st.selectbox("Select Patient ID", patient_ids) if patient_ids else None

# Function to load nurse inputs from CSV
def load_nurse_inputs(patient_id):
    try:
        nurse_data = pd.read_csv(csv_file, dtype={'ID': str})
        row = nurse_data[nurse_data["ID"] == patient_id]
        if not row.empty:
            return row.iloc[0][["objectives", "tasks", "comments"]].fillna("")
        else:
            return {"objectives": "", "tasks": "", "comments": ""}
    except Exception as e:
        logging.error(f"Error loading nursing inputs from {csv_file}: {e}")
        return {"objectives": "", "tasks": "", "comments": ""}

# Function to save nurse inputs to CSV
def save_nurse_inputs(patient_id, objectives, tasks, comments):
    try:
        nurse_data = pd.read_csv(csv_file, dtype={'ID': str})
        if patient_id in nurse_data["ID"].values:
            nurse_data.loc[nurse_data["ID"] == patient_id, ["objectives", "tasks", "comments"]] = [objectives, tasks, comments]
        else:
            new_entry = {"ID": patient_id, "objectives": objectives, "tasks": tasks, "comments": comments}
            nurse_data = nurse_data.append(new_entry, ignore_index=True)
        nurse_data.to_csv(csv_file, index=False)
        logging.debug(f"Nursing inputs saved for ID {patient_id}")
        st.success("Nursing inputs saved successfully.")
    except Exception as e:
        logging.error(f"Error saving nursing inputs for ID {patient_id}: {e}")
        st.error("Error saving nursing inputs.")

# Patient Dashboard Page
def patient_dashboard():
    if not selected_patient_id:
        st.warning("No patient selected.")
        return

    patient_data = final_data[final_data["ID"] == selected_patient_id].iloc[0]

    # Patient Information and SMART Objectives
    st.header("Patient Overview")

    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Patient Information")
            st.write(f"**Age:** {patient_data['age']}")
            sex_numeric = patient_data['sexe']
            sex = "Male" if sex_numeric == '1' else "Female" if sex_numeric == '2' else "Other"
            st.write(f"**Sex:** {sex}")
            st.write(f"**Education Years (Baseline):** {patient_data.get('annees_education_bl', 'N/A')}")
            st.write(f"**Income (Baseline):** {patient_data.get('revenu_bl', 'N/A')}")
        with col2:
            st.subheader("SMART Objectives")
            objectives = patient_data.get("objectives", "N/A")
            tasks = patient_data.get("tasks", "N/A")
            comments = patient_data.get("comments", "N/A")
            st.write(f"**Objectives:** {objectives}")
            st.write(f"**Tasks:** {tasks}")
            st.write(f"**Comments:** {comments}")

    st.markdown("---")

    # Demographic and Clinical Data
    st.header("Demographic and Clinical Data")
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Demographic Data")
            demog_cols = ["sexe", "age", "annees_education_bl", "revenu_bl"]
            demog_data = patient_data[demog_cols].rename(index={
                "sexe": "Sex",
                "age": "Age",
                "annees_education_bl": "Education Years (Baseline)",
                "revenu_bl": "Income (Baseline)"
            })
            demog_df = pd.DataFrame(demog_data).T
            demog_df['Sex'] = demog_df['Sex'].apply(lambda x: "Male" if x == '1' else "Female" if x == '2' else "Other")
            st.table(demog_df)
        with col2:
            st.subheader("Clinical Data")
            clin_cols = ["comorbidities", "pregnant", "cigarette_bl", "alcool_bl", "cocaine_bl"]
            clin_data = patient_data[clin_cols].rename(index={
                "comorbidities": "Comorbidities",
                "pregnant": "Pregnant",
                "cigarette_bl": "Cigarettes (Baseline)",
                "alcool_bl": "Alcohol (Baseline)",
                "cocaine_bl": "Cocaine (Baseline)"
            })
            clin_df = pd.DataFrame(clin_data).T
            clin_df['Pregnant'] = clin_df['Pregnant'].map({1: "Yes", 0: "No"})
            st.table(clin_df)

    st.markdown("---")

    # MADRS Scores
    st.header("MADRS Scores")
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Total MADRS Score")
            madrs_total = {
                "Baseline": patient_data.get("madrs_score_bl", 0),
                "Day 30": patient_data.get("madrs_score_fu", 0)
            }
            fig_madrs = px.bar(
                x=list(madrs_total.keys()),
                y=list(madrs_total.values()),
                labels={"x": "Time", "y": "MADRS Score"},
                color=list(madrs_total.keys()),
                color_discrete_sequence=px.colors.qualitative.Plotly,
                title="Total MADRS Score"
            )
            st.plotly_chart(fig_madrs, use_container_width=True)
        with col2:
            st.subheader("MADRS Item Scores")
            madrs_items = patient_data.filter(regex=r"^madrs[_.]\d+[_.](bl|fu)$")
            if madrs_items.empty:
                st.warning("No MADRS item scores found for this patient.")
            else:
                madrs_items_df = madrs_items.to_frame().T
                madrs_long = madrs_items_df.melt(var_name="Item", value_name="Score").dropna()
                madrs_long["Time"] = madrs_long["Item"].str.extract("_(bl|fu)$")[0]
                madrs_long["Time"] = madrs_long["Time"].map({"bl": "Baseline", "fu": "Day 30"})
                madrs_long["Item"] = madrs_long["Item"].str.extract(r"madrs[_.](\d+)_")[0].astype(int)
                madrs_long["Item"] = madrs_long["Item"].map(madrs_items_mapping)
                madrs_long.dropna(subset=["Item"], inplace=True)

                if madrs_long.empty:
                    st.warning("All MADRS item scores are NaN.")
                else:
                    fig = px.bar(
                        madrs_long,
                        x="Item",
                        y="Score",
                        color="Time",
                        barmode="group",
                        title="MADRS Item Scores",
                        template="plotly_white",
                        color_discrete_sequence=px.colors.qualitative.Set2
                    )
                    fig.update_xaxes(tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # PID-5 and PHQ-9 Progression
    st.header("Assessment Scores")
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            if has_pid5:
                st.subheader("PID-5 Scores")
                pid5_columns_bl = []
                pid5_columns_fu = []
                for dimension, items in pid5_dimensions_mapping.items():
                    pid5_columns_bl += [f'pid5_{item}_bl' for item in items]
                    pid5_columns_fu += [f'pid5_{item}_fu' for item in items]

                if not set(pid5_columns_bl + pid5_columns_fu).issubset(final_data.columns):
                    st.warning("Incomplete PID-5 data for this patient.")
                else:
                    dimension_scores_bl = {}
                    dimension_scores_fu = {}
                    for dimension, items in pid5_dimensions_mapping.items():
                        baseline_score = patient_data[[f'pid5_{item}_bl' for item in items]].sum()
                        followup_score = patient_data[[f'pid5_{item}_fu' for item in items]].sum()
                        dimension_scores_bl[dimension] = baseline_score.sum()
                        dimension_scores_fu[dimension] = followup_score.sum()

                    categories = list(pid5_dimensions_mapping.keys())
                    values_bl = list(dimension_scores_bl.values())
                    values_fu = list(dimension_scores_fu.values())

                    categories += [categories[0]]
                    values_bl += [values_bl[0]]
                    values_fu += [values_fu[0]]

                    fig_spider = go.Figure()
                    fig_spider.add_trace(go.Scatterpolar(
                        r=values_bl,
                        theta=categories,
                        fill='toself',
                        name='Baseline',
                        line_color='blue'
                    ))
                    fig_spider.add_trace(go.Scatterpolar(
                        r=values_fu,
                        theta=categories,
                        fill='toself',
                        name='Day 30',
                        line_color='red'
                    ))
                    fig_spider.update_layout(
                        polar=dict(
                            radialaxis=dict(
                                visible=True,
                                range=[0, max(values_bl + values_fu)]
                            )
                        ),
                        showlegend=True,
                        title="PID-5 Dimension Scores",
                        template="plotly_white"
                    )
                    st.plotly_chart(fig_spider, use_container_width=True)
            else:
                st.info("PID-5 data is not available.")
        with col2:
            if has_phq9:
                st.subheader("PHQ-9 Progression")
                phq9_days = [5, 10, 15, 20, 25, 30]
                phq9_scores = {}
                missing_phq9 = False
                for day in phq9_days:
                    item_columns = [f'phq9_day{day}_item{item}' for item in range(1, 10)]
                    if not set(item_columns).issubset(final_data.columns):
                        missing_phq9 = True
                        break
                    phq9_score = patient_data[item_columns].sum()
                    phq9_scores[f'Day {day}'] = phq9_score

                if missing_phq9:
                    st.warning("Incomplete PHQ-9 data for this patient.")
                else:
                    phq9_df = pd.DataFrame(list(phq9_scores.items()), columns=["Day", "Score"])
                    fig_phq9 = px.line(
                        phq9_df,
                        x="Day",
                        y="Score",
                        markers=True,
                        title="PHQ-9 Progression",
                        template="plotly_white",
                        color_discrete_sequence=['#e74c3c']
                    )
                    fig_phq9.update_layout(xaxis_title="Day", yaxis_title="PHQ-9 Score")
                    st.plotly_chart(fig_phq9, use_container_width=True)
            else:
                st.info("PHQ-9 data is not available.")

    st.markdown("---")

    # Nursing Inputs
    st.header("Nursing Inputs")
    with st.form(key='nursing_inputs_form'):
        objectives_input = st.text_area("SMART Objectives", height=100, value=objectives)
        tasks_input = st.text_area("Behavioral Activation Tasks", height=100, value=tasks)
        comments_input = st.text_area("Comments", height=100, value=comments)
        submit_button = st.form_submit_button(label='Save')

        if submit_button:
            save_nurse_inputs(selected_patient_id, objectives_input, tasks_input, comments_input)

    st.markdown("---")

    # Display Saved Nursing Inputs
    st.subheader("Saved Nursing Inputs")
    if objectives or tasks or comments:
        st.write(f"**Objectives:** {objectives if objectives else 'N/A'}")
        st.write(f"**Tasks:** {tasks if tasks else 'N/A'}")
        st.write(f"**Comments:** {comments if comments else 'N/A'}")
    else:
        st.write("No inputs saved.")

# Nursing Inputs Page
def nurse_inputs_page():
    if not selected_patient_id:
        st.warning("No patient selected.")
        return

    st.header("Nursing Inputs")
    nurse_inputs = load_nurse_inputs(selected_patient_id)
    with st.form(key='nursing_inputs_form'):
        objectives_input = st.text_area("SMART Objectives", height=100, value=nurse_inputs.get("objectives", ""))
        tasks_input = st.text_area("Behavioral Activation Tasks", height=100, value=nurse_inputs.get("tasks", ""))
        comments_input = st.text_area("Comments", height=100, value=nurse_inputs.get("comments", ""))
        submit_button = st.form_submit_button(label='Save')

        if submit_button:
            save_nurse_inputs(selected_patient_id, objectives_input, tasks_input, comments_input)

    st.markdown("---")

    # Display Saved Nursing Inputs
    st.subheader("Saved Nursing Inputs")
    if nurse_inputs:
        st.write(f"**Objectives:** {nurse_inputs.get('objectives', 'N/A')}")
        st.write(f"**Tasks:** {nurse_inputs.get('tasks', 'N/A')}")
        st.write(f"**Comments:** {nurse_inputs.get('comments', 'N/A')}")
    else:
        st.write("No inputs saved.")

# PID-5 Details Page
def details_pid5_page():
    if not selected_patient_id:
        st.warning("No patient selected.")
        return

    if not has_pid5:
        st.info("PID-5 data is not available.")
        return

    patient_data = final_data[final_data["ID"] == selected_patient_id].iloc[0]

    pid5_columns = []
    for dimension, items in pid5_dimensions_mapping.items():
        pid5_columns += [f'pid5_{item}_bl' for item in items] + [f'pid5_{item}_fu' for item in items]

    if not set(pid5_columns).issubset(final_data.columns):
        st.warning("Incomplete PID-5 data for this patient.")
        return

    dimension_scores_bl = {}
    dimension_scores_fu = {}
    for dimension, items in pid5_dimensions_mapping.items():
        baseline_score = patient_data[[f'pid5_{item}_bl' for item in items]].sum()
        followup_score = patient_data[[f'pid5_{item}_fu' for item in items]].sum()
        dimension_scores_bl[dimension] = baseline_score.sum()
        dimension_scores_fu[dimension] = followup_score.sum()

    # Prepare data for the table
    table_data = []
    for dimension in pid5_dimensions_mapping.keys():
        table_data.append({
            "Domain": dimension,
            "Total Baseline": dimension_scores_bl[dimension],
            "Total Day 30": dimension_scores_fu[dimension]
        })

    pid5_df = pd.DataFrame(table_data)

    st.subheader("PID-5 Scores by Domain")
    st.table(pid5_df.style.set_properties(**{'text-align': 'center'}))

    # Create Spider Chart
    categories = list(pid5_dimensions_mapping.keys())
    values_bl = list(dimension_scores_bl.values())
    values_fu = list(dimension_scores_fu.values())

    categories += [categories[0]]
    values_bl += [values_bl[0]]
    values_fu += [values_fu[0]]

    fig_spider = go.Figure()
    fig_spider.add_trace(go.Scatterpolar(
        r=values_bl,
        theta=categories,
        fill='toself',
        name='Baseline',
        line_color='blue'
    ))
    fig_spider.add_trace(go.Scatterpolar(
        r=values_fu,
        theta=categories,
        fill='toself',
        name='Day 30',
        line_color='red'
    ))
    fig_spider.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(values_bl + values_fu)]
            )
        ),
        showlegend=True,
        title="PID-5 Dimension Scores",
        template="plotly_white"
    )
    st.plotly_chart(fig_spider, use_container_width=True)

# Main App Logic
if page == "Patient Dashboard":
    patient_dashboard()
elif page == "Nursing Inputs":
    nurse_inputs_page()
elif page == "PID-5 Details":
    details_pid5_page()
