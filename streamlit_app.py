import streamlit as st
import pandas as pd
import random
import io

st.set_page_config(page_title="Balaclava Schedule Generator", layout="wide")

st.title("Balaclava Schedule Generator")

st.write(
    "Generate a schedule for selected participants and Balaclavas. "
    "Step 5 can be adjusted manually in the table before downloading."
)

# =========================
# INPUT
# =========================

all_participants = [f"P{i}" for i in range(1, 13)]

selected_participants = st.multiselect(
    "Which participants are present today?",
    all_participants,
    default=[]
)

Balaclavas_input = st.text_area(
    "Which Balaclavas do you want to use today? Enter comma separated values, for example M1,M2,M3,M4",
    value=""
)

active_Balaclavas = [m.strip() for m in Balaclavas_input.split(",") if m.strip()]

uploaded_history = st.file_uploader(
    "Upload a previous history file, optional",
    type=["csv", "xlsx"]
)

# =========================
# Use a history file so that the previous participants are not following the same exact route again
# =========================

if uploaded_history is not None:
    if uploaded_history.name.endswith(".csv"):
        history_df = pd.read_csv(uploaded_history)
    else:
        history_df = pd.read_excel(uploaded_history)
else:
    history_df = pd.DataFrame()

# =========================
# Follow the route, step 1 (a) until step 5 (e)
# =========================

def create_schedule(participants, Balaclavas, history_df):
    step_names = [
        "Step 1 (A)",
        "Step 2 (B)",
        "Step 3 (C)",
        "Step 4 (D)",
        "Step 5 (E)"
    ]

    schedule = []

    # Start counts from history
    counts = {step: {p: 0 for p in participants} for step in step_names}

    if not history_df.empty:
        for step in step_names:
            if step in history_df.columns:
                value_counts = history_df[step].value_counts()
                for p in participants:
                    counts[step][p] = value_counts.get(p, 0)

    # Skip Balaclavas already present in history, since the same Balaclava cannot be used again
    used_Balaclavas = set()
    if not history_df.empty and "Balaclava" in history_df.columns:
        used_Balaclavas = set(history_df["Balaclava"].dropna().astype(str).tolist())

    filtered_Balaclavas = [m for m in Balaclavas if m not in used_Balaclavas]

    for Balaclava in filtered_Balaclavas:
        route = {"Balaclava": Balaclava}
        possible_participants = participants.copy()

        for step in step_names:
            if not possible_participants:
                break

            min_count = min(counts[step][p] for p in possible_participants)
            candidates = [
                p for p in possible_participants
                if counts[step][p] == min_count
            ]

            chosen = random.choice(candidates)

            route[step] = chosen
            possible_participants.remove(chosen)
            counts[step][chosen] += 1

        schedule.append(route)

    if not schedule:
        return pd.DataFrame(
            columns=["Balaclava"] + step_names
        )

    df = pd.DataFrame(schedule)
    df = df[["Balaclava"] + step_names]

    return df


def validate_step5_duplicates(df):
    """
    Checks whether Step 5 duplicates another participant in the same row. We do not want this.
    Returns a list of row indices with duplicates. We also do not want duplicates.
    """
    duplicate_rows = []

    for idx, row in df.iterrows():
        row_values = [
            row.get("Step 1 (A)"),
            row.get("Step 2 (B)"),
            row.get("Step 3 (C)"),
            row.get("Step 4 (D)"),
            row.get("Step 5 (E)")
        ]

        row_values = [x for x in row_values if pd.notna(x)]

        if len(row_values) != len(set(row_values)):
            duplicate_rows.append(idx)

    return duplicate_rows

# =========================
# Generate a schedule for that particular day with the selected balaclavas and with the selected participants
# =========================

if st.button("Generate schedule"):
    if len(selected_participants) < 5:
        st.error("You need at least 5 participants for a 5 step route.")
    elif len(active_Balaclavas) == 0:
        st.error("Please enter at least 1 Balaclava.")
    else:
        df_schedule = create_schedule(
            participants=selected_participants,
            Balaclavas=active_Balaclavas,
            history_df=history_df
        )

        if df_schedule.empty:
            st.warning("No new Balaclavas are left to schedule, or they were already present in the history.")
        else:
            st.subheader("Generated schedule")

            edited_df = st.data_editor(
                df_schedule,
                column_config={
                    "Step 5 (E)": st.column_config.SelectboxColumn(
                        "Step 5 (E)",
                        options=selected_participants,
                        required=True
                    )
                },
                disabled=["Balaclava", "Step 1 (A)", "Step 2 (B)", "Step 3 (C)", "Step 4 (D)"],
                use_container_width=True,
                hide_index=True
            )

            duplicate_rows = validate_step5_duplicates(edited_df)

            if duplicate_rows:
                st.error(
                    "One or more rows contain a duplicate participant after editing Step 5. "
                    "Please make sure each participant appears only once per row."
                )
            else:
                st.success("Schedule is valid.")

                if history_df.empty:
                    updated_history = edited_df.copy()
                else:
                    updated_history = pd.concat([history_df, edited_df], ignore_index=True)

                st.subheader("Updated history preview")
                st.dataframe(updated_history, use_container_width=True, hide_index=True)

                # CSV download for schedule
                schedule_csv = edited_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download schedule as CSV",
                    data=schedule_csv,
                    file_name="schedule.csv",
                    mime="text/csv"
                )

                # Excel download for schedule
                schedule_excel_buffer = io.BytesIO()
                with pd.ExcelWriter(schedule_excel_buffer, engine="openpyxl") as writer:
                    edited_df.to_excel(writer, index=False, sheet_name="Schedule")
                schedule_excel_buffer.seek(0)

                st.download_button(
                    label="Download schedule as Excel",
                    data=schedule_excel_buffer,
                    file_name="schedule.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                # CSV download for updated history
                history_csv = updated_history.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download updated history as CSV",
                    data=history_csv,
                    file_name="history.csv",
                    mime="text/csv"
                )

                # Excel download for updated history
                history_excel_buffer = io.BytesIO()
                with pd.ExcelWriter(history_excel_buffer, engine="openpyxl") as writer:
                    updated_history.to_excel(writer, index=False, sheet_name="History")
                history_excel_buffer.seek(0)

                st.download_button(
                    label="Download updated history as Excel",
                    data=history_excel_buffer,
                    file_name="history.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

