import streamlit as st
import pandas as pd
from difflib import get_close_matches
from itertools import tee

# Load and prepare dataset
def load_data():
    df = pd.read_csv("narrators_dataset_v2.csv")
    df = df[(df['birth_greg'] > 0) & (df['death_greg'] > 0)]
    df = df[df['birth_greg'] != df['death_greg']]
    df.columns = df.columns.str.strip().str.lower()
    return df

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

# State initialization
if 'narrator_chain' not in st.session_state:
    st.session_state.narrator_chain = []
if 'matches' not in st.session_state:
    st.session_state.matches = []
if 'selected' not in st.session_state:
    st.session_state.selected = None

# Callback to update matches when input changes
def update_matches():
    query = st.session_state.input
    if query:
        st.session_state.matches = search_narrators(query, narrators_df['name_letters'].tolist())
    else:
        st.session_state.matches = []

# Callback to add narrator and clear input
def add_narrator():
    sel = st.session_state.selected
    if sel and sel not in st.session_state.narrator_chain:
        st.session_state.narrator_chain.append(sel)
    # Clear input and matches
    st.session_state.input = ''
    st.session_state.matches = []
    st.session_state.selected = None

# Input and search controls
st.subheader("Step 1: Add Narrator to Chain")
st.text_input("Type a narrator's name (partial allowed):", key='input', on_change=update_matches)

# Show dropdown if matches exist
if st.session_state.matches:
    st.selectbox("Select from matches:", st.session_state.matches, key='selected')
    st.button("Add Narrator", on_click=add_narrator)

# Display selected chain with removal
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
            if st.button("❌ Remove", key=f"remove_{idx}"):
                st.session_state.narrator_chain.pop(idx)
                break
    # Reset chain\#
    if st.button("Reset Chain"):
        st.session_state.narrator_chain.clear()

# Overlap calculation and display
def lifespan_overlap(b1, d1, b2, d2):
    return max(0, min(d1, d2) - max(b1, b2))

chain = st.session_state.narrator_chain
if len(chain) >= 2:
    st.subheader("Lifespan Overlap Check")
    results = []
    a_iter, b_iter = tee(chain)
    next(b_iter, None)
    for a, b in zip(a_iter, b_iter):
        ra = narrators_df[narrators_df['name_letters'] == a].iloc[0]
        rb = narrators_df[narrators_df['name_letters'] == b].iloc[0]
        overlap = lifespan_overlap(ra['birth_greg'], ra['death_greg'], rb['birth_greg'], rb['death_greg'])
        strength = ("✅ Strong" if overlap >= 10 else "🟡 Weak" if overlap >= 1 else "❌ None")
        results.append({
            'Narrator A': f"{a} ({ra.get('name_arabic','')})",
            'Lifespan A': f"{ra['birth_greg']}–{ra['death_greg']}",
            'Narrator B': f"{b} ({rb.get('name_arabic','')})",
            'Lifespan B': f"{rb['birth_greg']}–{rb['death_greg']}",
            'Overlap Strength': strength
        })
    st.dataframe(pd.DataFrame(results), use_container_width=True)
elif len(chain) == 1:
    st.info("Select at least two narrators to see overlap.")
else:
    st.info("Add narrators above to build your chain.")
