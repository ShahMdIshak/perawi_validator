import streamlit as st
import pandas as pd
import plotly.express as px
from itertools import tee

# Load dataset
@st.cache_data
def load_data():
    return pd.read_csv("narrators_dataset_v2.csv")

narrators_df = load_data()

st.set_page_config(layout="wide")
st.title("Chronological Sanad Validator")
st.markdown("Check if narrators in a hadith chain lived during overlapping periods.")

# Sort names alphabetically for dropdown
sorted_names = narrators_df['name_letters'].sort_values().tolist()

# Input: searchable narrator selection
narrator_names = st.multiselect(
    "Select Narrators in Sanad Order (Top = Earliest)",
    options=sorted_names,
    placeholder="Start typing a narrator's name..."
)

# Helper to check overlap between two lifespans
def lifespans_overlap(birth_a, death_a, birth_b, death_b):
    return not (death_a < birth_b or death_b < birth_a)

# Helper to pair narrators in order
def pairwise(iterable):
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)

# Output table
if len(narrator_names) >= 2:
    st.subheader("Lifespan Overlap Check")
    results = []

    for name_a, name_b in pairwise(narrator_names):
        row_a = narrators_df[narrators_df['name_letters'] == name_a].iloc[0]
        row_b = narrators_df[narrators_df['name_letters'] == name_b].iloc[0]

        overlap = lifespans_overlap(row_a['birth_greg'], row_a['death_greg'],
                                    row_b['birth_greg'], row_b['death_greg'])

        results.append({
            'Narrator A': f"{name_a}",
            'Lifespan A': f"{row_a['birth_greg']}–{row_a['death_greg']}",
            'Narrator B': f"{name_b}",
            'Lifespan B': f"{row_b['birth_greg']}–{row_b['death_greg']}",
            'Overlap': "✅ Yes" if overlap else "❌ No",
        })

    result_df = pd.DataFrame(results)
    st.dataframe(result_df, use_container_width=True)

    # Timeline section
    st.subheader("Narrator Lifespans")
    timeline_data = narrators_df[narrators_df['name_letters'].isin(narrator_names)].copy()
    timeline_data = timeline_data.assign(Name=timeline_data['name_letters'])

    # Optional: include generation level if available
    if 'grade' in narrators_df.columns:
        timeline_data['Name'] = timeline_data.apply(
            lambda row: f"{row['name_letters']} ({row['grade']})" if pd.notna(row['grade']) else row['name_letters'],
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
    st.info("Use the selector above to choose narrators in chain order.")
