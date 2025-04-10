import streamlit as st
import pandas as pd
import plotly.express as px


# --- Load data ---
@st.cache_data
def load_data():
    df = pd.read_csv("data/CSCI_full_schedule.csv")
    return df

df = load_data()

# Map short weekday letters to full names
day_map = {"M": "Monday", "T": "Tuesday", "W": "Wednesday", "R": "Thursday", "F": "Friday"}

def expand_days(day_str):
    if isinstance(day_str, str):
        day_str = day_str.replace("[", "").replace("]", "").replace("'", "")
        days = [d.strip() for d in day_str.split(",")]
        return [day_map.get(d, d) for d in days]
    return [None]

# Create new column with list of full weekday names
df["Expanded Days"] = df["Days"].apply(expand_days)

# Explode the dataframe so each day gets its own row
df = df.explode("Expanded Days")

# Replace the original Days column with the expanded one
df["Days"] = df["Expanded Days"]
df = df.drop(columns=["Expanded Days"])



# --- Extract year from course title ---
def get_year(course_title):
    try:
        code = int(course_title.split()[1])
        if 1000 <= code < 2000:
            return "Year 1"
        elif 2000 <= code < 3000:
            return "Year 2"
        elif 3000 <= code < 4000:
            return "Year 3"
        elif 4000 <= code < 5000:
            return "Year 4"
        else:
            return "Other"
    except:
        return "Unknown"

def time_bucket(t):
    try:
        start = t.split("-")[0]
        hour = int(start[:2])
        return f"{hour:02d}:00"
    except:
        return "Unknown"

# --- Preprocess data ---
df["Year"] = df["Course Title"].apply(get_year)
df["Time Block"] = df["Time"].apply(time_bucket)
df = df[df["Time Block"] != "Unknown"]  # Remove rows with unknown time blocks

# --- Sidebar Filters ---
st.sidebar.title("Filters")
year_options = df["Year"].unique().tolist()
selected_years = st.sidebar.multiselect("Select Year(s)", year_options, default=year_options)
metric_option = st.sidebar.radio("Metric:", ["Number of Courses", "Current Enrollment"])
filtered_df = df[df["Year"].isin(selected_years)]
metric_col = "Course Count" if metric_option == "Number of Courses" else "Current Enrollment"

# --- Page Title ---
st.title("Dalhousie CSCI Schedule Dashboard")
st.markdown("Visualize class schedules to support student engagement planning.")

# --- Tabs for Visualization ---
tabs = st.tabs([
    "Heatmap", "Daily Volume", "Time Trends",
    "Quiet Times", "Busiest Times", "Recommended Times", "Download"
])

# --- Heatmap Tab ---
with tabs[0]:
    st.subheader("Heatmap of Course Density")
    if metric_option == "Number of Courses":
        heatmap_df = (
            filtered_df.groupby(["Days", "Time Block"])
            .size()
            .reset_index(name="Course Count")
        )
    else:
        heatmap_df = (
            filtered_df.groupby(["Days", "Time Block"])["Current Enrollment"]
            .sum()
            .reset_index()
        )
    heatmap_df["Days"] = pd.Categorical(heatmap_df["Days"], categories=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], ordered=True)
    heatmap_df = heatmap_df.sort_values(by=["Days", "Time Block"])

    fig = px.density_heatmap(
        heatmap_df,
        x="Days",
        y="Time Block",
        z=metric_col,
        color_continuous_scale="Blues",
        nbinsx=5,
        nbinsy=24,
    )
    
    st.plotly_chart(fig, use_container_width=True)

