
import streamlit as st
import pandas as pd
import random
import io

st.set_page_config(page_title="Planning Generator", layout="wide")

st.title("Planning Generator")

st.write("Deze versie gebruikt jouw originele logica, stap 2, 3 en 4 zijn restricted binnen een blok van 4 routes, stap 1 en stap 5 zijn vrij.")

# =========================
# INPUT
# =========================

all_participants = [f"P{i}" for i in range(1, 13)]

selected_participants = st.multiselect(
    "Welke personen zijn er vandaag?",
    all_participants,
    default=all_participants
)

balls_input = st.text_area(
    "Welke balls/routes wil je vandaag gebruiken? Vul komma-gescheiden in, bijvoorbeeld B1,B2,B3,B4",
    value="B1,B2,B3,B4"
)

active_balls = [b.strip() for b in balls_input.split(",") if b.strip()]

uploaded_history = st.file_uploader(
    "Upload een eerdere history file, optioneel",
    type=["csv", "xlsx"]
)

# =========================
# HISTORY INLEZEN
# =========================

if uploaded_history is not None:
    if uploaded_history.name.endswith(".csv"):
        history_df = pd.read_csv(uploaded_history)
    else:
        history_df = pd.read_excel(uploaded_history)
else:
    history_df = pd.DataFrame()

# =========================
# FUNCTIE
# =========================

def create_schedule(participants, active_balls, history_df, route_length=5):
    schedule = []

    # Start zoals in je originele code
    turn_history = {f"Stap {i + 1}": participants.copy() for i in range(route_length)}

    # Als er history is, voeg die toe aan turn_history zodat eerdere verdeling meetelt
    if not history_df.empty:
        for step_name in turn_history.keys():
            if step_name in history_df.columns:
                previous_values = history_df[step_name].dropna().tolist()
                previous_values = [p for p in previous_values if p in participants]
                turn_history[step_name].extend(previous_values)

    restricted_steps = ["Stap 2", "Stap 3", "Stap 4"]
    block_used_in_restricted = set()

    # Eventueel balls overslaan die al in history zitten
    used_balls = set()
    if not history_df.empty and "Ball" in history_df.columns:
        used_balls = set(history_df["Ball"].dropna().astype(str).tolist())

    filtered_active_balls = [b for b in active_balls if b not in used_balls]

    for ball_idx, ball_name in enumerate(filtered_active_balls, start=1):
        # Reset blok after every four rows
        if (ball_idx - 1) % 4 == 0:
            block_used_in_restricted = set()

        route = {"Ball": ball_name}
        possible_participants = participants.copy()
        step_order = ["Stap 2", "Stap 3", "Stap 4", "Stap 1", "Stap 5"]

        for step_name in step_order:
            # Tel hoe vaak iemand al op deze stap heeft gestaan
            counts = pd.Series(turn_history[step_name]).value_counts()

            if step_name in restricted_steps:
                valid_for_this_step = [
                    p for p in possible_participants
                    if p not in block_used_in_restricted
                ]
            else:
                valid_for_this_step = possible_participants.copy()

            # Fallback als restricted te streng wordt
            if not valid_for_this_step:
                valid_for_this_step = possible_participants.copy()

            participant_count_labels = []
            participant_count_values = []

            for p in valid_for_this_step:
                participant_count_labels.append(p)
                participant_count_values.append(counts.get(p, 0))

            min_val = min(participant_count_values)
            selected_participants_for_step = [
                p for p, x in zip(participant_count_labels, participant_count_values)
                if x == min_val
            ]

            p = random.choice(selected_participants_for_step)
            route[step_name] = p

            possible_participants.remove(p)
            turn_history[step_name].append(p)

            if step_name in restricted_steps:
                block_used_in_restricted.add(p)

        schedule.append(route)

    if not schedule:
        return pd.DataFrame(columns=["Ball", "Blok", "Stap 1", "Stap 2", "Stap 3", "Stap 4", "Stap 5"])

    df = pd.DataFrame(schedule)
    cols = ["Ball"] + [f"Stap {i + 1}" for i in range(route_length)]
    df = df[cols]
    df.insert(1, "Blok", [(i // 4) + 1 for i in range(len(df))])

    return df

# =========================
# GENEREREN
# =========================

if st.button("Genereer planning"):
    if len(selected_participants) < 5:
        st.error("Je hebt minimaal 5 aanwezige personen nodig voor een route van 5 stappen.")
    elif len(active_balls) == 0:
        st.error("Voer minstens 1 ball in.")
    else:
        df_schedule = create_schedule(
            participants=selected_participants,
            active_balls=active_balls,
            history_df=history_df,
            route_length=5
        )

        if df_schedule.empty:
            st.warning("Er zijn geen nieuwe routes over om te plannen, of alles stond al in de history.")
        else:
            st.subheader("Nieuwe planning")
            st.dataframe(df_schedule, use_container_width=True)

            # Updated history maken
            if history_df.empty:
                updated_history = df_schedule.copy()
            else:
                updated_history = pd.concat([history_df, df_schedule], ignore_index=True)

            st.subheader("Preview updated history")
            st.dataframe(updated_history, use_container_width=True)

            # CSV download planning
            schedule_csv = df_schedule.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download planning als CSV",
                data=schedule_csv,
                file_name="schedule.csv",
                mime="text/csv"
            )

            # Excel download planning
            schedule_excel_buffer = io.BytesIO()
            with pd.ExcelWriter(schedule_excel_buffer, engine="openpyxl") as writer:
                df_schedule.to_excel(writer, index=False, sheet_name="Schedule")
            schedule_excel_buffer.seek(0)

            st.download_button(
                label="Download planning als Excel",
                data=schedule_excel_buffer,
                file_name="schedule.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # CSV download updated history
            history_csv = updated_history.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download updated history als CSV",
                data=history_csv,
                file_name="history.csv",
                mime="text/csv"
            )

            # Excel download updated history
            history_excel_buffer = io.BytesIO()
            with pd.ExcelWriter(history_excel_buffer, engine="openpyxl") as writer:
                updated_history.to_excel(writer, index=False, sheet_name="History")
            history_excel_buffer.seek(0)

            st.download_button(
                label="Download updated history als Excel",
                data=history_excel_buffer,
                file_name="history.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

