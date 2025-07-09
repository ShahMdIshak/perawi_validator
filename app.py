import streamlit as st
import pandas as pd
from difflib import get_close_matches
from itertools import tee

# Load and prepare dataset
def load_data():
    df = pd.read_csv("narrators_dataset_v2.csv")
    # valid lifespans
    df = df[(df['birth_greg'] > 0) & (df['death_greg'] > 0)]
    # exclude narrators whose birth and death years are the same
    df = df[df['birth_greg'] != df['death_greg']]
    # normalize column names
    df.columns = df.columns.str.strip().str.lower()
    return df

# Cache data
narrators_df = st.cache_data(load_data)()

# App layout
st.set_page_config(layout="wide")
st.title("Chronological Sanad Validator")
st.markdown("Check if narrators in a hadith chain lived during overlapping periods.")

# Search helper: substring first, then fuzzy fallback
def search_narrators(query, choices, cutoff=0.7, n=8):
    q = query.lower().strip()
    # substring match
    substr = [c for c in choices if q in c.lower()]
    if substr:
        return substr[:n]
    # fuzzy fallback
    lowered = [c.lower() for c in choices]
    fuzzy = get_close_matches(q, lowered, n=n, cutoff=cutoff)
    return [choices[i] for i, lc in enumerate(lowered) if lc in fuzzy]

# Callback functions for removal and reset
def remove_narrator(idx):
    chain = st.session_state.narrator_chain
    if 0 <= idx < len(chain):
        chain.pop(idx)

def reset_chain():
    st.session_state.narrator_chain = []

# Initialize session state
if 'narrator_chain' not in st.session_state:
    st.session_state.narrator_chain = []

# Step 1: Add narrators via form
st.subheader("Step 1: Add Narrator to Chain")
with st.form(key="nar_form", clear_on_submit=True):
    name_input = st.text_input("Type a narrator's name (partial allowed):")
    options = narrators_df['name_letters'].tolist()
    matches = search_narrators(name_input, options) if name_input else []
    selected = st.selectbox("Select a narrator:", matches) if matches else None
    submitted = st.form_submit_button("Add Narrator")
    if submitted and selected:
        if selected not in st.session_state.narrator_chain:
            st.session_state.narrator_chain.append(selected)

# Display selected chain with removal buttons
if st.session_state.narrator_chain:
    st.markdown("**Selected Chain (Earliest to Latest):**")
    for idx, name in enumerate(st.session_state.narrator_chain):
        row = narrators_df[narrators_df['name_letters'] == name].iloc[0]
        arabic = row.get('name_arabic', '')
        grade = row.get('grade', '—') if pd.notna(row.get('grade', None)) else '—'
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            st.write(f"{idx+1}. {name} ({arabic}) — Grade: {grade}")
        with col2:
            st.button("❌ Remove", key=f"remove_{idx}", on_click=remove_narrator, args=(idx,))
    # Reset chain button
    st.button("Reset Chain", key="reset_chain", on_click=reset_chain)

# Step 2: Compute and display overlap
chain = st.session_state.narrator_chain
if len(chain) >= 2:
    st.subheader("Lifespan Overlap Check")
    rows = []
    a_iter, b_iter = tee(chain)
    next(b_iter, None)
    for a, b in zip(a_iter, b_iter):
        ra = narrators_df[narrators_df['name_letters'] == a].iloc[0]
        rb = narrators_df[narrators_df['name_letters'] == b].iloc[0]
        overlap = max(0, min(ra['death_greg'], rb['death_greg']) - max(ra['birth_greg'], rb['birth_greg']))
        strength = ("✅ Strong" if overlap >= 10 else "🟡 Weak" if overlap >= 1 else "❌ None")
        rows.append({
            'Narrator A': f"{a} ({ra.get('name_arabic','')})",
            'Lifespan A': f"{ra['birth_greg']}–{ra['death_greg']}",
            'Narrator B': f"{b} ({rb.get('name_arabic','')})",
            'Lifespan B': f"{rb['birth_greg']}–{rb['death_greg']}",
            'Overlap Strength': strength
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
elif len(chain) == 1:
    st.info("Select at least two narrators to see overlap.")
else:
    st.info("Add narrators above to build your chain.")
