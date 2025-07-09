import streamlit as st
import pandas as pd
from difflib import get_close_matches
from itertools import tee

# Load dataset
@st.cache_data
def load_data():
    df = pd.read_csv("narrators_dataset_v2.csv")
    df = df[(df['birth_greg'] > 0) & (df['death_greg'] > 0)]  # Filter out invalid records
    df = df[df['birth_greg'] != df['death_greg']]  # Exclude narrators with same birth and death year
    df.columns = df.columns.str.strip().str.lower()  # Normalize column names
    return df

narrators_df = load_data()

st.set_page_config(layout="wide")
st.title("Chronological Sanad Validator")
st.markdown("Check if narrators in a hadith chain lived during overlapping periods.")

# Fuzzy search helper (lowercased for broader match)
def fuzzy_search(name, choices, cutoff=0.8):
    name = name.lower()
    choices = [c.lower() for c in choices]
    matches = get_close_matches(name, choices, n=8, cutoff=cutoff)
    # Map matches back to original case-sensitive names
    original = narrators_df['name_letters'].tolist()
    return [o for o in original if o.lower() in matches]

# Input: fuzzy search for narrator names
st.subheader("Step 1: Select Narrators One by One")
if "narrator_chain" not in st.session_state:
    st.session_state.narrator_chain = []
if "delete_index" not in st.session_state:
    st.session_state.delete_index = None

name_input = st.text_input("Type a narrator's name (partial allowed):")

selected_match = None
if name_input:
    matches = fuzzy_search(name_input, narrators_df['name_letters'].tolist())
    if matches:
        # Auto-add if exactly one match
        if len(matches) == 1:
            selected_match = matches[0]
            if selected_match not in st.session_state.narrator_chain:
                st.session_state.narrator_chain.append(selected_match)
            name_input = ""
        else:
            selected_match = st.selectbox("Select from closest matches:", matches)
            if selected_match and st.button("Add Narrator"):
                if selected_match not in st.session_state.narrator_chain:
                    st.session_state.narrator_chain.append(selected_match)

# Display selected narrators
if st.session_state.narrator_chain:
    st.markdown("**Selected Chain (Earliest to Latest):**")
    for idx, name in enumerate(st.session_state.narrator_chain):
        row = narrators_df[narrators_df['name_letters'] == name].iloc[0]
        arabic = row['name_arabic'] if 'name_arabic' in row else ""
        grade = row['grade'] if 'grade' in row and pd.notna(row['grade']) and str(row['grade']).strip() else "—"
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            st.write(f"{idx+1}. {name} ({arabic}) — Grade: {grade}")
        with col2:
            if st.button("❌", key=f"remove_{idx}"):
                st.session_state.delete_index = idx

    if st.session_state.delete_index is not None:
        st.session_state.narrator_chain.pop(st.session_state.delete_index)
        st.session_state.delete_index = None

    if st.button("Reset Chain"):
        st.session_state.narrator_chain = []

# Helper to check overlap strength
def lifespans_overlap(birth_a, death_a, birth_b, death_b):
    latest_start = max(birth_a, birth_b)
    earliest_end = min(death_a, death_b)
    return max(0, earliest_end - latest_start)

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

        overlap_years = lifespans_overlap(row_a['birth_greg'], row_a['death_greg'],
                                          row_b['birth_greg'], row_b['death_greg'])

        strength = (
            "✅ Strong" if overlap_years >= 10 else
            "🟡 Weak" if 1 <= overlap_years < 10 else
            "❌ None"
        )

        results.append({
            'Narrator A': f"{name_a} ({row_a['name_arabic']})",
            'Lifespan A': f"{row_a['birth_greg']}–{row_a['death_greg']}",
            'Narrator B': f"{name_b} ({row_b['name_arabic']})",
            'Lifespan B': f"{row_b['birth_greg']}–{row_b['death_greg']}",
            'Overlap Strength': strength
        })

    result_df = pd.DataFrame(results)
    st.dataframe(result_df, use_container_width=True)

elif len(narrator_names) == 1:
    st.info("Select at least two narrators to check overlap.")
else:
    st.info("Start by typing a narrator name and selecting from suggestions.")
