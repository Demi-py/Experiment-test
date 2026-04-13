import streamlit as st
import pandas as pd
import random
import os

st.title("Planning Generator")

# =========================
# INPUTS
# =========================

participants = st.multiselect(
    "Select aanwezige personen",
    [f"P{i}" for i in range(1, 13)]
)

balls_input = st.text_input(
    "Voer actieve balls in (bijv: B1,B2,B3)",
    "B1,B2,B3,B4"
)

active_balls = [b.strip() for b in balls_input.split(",") if b.strip()]

history_file = "history.xlsx"

# =========================
# HISTORY INLEZEN
# =========================

if os.path.exists(history_file):
    history_df = pd.read_excel(history_file)
else:
    history_df = pd.DataFrame()

used_balls = set(history_df["Ball"]) if not history_df.empty else set()

# =========================
# PLANNING FUNCTIE
# =========================

def create_schedule(participants, active_balls, history_df):
    step_names = ["Stap 1", "Stap 2", "Stap 3", "Stap 4", "Stap 5"]

    # hoe vaak iemand op een stap stond
    counts = {step: {p: 0 for p in participants} for step in step_names}

    for step in step_names:
        if step in history_df.columns:
            vc = history_df[step].value_counts()
            for p in participants:
                counts[step][p] = vc.get(p, 0)

    schedule = []

    for i, ball in enumerate(active_balls):
        if ball in used_balls:
            continue

        route = {"Ball": ball}
        possible = participants.copy()

        step_order = ["Stap 2", "Stap 3", "Stap 4", "Stap 1", "Stap 5"]

        current_route_people = []

        for step in step_order:
            valid = [p for p in possible]

            # overlap check met history
            def overlap_score(p):
                score = 0
                for _, row in history_df.iterrows():
                    prev = set([row[s] for s in step_names if s in row])
                    new = set(current_route_people + [p])
                    score += len(prev.intersection(new))
                return score

            min_count = min(counts[step][p] for p in valid)
            candidates = [p for p in valid if counts[step][p] == min_count]

            best = min(candidates, key=lambda p: overlap_score(p))

            route[step] = best
            possible.remove(best)
            counts[step][best] += 1
            current_route_people.append(best)

        schedule.append(route)

    df = pd.DataFrame(schedule)
    df.insert(1, "Blok", [(i // 4) + 1 for i in range(len(df))])

    return df

# =========================
# GENEREREN
# =========================

if st.button("Genereer planning"):

    if not participants:
        st.warning("Selecteer eerst deelnemers")
    else:
        df = create_schedule(participants, active_balls, history_df)
        st.dataframe(df)

        # download schedule
        st.download_button(
            "Download planning",
            df.to_csv(index=False),
            "schedule.csv"
        )

        # update history
        new_history = pd.concat([history_df, df], ignore_index=True)

        st.download_button(
            "Download updated history",
            new_history.to_csv(index=False),
            "history.csv"
        )
