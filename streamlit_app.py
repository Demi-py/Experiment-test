import streamlit as st
import pandas as pd
import random
import io

# 1. Setup for the schedule
st.set_page_config(page_title="Balaclava Schedule Generator", layout="wide")
st.title("Balaclava Schedule Generator")
steps = [f"Step {i} ({chr(64+i)})" for i in range(1, 6)]

if "history_df" not in st.session_state:
    st.session_state.history_df = pd.DataFrame()
if "df_schedule" not in st.session_state:
    st.session_state.df_schedule = None


def create_schedule(all_parts, present_parts, balas, hist_df):
    """Generate routes. Steps 1 and 5 use all participants, but prefer absent participants.
    Steps 2, 3, 4 use only present participants. No participant may appear twice in one row.
    """
    counts = {s: {p: 0 for p in all_parts} for s in steps}

    if not hist_df.empty:
        for s in steps:
            if s in hist_df.columns:
                value_counts = hist_df[s].value_counts()
                for p in all_parts:
                    counts[s][p] = value_counts.get(p, 0)

    used_balas = set()
    if not hist_df.empty and "Balaclava" in hist_df.columns:
        used_balas = set(hist_df["Balaclava"].dropna().astype(str))

    schedule = []
    absent_parts = [p for p in all_parts if p not in present_parts]

    for b in [m for m in balas if m not in used_balas]:
        route_created = False

        for _ in range(200):
            route = {"Balaclava": b}
            row_assigned = []
            valid_route = True

            for s in steps:
                if s in ["Step 2 (B)", "Step 3 (C)", "Step 4 (D)"]:
                    pool = [p for p in present_parts if p not in row_assigned]
                else:
                    preferred_pool = [p for p in absent_parts if p not in row_assigned]
                    fallback_pool = [p for p in all_parts if p not in row_assigned]
                    pool = preferred_pool if preferred_pool else fallback_pool

                if not pool:
                    valid_route = False
                    break

                min_val = min(counts[s][p] for p in pool)
                candidates = [p for p in pool if counts[s][p] == min_val]
                chosen = random.choice(candidates)

                route[s] = chosen
                row_assigned.append(chosen)

            if valid_route:
                row_values = [route[s] for s in steps]
                no_duplicates = len(row_values) == len(set(row_values))
                middle_steps_valid = all(
                    route[s] in present_parts
                    for s in ["Step 2 (B)", "Step 3 (C)", "Step 4 (D)"]
                )

                if no_duplicates and middle_steps_valid:
                    for s in steps:
                        counts[s][route[s]] += 1
                    schedule.append(route)
                    route_created = True
                    break

        if not route_created:
            st.warning(f"Could not generate a valid route for {b}.")

    return pd.DataFrame(schedule, columns=["Balaclava"] + steps)


def render_downloads(df, filename):
    """Generates download buttons for CSV and Excel."""
    c1, c2 = st.columns(2)

    c1.download_button(
        f"Download {filename} (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        f"{filename}.csv",
        "text/csv"
    )

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    c2.download_button(
        f"Download {filename} (Excel)",
        buf.getvalue(),
        f"{filename}.xlsx"
    )


# 2. Layout
all_participants = [f"P{i}" for i in range(1, 13)]

with st.sidebar:
    st.header("Setup")

    present_participants = st.multiselect(
        "Which participants are present?",
        all_participants
    )

    balaclava_input = st.text_area(
        "Balaclavas (comma-separated)",
        placeholder="B1, B2, B3..."
    )
    active_balas = [m.strip() for m in balaclava_input.split(",") if m.strip()]

    history_file = st.file_uploader("Upload Master History", type=["csv", "xlsx"])
    if history_file and st.session_state.history_df.empty:
        if history_file.name.endswith(".csv"):
            st.session_state.history_df = pd.read_csv(history_file)
        else:
            st.session_state.history_df = pd.read_excel(history_file)


# 3. History
if not st.session_state.history_df.empty:
    with st.expander("View Uploaded History Records", expanded=False):
        st.dataframe(
            st.session_state.history_df,
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("No history loaded yet. Routes will be generated randomly.")


# 4. New schedule
if st.button("Generate New Schedule"):
    if len(present_participants) < 3:
        st.error("You need at least 3 present participants for Steps B, C, and D.")
    elif not active_balas:
        st.error("Please enter at least one Balaclava ID.")
    else:
        new_df = create_schedule(
            all_participants,
            present_participants,
            active_balas,
            st.session_state.history_df
        )

        if not new_df.empty:
            new_df["Done?"] = False
            new_df["Comments"] = ""
            st.session_state.df_schedule = new_df
        else:
            st.warning(
                "All provided Balaclava IDs have already been used in the history, or no valid routes could be generated."
            )


# 5. Create interactive table
if st.session_state.df_schedule is not None:
    st.divider()
    st.subheader("Today's Schedule")
    st.write("Steps A and E use the full list. Steps B, C, and D use present participants.")

    edited_df = st.data_editor(
        st.session_state.df_schedule,
        column_config={
            "Done?": st.column_config.CheckboxColumn("Completed", default=False),
            "Comments": st.column_config.TextColumn(
                "Comments",
                help="Optional notes for this route"
            )
        },
        disabled=["Balaclava"] + steps,
        use_container_width=True,
        hide_index=True,
        key="main_editor"
    )

    # Validation logic
    row_check = steps
    has_dupes = any(
        len(list(row)) != len(set(row))
        for _, row in edited_df[row_check].iterrows()
    )

    if has_dupes:
        st.error("Duplicate participant detected in the same row!")
    else:
        st.success("Schedule is valid.")

    st.subheader("Updated History Preview")
    combined_hist = pd.concat([st.session_state.history_df, edited_df], ignore_index=True)
    st.dataframe(combined_hist, use_container_width=True, hide_index=True)

    st.divider()
    st.write("### Export Data")
    render_downloads(edited_df, "daily_schedule")
    render_downloads(combined_hist, "history_updated")

    if st.button("Clear & Start Over"):
        st.session_state.df_schedule = None
        st.rerun()

##Credits
#This project was developed by Demi van Dijk, DNA Analyst at the Netherlands Forensic Institute (NFI). The initial vesion of the scheduling alogrithm was created with help from Stijn van Lierop, Datascientist at the NFI. 
#The application was further developed, refined, and extended by Demi van Dijk, including the interface and functionality.
#AI tools (ChatGPT and Google Gemini) were used as coding assistants during development.
