import streamlit as st
import pandas as pd
import plotly.express as px
from itertools import tee
from difflib import get_close_matches

# Load dataset
@st.cache_data
def load_data():
    return pd.read_csv("narrators_dataset_v2.csv")

narrators_df = load_data()

st.set_page_config(layout="wide")
st.title("Chronological Sanad Validator")
st.markdown("Check if narrators in a hadith chain lived during overlapping periods.")

# Fuzzy search helper
def fuzzy_search(name, choices, cutoff=0.6):
    return get_close_matches(name, choices, n=5, cutoff=cutoff)

# Input: fuzzy search for narrator names
st.subheader("Step 1: Select Narrators One by One")
if "narrator_chain" not in st.session_state:
    st.session_state.narrator_chain = []

name_input = st.text_input("Type a narrator's name (partial allowed):")

selected_match = None
if name_input:
    matches = fuzzy_search(name_input, narrators_df['name_letters'].tolist())
    if matches:
        selected_match = st.selectbox("Select from closest matches:", matches)
        if selected_match and st.button("Add Narrator"):
            if selected_match not in st.session_state.narrator_chain:
                st.session_state.narrator_chain.append(selected_match)

# Display selected narrators
if st.session_state.narrator_chain:
    st.markdown("**Selected Chain (Earliest to Latest):**")
    for idx, name in enumerate(st.session_state.narrator_chain, start=1):
        arabic = narrators_df[narrators_df['name_letters'] == name]['name_arabic'].values[0]
        st.write(f"{idx}. {name} ({arabic})")

    if st.button("Reset Chain"):
        st.session_state.narrator_chain = []

# Helper to check overlap between two lifespans
def lifespans_overlap(birth_a, death_a, birth_b, death_b):
    return not (death_a < birth_b or death_b < birth_a)

# Helper to pair narrators in order
def pairwise(iterable):
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)

# Output table
narrator_names = st.session_state.narrator_chain
if len(narrator_names) >= 2:
    st.subheader("Lifespan Overlap Check")
    results = []

    for name_a, name_b in pairwise(narrator_names):
        row_a = narrators_df[narrators_df['name_letters'] == name_a].iloc[0]
        row_b = narrators_df[narrators_df['name_letters'] == name_b].iloc[0]

        overlap = lifespans_overlap(row_a['birth_greg'], row_a['death_greg'],
                                    row_b['birth_greg'], row_b['death_greg'])

        results.append({
            'Narrator A': f"{name_a} ({row_a['name_arabic']})",
            'Lifespan A': f"{row_a['birth_greg']}–{row_a['death_greg']}",
            'Narrator B': f"{name_b} ({row_b['name_arabic']})",
            'Lifespan B': f"{row_b['birth_greg']}–{row_b['death_greg']}",
            'Overlap': "✅ Yes" if overlap else "❌ No",
        })

    result_df = pd.DataFrame(results)
    st.dataframe(result_df, use_container_width=True)

    # Timeline
    st.subheader("Narrator Lifespans Timeline")
    timeline_data = narrators_df[narrators_df['name_letters'].isin(narrator_names)].copy()
    timeline_data = timeline_data.assign(Name=timeline_data['name_letters'])

    # Show English + Arabic name + grade
    if 'grade' in narrators_df.columns:
        timeline_data['Name'] = timeline_data.apply(
            lambda row: f"{row['name_letters']}\n{row['name_arabic']} ({row['grade']})" if pd.notna(row['grade']) else f"{row['name_letters']}\n{row['name_arabic']}",
            axis=1
        )

    fig = px.timeline(
        timeline_data,
        x_start="birth_greg",
        x_end="death_greg",
        y="Name",
        color="Name",
        labels={"Name": "Narrator"},
        height=500
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)

elif len(narrator_names) == 1:
    st.info("Select at least two narrators to check overlap.")
else:
    st.info("Start by typing a narrator name and selecting from suggestions.")
