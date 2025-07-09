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

# App configuration
st.set_page_config(layout="wide")
st.title("Chronological Sanad Validator")
st.markdown("Check if narrators in a hadith chain lived during overlapping periods.")

# Search helper: substring first, then fuzzy fallback
def search_narrators(query, choices, cutoff=0.7, n=8):
    q = query.lower().strip()
    substr = [c for c in choices if q in c.lower()]
    if substr:
        return substr[:n]
    lowered = [c.lower() for c in choices]
    fuzzy = get_close_matches(q, lowered, n=n, cutoff=cutoff)
    return [choices[i] for i, lc in enumerate(lowered) if lc in fuzzy]

# Initialize session state defaults
def init_state():
    if 'narrator_chain' not in st.session_state:
        st.session_state.narrator_chain = []
    for key in ('input', 'matches', 'selected'):
        if key not in st.session_state:
            st.session_state[key] = [] if key == 'matches' else ''

init_state()

# Callbacks

def add_narrator():
    sel = st.session_state.selected
    if sel and sel not in st.session_state.narrator_chain:
        st.session_state.narrator_chain.append(sel)
    # reset input state
    st.session_state.input = ''
    st.session_state.matches = []
    st.session_state.selected = ''

def remove_narrator(idx):
    if 0 <= idx < len(st.session_state.narrator_chain):
        st.session_state.narrator_chain.pop(idx)
        # Also clear input and matches
        st.session_state.input = ''
        st.session_state.matches = []
        st.session_state.selected = ''

    if 0 <= idx < len(st.session_state.narrator_chain):
        st.session_state.narrator_chain.pop(idx)
        # reset any selection
        st.session_state.matches = []
        st.session_state.selected = ''
        st.session_state.input = ''
    st.experimental_rerun()

def reset_chain():
    st.session_state.narrator_chain = []
    st.session_state.input = ''
    st.session_state.matches = []
    st.session_state.selected = ''


# Input section
st.subheader("Step 1: Add Narrator to Chain")
st.text_input("Type a narrator's name (partial allowed):", key='input', on_change=lambda: st.session_state.update({'matches': search_narrators(st.session_state.input, narrators_df['name_letters'].tolist())}))

# Suggestion dropdown and add button
if st.session_state['matches']:
    st.selectbox("Select from matches:", st.session_state.matches, key='selected')
    st.button("Add Narrator", on_click=add_narrator)

# Display selected chain
if st.session_state.narrator_chain:
    st.markdown("**Selected Chain (Earliest to Latest):**")
    for idx, name in enumerate(st.session_state.narrator_chain):
        row = narrators_df[narrators_df['name_letters'] == name].iloc[0]
        arabic = row.get('name_arabic', '')
        grade = row.get('grade', '') if pd.notna(row.get('grade', None)) else '—'
        c1, c2 = st.columns([0.9, 0.1])
        with c1:
            st.write(f"{idx+1}. {name} ({arabic}) — Grade: {grade}")
        with c2:
            st.button("❌ Remove", key=f"remove_{idx}", on_click=remove_narrator, args=(idx,))
    st.button("Reset Chain", on_click=reset_chain)

# Overlap calculation
chain = st.session_state.narrator_chain
if len(chain) >= 2:
    st.subheader("Lifespan Overlap Check")
    data = []
    a_iter, b_iter = tee(chain)
    next(b_iter, None)
    for a, b in zip(a_iter, b_iter):
        ra = narrators_df[narrators_df['name_letters'] == a].iloc[0]
        rb = narrators_df[narrators_df['name_letters'] == b].iloc[0]
        overlap = max(0, min(ra['death_greg'], rb['death_greg']) - max(ra['birth_greg'], rb['birth_greg']))
        strength = "✅ Strong" if overlap >= 10 else "🟡 Weak" if overlap >= 1 else "❌ None"
        data.append({
            'Narrator A': f"{a} ({ra.get('name_arabic','')})",
            'Lifespan A': f"{ra['birth_greg']}–{ra['death_greg']}",
            'Narrator B': f"{b} ({rb.get('name_arabic','')})",
            'Lifespan B': f"{rb['birth_greg']}–{rb['death_greg']}",
            'Overlap Strength': strength
        })
    st.dataframe(pd.DataFrame(data), use_container_width=True)
elif len(chain) == 1:
    st.info("Select at least two narrators to see overlap.")
else:
    st.info("Add narrators above to build your chain.")
