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

# Définir une palette de couleurs pastel pour les graphiques
PASTEL_COLORS = px.colors.qualitative.Pastel

# Set page configuration for better aesthetics
st.set_page_config(
    page_title="Tableau de Bord des Patients",
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

# Define data file paths
csv_file = "final_data.csv"

# Function to load data with correct encoding
@st.cache_data
def load_data(csv_file):
    try:
        data = pd.read_csv(csv_file, dtype={'ID': str}, encoding='utf-8')  # Changement d'encodage à 'utf-8'
        logging.debug(f"Données chargées avec succès depuis {csv_file}")
        return data
    except Exception as e:
        logging.error(f"Erreur lors du chargement des données depuis {csv_file}: {e}")
        return pd.DataFrame()

# Load data
final_data = load_data(csv_file)
logging.debug("Colonnes des données finales: %s", final_data.columns.tolist())
logging.debug("Échantillon des données finales:\n%s", final_data.head())

# MADRS Items Mapping (en français)
madrs_items_mapping = {
    1: "Tristesse Apparente",
    2: "Tristesse Signalée",
    3: "Tension Intérieure",
    4: "Sommeil Réduit",
    5: "Appétit Réduit",
    6: "Difficultés de Concentration",
    7: "Lassitude",
    8: "Incapacité à Ressentir",
    9: "Pensées Pessimistes",
    10: "Pensées Suicidaires"
}

# PID-5 Dimensions Mapping (en français)
pid5_dimensions_mapping = {
    'Affect Négatif': [8, 9, 10, 11, 15],
    'Détachement': [4, 13, 14, 16, 18],
    'Antagonisme': [17, 19, 20, 22, 25],
    'Désinhibition': [1, 2, 3, 5, 6],
    'Psychoticisme': [7, 12, 21, 23, 24]
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
    st.title("Tableau de Bord des Patients")
    st.markdown("---")
    st.header("Navigation")
    page = st.radio("Aller à", ["Tableau de Bord du Patient", "Entrées Infirmières", "Détails PID-5"])

    st.markdown("---")
    st.header("Sélectionner un Patient")
    patient_ids = sorted(final_data["ID"].unique(), key=extract_number) if not final_data.empty else []
    selected_patient_id = st.selectbox("Sélectionner l'ID du Patient", patient_ids) if patient_ids else None

# Function to load nurse inputs from CSV
def load_nurse_inputs(patient_id):
    try:
        nurse_data = pd.read_csv(csv_file, dtype={'ID': str}, encoding='utf-8')  # Changement d'encodage
        row = nurse_data[nurse_data["ID"] == patient_id]
        if not row.empty:
            return row.iloc[0][["objectives", "tasks", "comments"]].fillna("")
        else:
            return {"objectives": "", "tasks": "", "comments": ""}
    except Exception as e:
        logging.error(f"Erreur lors du chargement des entrées infirmières depuis {csv_file}: {e}")
        return {"objectives": "", "tasks": "", "comments": ""}

# Function to save nurse inputs to CSV
def save_nurse_inputs(patient_id, objectives, tasks, comments):
    try:
        nurse_data = pd.read_csv(csv_file, dtype={'ID': str}, encoding='utf-8')  # Changement d'encodage
        if patient_id in nurse_data["ID"].values:
            nurse_data.loc[nurse_data["ID"] == patient_id, ["objectives", "tasks", "comments"]] = [objectives, tasks, comments]
        else:
            new_entry = {"ID": patient_id, "objectives": objectives, "tasks": tasks, "comments": comments}
            nurse_data = nurse_data.append(new_entry, ignore_index=True)
        nurse_data.to_csv(csv_file, index=False, encoding='utf-8')  # Changement d'encodage
        logging.debug(f"Entrées infirmières sauvegardées pour l'ID {patient_id}")
        st.success("Entrées infirmières sauvegardées avec succès.")
    except Exception as e:
        logging.error(f"Erreur lors de la sauvegarde des entrées infirmières pour l'ID {patient_id}: {e}")
        st.error("Erreur lors de la sauvegarde des entrées infirmières.")

# Patient Dashboard Page
def patient_dashboard():
    if not selected_patient_id:
        st.warning("Aucun patient sélectionné.")
        return

    patient_data = final_data[final_data["ID"] == selected_patient_id].iloc[0]

    # Patient Information and SMART Objectives
    st.header("Aperçu du Patient")

    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Informations du Patient")
            st.write(f"**Âge :** {patient_data['age']}")
            sex_code = patient_data['sexe']
            sex_mapping = {'H': 'Homme', 'F': 'Femme', 'Autre': 'Autre'}
            sex = sex_mapping.get(sex_code, "N/A")
            st.write(f"**Sexe :** {sex}")
            annees_education = patient_data.get('annees_education_bl', 'N/A')
            st.write(f"**Années d'éducation (Baseline) :** {annees_education}")
            revenu_bl = patient_data.get('revenu_bl', 'N/A')
            revenu_formate = f"${revenu_bl}" if pd.notna(revenu_bl) and revenu_bl != 'N/A' else 'N/A'
            st.write(f"**Revenu (Baseline) :** {revenu_formate}")
        with col2:
            st.subheader("Objectifs SMART")
            objectives = patient_data.get("objectives", "N/A")
            tasks = patient_data.get("tasks", "N/A")
            comments = patient_data.get("comments", "N/A")
            st.write(f"**Objectifs :** {objectives}")
            st.write(f"**Tâches :** {tasks}")
            st.write(f"**Commentaires :** {comments}")

    st.markdown("---")

    # Demographic and Clinical Data
    st.header("Données Démographiques et Cliniques")
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Données Démographiques")
            demog_labels = ["Sexe", "Âge", "Années d'éducation (Baseline)", "Revenu (Baseline)"]
            demog_values = [
                sex,  # Utilise le sexe mappé précédemment
                patient_data['age'],
                patient_data.get('annees_education_bl', 'N/A'),
                revenu_formate
            ]
            demog_df = pd.DataFrame({
                "Paramètre": demog_labels,
                "Valeur": demog_values
            })
            st.table(demog_df)
        with col2:
            st.subheader("Données Cliniques")
            clin_labels = ["Comorbidités", "Enceinte", "Cigarettes (Baseline)", "Alcool (Baseline)", "Cocaïne (Baseline)"]
            # Gestion de la colonne "pregnant"
            pregnant_val = patient_data.get('pregnant', 'N/A')
            if pregnant_val in ["Oui", "Non"]:
                pregnant_display = pregnant_val
            else:
                pregnant_display = "N/A"
            clin_values = [
                patient_data.get('comorbidities', 'N/A'),
                pregnant_display,
                patient_data.get('cigarette_bl', 'N/A'),
                patient_data.get('alcool_bl', 'N/A'),
                patient_data.get('cocaine_bl', 'N/A')
            ]
            clin_df = pd.DataFrame({
                "Paramètre": clin_labels,
                "Valeur": clin_values
            })
            st.table(clin_df)

    st.markdown("---")

    # MADRS Scores
    st.header("Scores MADRS")
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Score Total MADRS")
            madrs_total = {
                "Baseline": patient_data.get("madrs_score_bl", 0),
                "Jour 30": patient_data.get("madrs_score_fu", 0)
            }
            fig_madrs = px.bar(
                x=list(madrs_total.keys()),
                y=list(madrs_total.values()),
                labels={"x": "Temps", "y": "Score MADRS"},
                color=list(madrs_total.keys()),
                color_discrete_sequence=PASTEL_COLORS,
                title="Score Total MADRS"
            )
            st.plotly_chart(fig_madrs, use_container_width=True)
        with col2:
            st.subheader("Scores par Item MADRS")
            madrs_items = patient_data.filter(regex=r"^madrs[_.]\d+[_.](bl|fu)$")
            if madrs_items.empty:
                st.warning("Aucun score par item MADRS trouvé pour ce patient.")
            else:
                madrs_items_df = madrs_items.to_frame().T
                madrs_long = madrs_items_df.melt(var_name="Item", value_name="Score").dropna()
                madrs_long["Temps"] = madrs_long["Item"].str.extract("_(bl|fu)$")[0]
                madrs_long["Temps"] = madrs_long["Temps"].map({"bl": "Baseline", "fu": "Jour 30"})
                madrs_long["Item"] = madrs_long["Item"].str.extract(r"madrs[_.](\d+)_")[0].astype(int)
                madrs_long["Item"] = madrs_long["Item"].map(madrs_items_mapping)
                madrs_long.dropna(subset=["Item"], inplace=True)

                if madrs_long.empty:
                    st.warning("Tous les scores par item MADRS sont NaN.")
                else:
                    fig = px.bar(
                        madrs_long,
                        x="Item",
                        y="Score",
                        color="Temps",
                        barmode="group",
                        title="Scores par Item MADRS",
                        template="plotly_white",
                        color_discrete_sequence=PASTEL_COLORS
                    )
                    fig.update_xaxes(tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # PID-5 and PHQ-9 Progression
    st.header("Scores d'Évaluation")
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            if has_pid5:
                st.subheader("Scores PID-5")
                pid5_columns_bl = []
                pid5_columns_fu = []
                for dimension, items in pid5_dimensions_mapping.items():
                    pid5_columns_bl += [f'pid5_{item}_bl' for item in items]
                    pid5_columns_fu += [f'pid5_{item}_fu' for item in items]

                if not set(pid5_columns_bl + pid5_columns_fu).issubset(final_data.columns):
                    st.warning("Données PID-5 incomplètes pour ce patient.")
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
                        line_color=PASTEL_COLORS[0]
                    ))
                    fig_spider.add_trace(go.Scatterpolar(
                        r=values_fu,
                        theta=categories,
                        fill='toself',
                        name='Jour 30',
                        line_color=PASTEL_COLORS[1]
                    ))
                    fig_spider.update_layout(
                        polar=dict(
                            radialaxis=dict(
                                visible=False  # Suppression des étiquettes et ticks de l'axe radial
                            )
                        ),
                        showlegend=True,
                        title="Scores par Dimension PID-5",
                        template="plotly_white"
                    )
                    st.plotly_chart(fig_spider, use_container_width=True)
            else:
                st.info("Les données PID-5 ne sont pas disponibles.")
        with col2:
            if has_phq9:
                st.subheader("Progression PHQ-9")
                phq9_days = [5, 10, 15, 20, 25, 30]
                phq9_scores = {}
                missing_phq9 = False
                for day in phq9_days:
                    item_columns = [f'phq9_day{day}_item{item}' for item in range(1, 10)]
                    if not set(item_columns).issubset(final_data.columns):
                        missing_phq9 = True
                        break
                    phq9_score = patient_data[item_columns].sum()
                    phq9_scores[f'Jour {day}'] = phq9_score

                if missing_phq9:
                    st.warning("Données PHQ-9 incomplètes pour ce patient.")
                else:
                    phq9_df = pd.DataFrame(list(phq9_scores.items()), columns=["Jour", "Score"])
                    fig_phq9 = px.line(
                        phq9_df,
                        x="Jour",
                        y="Score",
                        markers=True,
                        title="Progression PHQ-9",
                        template="plotly_white",
                        color_discrete_sequence=[PASTEL_COLORS[2]]  # Utiliser une couleur pastel différente
                    )
                    fig_phq9.update_layout(xaxis_title="Jour", yaxis_title="Score PHQ-9")
                    st.plotly_chart(fig_phq9, use_container_width=True)
            else:
                st.info("Les données PHQ-9 ne sont pas disponibles.")

    st.markdown("---")

    # Nursing Inputs
    st.header("Entrées Infirmières")
    with st.form(key='nursing_inputs_form'):
        objectives_input = st.text_area("Objectifs SMART", height=100, value=objectives)
        tasks_input = st.text_area("Tâches d'Activation Comportementale", height=100, value=tasks)
        comments_input = st.text_area("Commentaires", height=100, value=comments)
        submit_button = st.form_submit_button(label='Sauvegarder')

        if submit_button:
            save_nurse_inputs(selected_patient_id, objectives_input, tasks_input, comments_input)

    st.markdown("---")

    # Display Saved Nursing Inputs
    st.subheader("Entrées Infirmières Sauvegardées")
    if objectives or tasks or comments:
        st.write(f"**Objectifs :** {objectives if objectives else 'N/A'}")
        st.write(f"**Tâches :** {tasks if tasks else 'N/A'}")
        st.write(f"**Commentaires :** {comments if comments else 'N/A'}")
    else:
        st.write("Aucune entrée sauvegardée.")

# Nursing Inputs Page
def nurse_inputs_page():
    if not selected_patient_id:
        st.warning("Aucun patient sélectionné.")
        return

    st.header("Entrées Infirmières")
    nurse_inputs = load_nurse_inputs(selected_patient_id)
    with st.form(key='nursing_inputs_form'):
        objectives_input = st.text_area("Objectifs SMART", height=100, value=nurse_inputs.get("objectives", ""))
        tasks_input = st.text_area("Tâches d'Activation Comportementale", height=100, value=nurse_inputs.get("tasks", ""))
        comments_input = st.text_area("Commentaires", height=100, value=nurse_inputs.get("comments", ""))
        submit_button = st.form_submit_button(label='Sauvegarder')

        if submit_button:
            save_nurse_inputs(selected_patient_id, objectives_input, tasks_input, comments_input)

    st.markdown("---")

    # Display Saved Nursing Inputs
    st.subheader("Entrées Infirmières Sauvegardées")
    if nurse_inputs:
        st.write(f"**Objectifs :** {nurse_inputs.get('objectives', 'N/A')}")
        st.write(f"**Tâches :** {nurse_inputs.get('tasks', 'N/A')}")
        st.write(f"**Commentaires :** {nurse_inputs.get('comments', 'N/A')}")
    else:
        st.write("Aucune entrée sauvegardée.")

# PID-5 Details Page
def details_pid5_page():
    if not selected_patient_id:
        st.warning("Aucun patient sélectionné.")
        return

    if not has_pid5:
        st.info("Les données PID-5 ne sont pas disponibles.")
        return

    patient_data = final_data[final_data["ID"] == selected_patient_id].iloc[0]

    pid5_columns = []
    for dimension, items in pid5_dimensions_mapping.items():
        pid5_columns += [f'pid5_{item}_bl' for item in items] + [f'pid5_{item}_fu' for item in items]

    if not set(pid5_columns).issubset(final_data.columns):
        st.warning("Données PID-5 incomplètes pour ce patient.")
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
            "Domaine": dimension,
            "Total Baseline": dimension_scores_bl[dimension],
            "Total Jour 30": dimension_scores_fu[dimension]
        })

    pid5_df = pd.DataFrame(table_data)

    st.subheader("Scores PID-5 par Domaine")
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
        line_color=PASTEL_COLORS[0]
    ))
    fig_spider.add_trace(go.Scatterpolar(
        r=values_fu,
        theta=categories,
        fill='toself',
        name='Jour 30',
        line_color=PASTEL_COLORS[1]
    ))
    fig_spider.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=False  # Suppression des étiquettes et ticks de l'axe radial
            )
        ),
        showlegend=True,
        title="Scores par Dimension PID-5",
        template="plotly_white"
    )
    st.plotly_chart(fig_spider, use_container_width=True)

# Main App Logic
if page == "Tableau de Bord du Patient":
    patient_dashboard()
elif page == "Entrées Infirmières":
    nurse_inputs_page()
elif page == "Détails PID-5":
    details_pid5_page()
