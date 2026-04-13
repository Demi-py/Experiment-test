import streamlit as st
import pandas as pd
import random
import io

st.set_page_config(page_title="Mask Schedule Generator", layout="wide")

st.title("Mask Schedule Generator")

# =========================
# PARTICIPANT SELECTION
# =========================

st.subheader("Select participants")

all_participants = [f"P{i}" for i in range(1, 13)]

selected_participants = []
cols = st.columns(6)

for i, p in enumerate(all_participants):
    if cols[i % 6].checkbox(p):
        selected_participants.append(p)

# =========================
# MASK INPUT
# =========================

masks_input = st.text_area(
    "Enter masks (comma separated, e.g. M1,M2,M3)",
    value=""
)

active_masks = [m.strip() for m in masks_input.split(",") if m.strip()]

# =========================
# HISTORY UPLOAD
# =========================

uploaded_history = st.file_uploader(
    "Upload previous history (optional)",
    type=["csv", "xlsx"]
)

if uploaded_history is not None:
    if uploaded_history.name.endswith(".csv"):
        history_df = pd.read_csv(uploaded_history)
    else:
        history_df = pd.read_excel(uploaded_history)
else:
    history_df = pd.DataFrame()

# =========================
# SCHEDULE FUNCTION
# =========================

def create_schedule(participants, masks, history_df):
    step_names = [
        "Step 1 (A)",
        "Step 2 (B)",
        "Step 3 (C)",
        "Step 4 (D)",
        "Step 5 (E)"
    ]

    schedule = []

    # history counts
    counts = {step: {p: 0 for p in participants} for step in step_names}

    for step in step_names:
        if step in history_df.columns:
            vc = history_df[step].value_counts()
            for p in participants:
                counts[step][p] = vc.get(p, 0)

    for mask in masks:
        route = {"Mask": mask}
        possible = participants.copy()

        for step in step_names:
            if not possible:
                break

            # choose least-used participant for this step
            min_count = min(counts[step][p] for p in possible)
            candidates = [p for p in possible if counts[step][p] == min_count]

            chosen = random.choice(candidates)

            route[step] = chosen
            possible.remove(chosen)
            counts[step][chosen] += 1

        schedule.append(route)

    df = pd.DataFrame(schedule)

    return df

# =========================
# GENERATE
# =========================

if st.button("Generate schedule"):
    if len(selected_participants) < 5:
        st.error("You need at least 5 participants.")
    elif len(active_masks) == 0:
        st.error("Enter at least 1 mask.")
    else:
        df = create_schedule(selected_participants, active_masks, history_df)

        st.subheader("Generated schedule")
        st.dataframe(df, use_container_width=True)

        # updated history
        if history_df.empty:
            updated_history = df.copy()
        else:
            updated_history = pd.concat([history_df, df], ignore_index=True)

        # downloads
        schedule_csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download schedule (CSV)",
            schedule_csv,
            "schedule.csv"
        )

        history_csv = updated_history.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download updated history (CSV)",
            history_csv,
            "history.csv"
        )

        # Excel export
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Schedule")
        excel_buffer.seek(0)

        st.download_button(
            "Download schedule (Excel)",
            excel_buffer,
            "schedule.xlsx"
        )

