import streamlit as st
import pandas as pd
from difflib import get_close_matches
from itertools import tee
import os

# Load and prepare dataset
@st.cache_data
def load_data():
    base_dir = os.path.dirname(__file__)
    candidates = [
        'narrators_dataset_v3.csv',
        os.path.join(base_dir, 'narrators_dataset_v3.csv'),
        '/mnt/data/narrators_dataset_v3.csv'
    ]
    csv_file = next((p for p in candidates if os.path.exists(p)), None)
    if csv_file is None:
        st.error(
            "Data file 'narrators_dataset_v3.csv' not found. "
            "Please upload the CSV into the same directory as app.py or place it in '/mnt/data'."
        )
        return pd.DataFrame()
    df = pd.read_csv(csv_file)
    # Filter valid lifespans
    df = df[(df['birth_greg'] > 0) & (df['death_greg'] > 0)]
    df = df[df['birth_greg'] != df['death_greg']]
    # Normalize column names
    df.columns = df.columns.str.strip().str.lower()
    # Parse places_of_stay into cities list
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
st.title("Hadith Narrator Connection")
st.markdown("Visualize and validate the hand-off between hadith narrators.")

# Search helper
def search_narrators(query, choices, cutoff=0.7, n=8):
    q = query.lower().strip()
    substr = [c for c in choices if q in c.lower()]
    if substr:
        return substr[:n]
    lowered = [c.lower() for c in choices]
    fuzzy = get_close_matches(q, lowered, n=n, cutoff=cutoff)
    return [choices[i] for i, lc in enumerate(lowered) if lc in fuzzy]

# Initialize session state
for k, default in [('narrator_chain', []), ('matches', []), ('input', ''), ('selected', '')]:
    if k not in st.session_state:
        st.session_state[k] = default

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
if st.session_state.input and not st.session_state.matches:
    st.error("Unable to find narrator. Please try a different name.")

if st.session_state.matches:
    st.selectbox("Select from matches:", st.session_state.matches, key='selected')
    st.button("Add Narrator", on_click=add_narrator)

# Display selected chain
chain = st.session_state.narrator_chain
if chain:
    st.markdown("**Selected Chain (Earliest to Latest):**")
    for idx, name in enumerate(chain):
        row = narrators_df[narrators_df['name_letters'] == name].iloc[0]
        grade = row.get('grade', '—') if pd.notna(row.get('grade', None)) else '—'
        c1, c2 = st.columns([0.9, 0.1])
        with c1:
            st.write(f"{idx+1}. {name} — Grade: {grade}")
        with c2:
            st.button("❌", key=f"remove_{idx}", on_click=remove_narrator, args=(idx,))
    st.button("Reset Chain", on_click=reset_chain)

# Results cards
if len(chain) >= 2:
    st.subheader("Sanad Validation Results")
    lookup = narrators_df.set_index('name_letters')
    for i, (a, b) in enumerate(zip(chain, chain[1:]), start=1):
        ra = lookup.loc[a]
        rb = lookup.loc[b]
        # Temporal overlap
        overlap_years = max(
            0,
            min(ra['death_greg'], rb['death_greg']) - max(ra['birth_greg'], rb['birth_greg'])
        )
        # Geographic overlap
        common = set(ra['cities']).intersection(rb['cities'])
        # Direct isnad check
        a_idx = ra['scholar_index']
        b_idx = rb['scholar_index']
        is_teacher = b_idx in ra['students_index'] or a_idx in rb['teachers_index']
        is_student = b_idx in ra['teachers_index'] or a_idx in rb['students_index']
        # Link label
        if is_teacher:
            link_label = f"{a} is the teacher of {b}"
        elif is_student:
            link_label = f"{a} is the student of {b}"
        else:
            link_label = "None"
        # Status
        if is_teacher or is_student:
            status = "🟢 Silsilah muttasilah"
        elif overlap_years >= 10:
            status = "✅ Strong"
        elif overlap_years >= 1 and common:
            status = "✅ Strong (Geo)"
        elif overlap_years >= 1:
            status = "🟡 Weak"
        else:
            status = "❌ None"
        geo = ', '.join([c.title() for c in sorted(common)]) if common else '—'
        # Render card
        st.markdown(f"""
**{i}. {a} → {b}**  
• **Status:** {status}  
• **Lifespan {a}:** {ra['birth_greg']} CE – {ra['death_greg']} CE  
• **Lifespan {b}:** {rb['birth_greg']} CE – {rb['death_greg']} CE  
• **Overlap Duration:** {overlap_years} year{'s' if overlap_years != 1 else ''}  
• **Shared City:** {geo}  
• **Student-Teacher Link:** {link_label}
"""
        )
        st.divider()
elif len(chain) == 1:
    st.info("Select at least two narrators to see validation.")
else:
    st.info("Add narrators above to build your chain.")
