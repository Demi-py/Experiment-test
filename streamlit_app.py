import streamlit as st
import pandas as pd
import random
import io

# 1. Page Configuration & Title
st.set_page_config(page_title="Balaclava Schedule Generator", layout="wide")
st.title("Balaclava Schedule Generator 2.0")

# 2. Setup Step Names & Initial Session States
steps = [f"Step {i} ({chr(64+i)})" for i in range(1, 6)]

if "history_df" not in st.session_state:
    st.session_state.history_df = pd.DataFrame()
if "df_schedule" not in st.session_state:
    st.session_state.df_schedule = None

# --- Helper Functions ---

def create_schedule(parts, balas, hist_df):
    """Core logic to generate the route avoiding previous counts."""
    counts = {s: {p: 0 for p in parts} for s in steps}
    if not hist_df.empty:
        for s in steps:
            if s in hist_df:
                for p in parts: 
                    counts[s][p] = hist_df[s].value_counts().get(p, 0)

    used_balas = set(hist_df["Balaclava"].dropna().astype(str)) if not hist_df.empty and "Balaclava" in hist_df else set()
    
    schedule = []
    for b in [m for m in balas if m not in used_balas]:
        route, avail_parts = {"Balaclava": b}, parts.copy()
        for s in steps:
            if not avail_parts: break
            # Logic: Choose participant with the minimum previous count for this specific step
            min_val = min(counts[s][p] for p in avail_parts)
            candidates = [p for p in avail_parts if counts[s][p] == min_val]
            chosen = random.choice(candidates)
            route[s] = chosen
            avail_parts.remove(chosen)
            counts[s][chosen] += 1
        schedule.append(route)
    return pd.DataFrame(schedule, columns=["Balaclava"] + steps)

def render_downloads(df, filename):
    """Generates download buttons for CSV and Excel."""
    c1, c2 = st.columns(2)
    # CSV
    c1.download_button(f"Download {filename} (CSV)", df.to_csv(index=False).encode("utf-8"), f"{filename}.csv", "text/csv")
    # Excel
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    c2.download_button(f"Download {filename} (Excel)", buf.getvalue(), f"{filename}.xlsx")

# --- UI Layout ---

# Sidebar for Inputs
with st.sidebar:
    st.header("Setup")
    participants = st.multiselect("Participants present?", [f"P{i}" for i in range(1, 13)])
    balaclava_input = st.text_area("Balaclavas (comma-separated)", placeholder="M1, M2, M3...")
    active_balas = [m.strip() for m in balaclava_input.split(",") if m.strip()]
    
    history_file = st.file_uploader("Upload Master History", type=["csv", "xlsx"])
    if history_file and st.session_state.history_df.empty:
        st.session_state.history_df = pd.read_csv(history_file) if history_file.name.endswith(".csv") else pd.read_excel(history_file)

# Main Section: History Preview
if not st.session_state.history_df.empty:
    with st.expander("View Uploaded History Records", expanded=False):
        st.dataframe(st.session_state.history_df, use_container_width=True, hide_index=True)
else:
    st.info("No history loaded yet. Routes will be generated randomly.")

# Generate Button
if st.button("Generate New Schedule"):
    if len(participants) < 5:
        st.error("Need at least 5 participants for a 5-step route.")
    elif not active_balas:
        st.error("Please enter at least one Balaclava ID.")
    else:
        new_df = create_schedule(participants, active_balas, st.session_state.history_df)
        if not new_df.empty:
            new_df["Done?"] = False  # Add your checkbox column
            st.session_state.df_schedule = new_df
        else:
            st.warning("All provided Balaclavas have already been used in the history!")

# Main Section: The Interactive Table
if st.session_state.df_schedule is not None:
    st.divider()
    st.subheader("Today's Schedule")
    st.write("Edit Step 5 or check off completed rows below:")

    edited_df = st.data_editor(
        st.session_state.df_schedule,
        column_config={
            "Step 5 (E)": st.column_config.SelectboxColumn("Step 5 (E)", options=participants, required=True),
            "Done?": st.column_config.CheckboxColumn("Completed", default=False)
        },
        disabled=["Balaclava"] + steps[:4],
        use_container_width=True,
        hide_index=True,
        key="main_editor"
    )

    # Validation logic
    row_check = [steps[i] for i in range(5)]
    has_dupes = any(len(row.dropna()) != len(set(row.dropna())) for _, row in edited_df[row_check].iterrows())
    
    if has_dupes:
        st.error("Duplicate participant detected in the same row! Please fix Step 5.")
    else:
        st.success("Schedule is valid.")

    # Show combined history for the final download
    st.subheader("Updated Master History Preview")
    combined_hist = pd.concat([st.session_state.history_df, edited_df], ignore_index=True)
    st.dataframe(combined_hist, use_container_width=True, hide_index=True)

    # Downloads
    st.divider()
    st.write("### Export Data")
    render_downloads(edited_df, "daily_schedule")
    render_downloads(combined_hist, "master_history_updated")

    if st.button("Clear & Start Over"):
        st.session_state.df_schedule = None
        st.rerun()
