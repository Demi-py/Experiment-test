import streamlit as st
import pandas as pd
import random
import io

st.set_page_config(page_title="Balaclava Schedule Generator", layout="wide")
st.title("Balaclava Schedule Generator")
st.write("Generate a schedule for selected participants. Step 5 can be manually adjusted before download.")

# =========================
# 1. Inputs & Setup
# =========================
participants = st.multiselect("Participants present today?", [f"P{i}" for i in range(1, 13)])
balaclavas = [m.strip() for m in st.text_area("Balaclavas (comma-separated, e.g., B1,B2)").split(",") if m.strip()]
history_file = st.file_uploader("Upload a previous history file (optional)", type=["csv", "xlsx"])

# Inline history loading
history_df = pd.DataFrame()
if history_file:
    history_df = pd.read_csv(history_file) if history_file.name.endswith(".csv") else pd.read_excel(history_file)

steps = [f"Step {i} ({chr(64+i)})" for i in range(1, 6)] # Generates Step 1 (A) to Step 5 (E)

# =========================
# 2. Logic Functions
# =========================
def create_schedule(parts, balas, hist_df):
    counts = {s: {p: 0 for p in parts} for s in steps}
    if not hist_df.empty:
        for s in steps:
            if s in hist_df:
                for p in parts: counts[s][p] = hist_df[s].value_counts().get(p, 0)

    used_balas = set(hist_df["Balaclava"].dropna().astype(str)) if not hist_df.empty and "Balaclava" in hist_df else set()
    
    schedule = []
    for b in [m for m in balas if m not in used_balas]:
        route, avail_parts = {"Balaclava": b}, parts.copy()
        for s in steps:
            if not avail_parts: break
            # Find participants with the minimum count for this step
            chosen = random.choice([p for p in avail_parts if counts[s][p] == min(counts[s][p] for p in avail_parts)])
            route[s] = chosen
            avail_parts.remove(chosen)
            counts[s][chosen] += 1
        schedule.append(route)
        
    return pd.DataFrame(schedule, columns=["Balaclava"] + steps)

def render_downloads(df, filename_prefix):
    """Helper function to keep download logic DRY (Don't Repeat Yourself)"""
    col1, col2 = st.columns(2)
    col1.download_button(f"Download {filename_prefix} (CSV)", df.to_csv(index=False).encode("utf-8"), f"{filename_prefix}.csv", "text/csv")
    
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    col2.download_button(f"Download {filename_prefix} (Excel)", buf.getvalue(), f"{filename_prefix}.xlsx")

# =========================
# 3. UI & Execution
# =========================
if st.button("Generate schedule"):
    if len(participants) < 5: st.error("You need at least 5 participants for a 5 step route.")
    elif not balaclavas: st.error("Please enter at least 1 Balaclava.")
    else:
        df_schedule = create_schedule(participants, balaclavas, history_df)
        
        if df_schedule.empty:
            st.warning("No new Balaclavas left to schedule, or they were already present in the history.")
        else:
            st.subheader("Generated schedule")
            
            # --- NEW: Add a boolean column for the checkbox ---
            df_schedule["Step 5 Done"] = False 
            
            edited_df = st.data_editor(
                df_schedule,
                column_config={
                    "Step 5 (E)": st.column_config.SelectboxColumn("Step 5 (E)", options=participants, required=True),
                    # --- NEW: Configure the checkbox column ---
                    "Step 5 Done": st.column_config.CheckboxColumn("Done?", default=False)
                },
                disabled=["Balaclava"] + steps[:4],
                use_container_width=True, hide_index=True
            )

            # Pythonic duplicate validation check (this stays the same, it ignores the new checkbox column)
            has_duplicates = any(len(row.dropna()) != len(set(row.dropna())) for _, row in edited_df[steps].iterrows())
            if has_duplicates:
                st.error("Duplicate participant found in a row. Each participant must appear only once per row.")
            else:
                st.success("Schedule is valid.")

            updated_hist = edited_df if history_df.empty else pd.concat([history_df, edited_df], ignore_index=True)
            st.subheader("Updated history preview")
            st.dataframe(updated_hist, use_container_width=True, hide_index=True)

            st.write("### Downloads")
            render_downloads(edited_df, "schedule")
            render_downloads(updated_hist, "history")


