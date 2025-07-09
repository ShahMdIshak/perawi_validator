import streamlit as st
import pandas as pd
from difflib import get_close_matches
from itertools import tee

# Load and prepare dataset
@st.cache_data
def load_data():
    df = pd.read_csv("narrators_dataset_v3.csv")
    # Valid lifespans
    df = df[(df['birth_greg'] > 0) & (df['death_greg'] > 0)]
    df = df[df['birth_greg'] != df['death_greg']]
    # Normalize column names
    df.columns = df.columns.str.strip().str.lower()
    # Parse places_of_stay into list of cities
    df['cities'] = df['places_of_stay']\
        .fillna('')\
        .apply(lambda x: [c.strip().lower() for c in x.split(',') if c.strip()])
    # Parse student and teacher indices
    df['students_index'] = df['students_index']\
        .fillna('')\
        .apply(lambda x: [int(i) for i in str(x).split(',') if i.strip().isdigit()])
    df['teachers_index'] = df['teachers_index']\
        .fillna('')\
        .apply(lambda x: [int(i) for i in str(x).split(',') if i.strip().isdigit()])
    return df

narrators_df = load_data()

# App configuration
st.set_page_config(layout="wide")
st.title("Chronological Sanad Validator")
st.markdown("Enhanced validation with temporal, geographic, and direct chain checks.")

# Search helper
def search_narrators(query, choices, cutoff=0.7, n=8):
    q = query.lower().strip()
    substr = [c for c in choices if q in c.lower()]
    if substr:
        return substr[:n]
    lowered = [c.lower() for c in choices]
    fuzzy = get_close_matches(q, lowered, n=n, cutoff=cutoff)
    return [choices[i] for i, lc in enumerate(lowered) if lc in fuzzy]

# Initialize state
def init_state():
    for key, default in [('narrator_chain', []), ('matches', []), ('input', ''), ('selected', '')]:
        if key not in st.session_state:
            st.session_state[key] = default

init_state()

# Callbacks

def add_narrator():
    sel = st.session_state.selected
    if sel and sel not in st.session_state.narrator_chain:
        st.session_state.narrator_chain.append(sel)
    st.session_state.input = ''
    st.session_state.matches = []
    st.session_state.selected = ''


def remove_narrator(idx):
    chain = st.session_state.narrator_chain
    if 0 <= idx < len(chain):
        chain.pop(idx)
    st.session_state.matches = []
    st.session_state.selected = ''
    st.session_state.input = ''


def reset_chain():
    st.session_state.narrator_chain.clear()
    st.session_state.input = ''
    st.session_state.matches = []
    st.session_state.selected = ''

# Input UI
st.subheader("Add Narrator to Chain")
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
# No match indicator
if st.session_state.input and not st.session_state.matches:
    st.error("Unable to find narrator. Please try a different name.")

# Suggestions and add button
if st.session_state.matches:
    st.selectbox("Select from matches:", st.session_state.matches, key='selected')
    st.button("Add Narrator", on_click=add_narrator)

# Display chain
chain = st.session_state.narrator_chain
if chain:
    st.markdown("**Selected Chain (Earliest to Latest):**")
    for idx, name in enumerate(chain):
        row = narrators_df[narrators_df['name_letters']==name].iloc[0]
        grade = row.get('grade','—') if pd.notna(row.get('grade',None)) else '—'
        col1, col2 = st.columns([0.9,0.1])
        with col1:
            st.write(f"{idx+1}. {name} — Grade: {grade}")
        with col2:
            st.button("❌ Remove", key=f"remove_{idx}", on_click=remove_narrator, args=(idx,))
    st.button("Reset Chain", on_click=reset_chain)

# Overlap & validation
if len(chain) >= 2:
    st.subheader("Sanad Validation Results")
    lookup = narrators_df.set_index('name_letters')
    for i, (a, b) in enumerate(zip(chain, chain[1:]), start=1):
        ra = lookup.loc[a]
        rb = lookup.loc[b]
        # Temporal overlap
        overlap_years = max(0, min(ra['death_greg'], rb['death_greg']) - max(ra['birth_greg'], rb['birth_greg']))
        # Geographic overlap
        common = set(ra['cities']).intersection(rb['cities'])
        # Direct isnad check
        direct = (rb['scholar_index'] in ra['students_index']) or (ra['scholar_index'] in rb['teachers_index'])
        # Scoring logic
        if direct:
            status = "🟢 Silsilah muttasilah"
        elif overlap_years >= 10:
            status = "✅ Strong"
        elif overlap_years >= 1 and common:
            status = "✅ Strong (Geo)"
        elif overlap_years >= 1:
            status = "🟡 Weak"
        else:
            status = "❌ None"
        geo = ', '.join(sorted(common)) if common else '—'
        # Render card
        st.markdown(f"""
**{i}. {a} → {b}**  
• **Status:** {status}  
• **Lifespan A:** {ra['birth_greg']}–{ra['death_greg']}  
• **Lifespan B:** {rb['birth_greg']}–{rb['death_greg']}  
• **Shared City:** {geo}  
• **Direct Link:** {'✔️' if direct else '—'}
"""
        )
        st.divider()
elif len(chain) == 1:
    st.info("Select at least two narrators to see validation.")
else:
    st.info("Add narrators above to build your chain.")
