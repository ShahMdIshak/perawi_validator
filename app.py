
import streamlit as st
import pandas as pd
import plotly.express as px
from itertools import tee

# Load dataset
@st.cache_data
def load_data():
    return pd.read_csv("narrators_dataset_v2.csv")

narrators_df = load_data()

st.title("Chronological Sanad Validator")
st.markdown("Check if narrators in a hadith chain lived during overlapping periods.")

# Input: narrator selection
narrator_names = st.multiselect(
    "Select Narrators in Sanad Order (Top = Earliest)",
    options=narrators_df['name_letters'].tolist()
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
            'Narrator A': name_a,
            'Lifespan A': f"{row_a['birth_greg']}–{row_a['death_greg']}",
            'Narrator B': name_b,
            'Lifespan B': f"{row_b['birth_greg']}–{row_b['death_greg']}",
            'Overlap': "✅ Yes" if overlap else "❌ No",
        })

    result_df = pd.DataFrame(results)
    st.dataframe(result_df, use_container_width=True)

    # Optional: plot timeline
    st.subheader("Narrator Lifespans")
    timeline_data = narrators_df[narrators_df['name_letters'].isin(narrator_names)]
    timeline_data = timeline_data.assign(Name=timeline_data['name_letters'])

    fig = px.timeline(
        timeline_data,
        x_start="birth_greg",
        x_end="death_greg",
        y="Name",
        title="Narrator Lifespans Timeline",
        labels={"Name": "Narrator"}
    )
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)

elif len(narrator_names) == 1:
    st.info("Select at least two narrators to check overlap.")
else:
    st.info("Use the selector above to choose narrators in chain order.")