# --- Daily Volume Tab ---
with tabs[1]:
    st.subheader("Courses by Day of Week")
    if metric_option == "Number of Courses":
        bar_df = (
            filtered_df["Days"]
            .value_counts()
            .reindex(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
            .reset_index()
        )
        bar_df.columns = ["Day", "Course Count"]
    else:
        bar_df = (
            filtered_df.groupby("Days")["Current Enrollment"]
            .sum()
            .reindex(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
            .reset_index()
        )
        bar_df.columns = ["Day", "Current Enrollment"]

    bar_chart = px.bar(bar_df, x="Day", y=metric_col, title="{} by Day".format(metric_option))
    st.plotly_chart(bar_chart, use_container_width=True)

# --- Time Trends Tab ---
with tabs[2]:
    st.subheader("Course Volume by Time of Day")
    day_choice = st.selectbox("Select a Day to View", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
    day_filtered = filtered_df[filtered_df["Days"] == day_choice]

    if metric_option == "Number of Courses":
        line_df = (
            day_filtered.groupby("Time Block")
            .size()
            .reset_index(name="Course Count")
            .sort_values("Time Block")
        )
    else:
        line_df = (
            day_filtered.groupby("Time Block")["Current Enrollment"]
            .sum()
            .reset_index()
            .sort_values("Time Block")
        )

    line_chart = px.line(line_df, x="Time Block", y=metric_col, markers=True,
                         title=f"{metric_option} on {day_choice}")
    st.plotly_chart(line_chart, use_container_width=True)

# --- Quiet Times Tab ---
with tabs[3]:
    st.subheader("Time Blocks with Fewest Courses (Quietest Times)")
    full_grid = pd.MultiIndex.from_product(
        [["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], sorted(df["Time Block"].dropna().unique())],
        names=["Days", "Time Block"]
    )
    if metric_option == "Number of Courses":
        light_df = (
            filtered_df.groupby(["Days", "Time Block"])
            .size()
            .reindex(full_grid, fill_value=0)
            .reset_index(name="Course Count")
            .sort_values("Course Count")
            .head(10)
        )
    else:
        enrollment_grid = (
            filtered_df.groupby(["Days", "Time Block"])["Current Enrollment"]
            .sum()
            .reindex(full_grid, fill_value=0)
            .reset_index()
            .sort_values("Current Enrollment")
            .head(10)
        )
        light_df = enrollment_grid

    st.write("Top 10 quietest times on the schedule:")
    st.dataframe(light_df)

# --- Busiest Times Tab ---
with tabs[4]:
    st.subheader("Time Blocks with Most Courses (Busiest Times)")
    full_grid = pd.MultiIndex.from_product(
        [["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], sorted(df["Time Block"].dropna().unique())],
        names=["Days", "Time Block"]
    )
    if metric_option == "Number of Courses":
        busy_df = (
            filtered_df.groupby(["Days", "Time Block"])
            .size()
            .reindex(full_grid, fill_value=0)
            .reset_index(name="Course Count")
            .sort_values("Course Count", ascending=False)
            .head(10)
        )
    else:
        enrollment_grid = (
            filtered_df.groupby(["Days", "Time Block"])["Current Enrollment"]
            .sum()
            .reindex(full_grid, fill_value=0)
            .reset_index()
            .sort_values("Current Enrollment", ascending=False)
            .head(10)
        )
        busy_df = enrollment_grid

    st.write("Top 10 busiest times on the schedule:")
    st.dataframe(busy_df)

# --- Recommended Times Tab ---
with tabs[5]:
    st.subheader("Top 5 Recommended Times for Engagement")
    st.markdown("Based on estimated student presence on campus vs class density.")

    # --- Time range filter ---
    min_hour, max_hour = st.slider("Limit time window", 8, 20, (10, 16))  # 24-hour format

    # Total student activity per day
    if metric_option == "Number of Courses":
        daily_totals = filtered_df.groupby("Days").size().to_dict()
        block_load = filtered_df.groupby(["Days", "Time Block"]).size().reset_index(name="Load")
    else:
        daily_totals = filtered_df.groupby("Days")["Current Enrollment"].sum().to_dict()
        block_load = filtered_df.groupby(["Days", "Time Block"])["Current Enrollment"].sum().reset_index(name="Load")

    # Drop missing Days
    block_load = block_load.dropna(subset=["Days", "Time Block"])

    # Add columns
    block_load["Foot Traffic Estimate"] = block_load["Days"].map(daily_totals)
    block_load["Opportunity Score"] = block_load["Foot Traffic Estimate"] - block_load["Load"]

    # Ensure consistent day ordering
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    block_load = block_load[block_load["Days"].isin(day_order)]
    block_load["Days"] = pd.Categorical(block_load["Days"], categories=day_order, ordered=True)

    # Extract hour for filtering
    block_load["Hour"] = block_load["Time Block"].str.extract(r"(\d{2})").astype(int)
    filtered_recs = block_load[(block_load["Hour"] >= min_hour) & (block_load["Hour"] <= max_hour)]

    # Best 5 times overall
    top5 = filtered_recs.sort_values("Opportunity Score", ascending=False).head(5).reset_index(drop=True)

    if not top5.empty:
        best_time = top5.iloc[0]
        st.success(
            f"📣 Best Time: **{best_time['Days']} at {best_time['Time Block']}** — "
            f"Score: {int(best_time['Opportunity Score'])}"
        )

        # --- Bar chart ---
        st.markdown("### Top 5 Blocks by Opportunity Score")
        bar_fig = px.bar(
            top5,
            x="Time Block",
            y="Opportunity Score",
            color="Days",
            title="Top Engagement Windows",
            labels={"Opportunity Score": "Score"},
            hover_data=["Days", "Load", "Foot Traffic Estimate"]
        )
        st.plotly_chart(bar_fig, use_container_width=True)

        # --- Table view of top 5 ---
        st.markdown("### Full Breakdown")
        st.dataframe(top5[["Days", "Time Block", "Opportunity Score", "Load", "Foot Traffic Estimate"]])
    else:
        st.warning("No recommended times found in selected range.")

    # --- Best time per day ---
    st.markdown("### Best Time Per Day")
    best_per_day = (
        filtered_recs.sort_values("Opportunity Score", ascending=False)
        .groupby("Days", as_index=False)
        .first()
        .sort_values("Days")
    )
    st.dataframe(best_per_day[["Days", "Time Block", "Opportunity Score", "Load", "Foot Traffic Estimate"]])





# --- Download Tab ---
with tabs[6]:
    st.subheader("Download Current Filtered Data")
    @st.cache_data
    def convert_df_to_csv(dataframe):
        return dataframe.to_csv(index=False).encode("utf-8")

    csv_data = convert_df_to_csv(filtered_df)
    st.download_button(
        label="Download CSV",
        data=csv_data,
        file_name="filtered_schedule.csv",
        mime="text/csv"
    )
