import streamlit as st
import pandas as pd
from difflib import get_close_matches
from itertools import tee

# Load and prepare dataset
def load_data():
    df = pd.read_csv("narrators_dataset_v2.csv")
    # Filter valid lifespans
    df = df[(df['birth_greg'] > 0) & (df['death_greg'] > 0)]
    # Exclude narrators with same birth and death year
    df = df[df['birth_greg'] != df['death_greg']]
    # Normalize column names
    df.columns = df.columns.str.strip().str.lower()
    # Parse places_of_stay into list of cities
    df['cities'] = df['places_of_stay']\
        .fillna('')\
        .apply(lambda x: [c.strip().lower() for c in x.split(',') if c.strip()])
    return df

narrators_df = st.cache_data(load_data)()

# App configuration
st.set_page_config(layout="wide")
st.title("Chronological Sanad Validator")
st.markdown("Check if narrators in a hadith chain lived during overlapping periods and locations.")

# Search helper: substring first, then fuzzy fallback
def search_narrators(query, choices, cutoff=0.7, n=8):
    q = query.lower().strip()
    # Substring match
    substr = [c for c in choices if q in c.lower()]
    if substr:
        return substr[:n]
    # Fuzzy fallback
    lowered = [c.lower() for c in choices]
    fuzzy = get_close_matches(q, lowered, n=n, cutoff=cutoff)
    return [choices[i] for i, lc in enumerate(lowered) if lc in fuzzy]

# Initialize session state defaults
def init_state():
    if 'narrator_chain' not in st.session_state:
        st.session_state.narrator_chain = []
    if 'matches' not in st.session_state:
        st.session_state.matches = []
    if 'input' not in st.session_state:
        st.session_state.input = ''
    if 'selected' not in st.session_state:
        st.session_state.selected = ''

init_state()

# Callbacks

def add_narrator():
    sel = st.session_state.selected
    if sel and sel not in st.session_state.narrator_chain:
        st.session_state.narrator_chain.append(sel)
    # Reset search state
    st.session_state.input = ''
    st.session_state.matches = []
    st.session_state.selected = ''


def remove_narrator(idx):
    chain = st.session_state.narrator_chain
    if 0 <= idx < len(chain):
        chain.pop(idx)
    # Clear search state
    st.session_state.matches = []
    st.session_state.selected = ''
    st.session_state.input = ''


def reset_chain():
    st.session_state.narrator_chain = []
    st.session_state.matches = []
    st.session_state.input = ''
    st.session_state.selected = ''

# Input section
st.subheader("Step 1: Add Narrator to Chain")
st.text_input(
    "Type a narrator's name (partial allowed):",
    key='input',
    on_change=lambda: st.session_state.update({
        'matches': search_narrators(
            st.session_state.input,
            narrators_df['name_letters'].tolist()
        )
    })
)

# Suggestion dropdown and add button
if st.session_state.matches:
    st.selectbox(
        "Select from matches:",
        st.session_state.matches,
        key='selected'
    )
    st.button("Add Narrator", on_click=add_narrator)

# Display selected chain with remove and reset
chain = st.session_state.narrator_chain
if chain:
    st.markdown("**Selected Chain (Earliest to Latest):**")
    for idx, name in enumerate(chain):
        row = narrators_df[narrators_df['name_letters'] == name].iloc[0]
        grade = row.get('grade', '—') if pd.notna(row.get('grade', None)) else '—'
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            st.write(f"{idx+1}. {name} — Grade: {grade}")
        with col2:
            st.button(
                "❌ Remove",
                key=f"remove_{idx}",
                on_click=remove_narrator,
                args=(idx,)
            )
    st.button("Reset Chain", on_click=reset_chain)

# Overlap calculation function
def lifespan_overlap(b1, d1, b2, d2):
    return max(0, min(d1, d2) - max(b1, b2))

# Display results as cards including shared city
if len(chain) >= 2:
    st.subheader("Lifespan & Geographic Overlap Check")
    choices = narrators_df.set_index('name_letters')
    for i, (a, b) in enumerate(zip(chain, chain[1:]), start=1):
        ra = choices.loc[a]
        rb = choices.loc[b]
        overlap = lifespan_overlap(
            ra['birth_greg'], ra['death_greg'],
            rb['birth_greg'], rb['death_greg']
        )
        strength = (
            "✅ Strong" if overlap >= 10 else
            "🟡 Weak" if overlap >= 1 else
            "❌ None"
        )
        common = set(ra['cities']).intersection(rb['cities'])
        geo = ', '.join(sorted(common)) if common else '—'
        st.markdown(f"""
**{i}. {a} → {b}**  
• **Overlap:** {strength}  
• **A:** {ra['birth_greg']}–{ra['death_greg']}  
• **B:** {rb['birth_greg']}–{rb['death_greg']}  
• **Shared City:** {geo}
"""
        )
        st.divider()
elif len(chain) == 1:
    st.info("Select at least two narrators to see overlap.")
else:
    st.info("Add narrators above to build your chain.")
