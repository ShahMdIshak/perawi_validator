import streamlit as st
import pandas as pd
from difflib import get_close_matches
from itertools import tee

# Load dataset
def load_data():
    df = pd.read_csv("narrators_dataset_v2.csv")
    df = df[(df['birth_greg'] > 0) & (df['death_greg'] > 0)]  # Filter invalid
    df = df[df['birth_greg'] != df['death_greg']]  # Exclude same-year narrators
    df.columns = df.columns.str.strip().str.lower()
    return df

narrators_df = st.cache_data(load_data)()

st.set_page_config(layout="wide")
st.title("Chronological Sanad Validator")
st.markdown("Check if narrators in a hadith chain lived during overlapping periods.")

# Fuzzy search helper
def fuzzy_search(query, choices, cutoff=0.7, n=8):
    q = query.lower()
    lowered = [c.lower() for c in choices]
    matches = get_close_matches(q, lowered, n=n, cutoff=cutoff)
    return [choices[i] for i, c in enumerate(lowered) if c in matches]

# Initialize session state
if 'narrator_chain' not in st.session_state:
    st.session_state.narrator_chain = []
if 'delete_index' not in st.session_state:
    st.session_state.delete_index = None

st.subheader("Step 1: Select Narrators One by One")
# Controlled text input with key for reset
name_input = st.text_input("Type a narrator's name (partial allowed):", key="name_input")

# Show matches and add
if name_input:
    options = narrators_df['name_letters'].tolist()
    matches = fuzzy_search(name_input, options)
    if matches:
        selected = st.selectbox("Select from closest matches:", matches, key="match_box")
        if st.button("Add Narrator", key="add_btn"):
            if selected not in st.session_state.narrator_chain:
                st.session_state.narrator_chain.append(selected)
            st.session_state.name_input = ""  # Reset input

# Display selected narrators with remove button
if st.session_state.narrator_chain:
    st.markdown("**Selected Chain (Earliest to Latest):**")
    for idx, name in enumerate(st.session_state.narrator_chain):
        row = narrators_df[narrators_df['name_letters'] == name].iloc[0]
        arabic = row.get('name_arabic', '')
        grade = row.get('grade', '') if pd.notna(row.get('grade', '')) else "—"
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            st.write(f"{idx+1}. {name} ({arabic}) — Grade: {grade}")
        with col2:
            if st.button("❌", key=f"remove_{idx}"):
                st.session_state.delete_index = idx
                break
    if st.session_state.delete_index is not None:
        st.session_state.narrator_chain.pop(st.session_state.delete_index)
        st.session_state.delete_index = None

    if st.button("Reset Chain", key="reset_btn"):
        st.session_state.narrator_chain = []

# Lifespan overlap logic
def lifespan_overlap(b1, d1, b2, d2):
    return max(0, min(d1, d2) - max(b1, b2))

# Output table
chain = st.session_state.narrator_chain
if len(chain) >= 2:
    st.subheader("Lifespan Overlap Check")
    rows = []
    for a, b in tee(chain): pass  # placeholder
    # correct pairwise
    a_iter, b_iter = tee(chain)
    next(b_iter, None)
    for a, b in zip(a_iter, b_iter):
        ra = narrators_df[narrators_df['name_letters'] == a].iloc[0]
        rb = narrators_df[narrators_df['name_letters'] == b].iloc[0]
        overlap = lifespan_overlap(ra['birth_greg'], ra['death_greg'], rb['birth_greg'], rb['death_greg'])
        status = "✅ Strong" if overlap >= 10 else "🟡 Weak" if overlap >=1 else "❌ None"
        rows.append({
            'Narrator A': f"{a} ({ra.get('name_arabic','')})",
            'Lifespan A': f"{ra['birth_greg']}–{ra['death_greg']}",
            'Narrator B': f"{b} ({rb.get('name_arabic','')})",
            'Lifespan B': f"{rb['birth_greg']}–{rb['death_greg']}",
            'Overlap Strength': status
        })
    df_res = pd.DataFrame(rows)
    st.dataframe(df_res, use_container_width=True)
elif len(chain) == 1:
    st.info("Select at least two narrators to check overlap.")
else:
    st.info("Start by typing a narrator name and selecting from suggestions.")
