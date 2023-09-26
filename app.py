# import modules
import streamlit as st
import glob
import pandas as pd
from helper import extract_text
from threading import Thread
import time
import numpy as np
import plotly.express as px
import sqlite3


# read excel files where all skills, company names, enclusion, exclusion mentioned
list_of_data_dict = glob.glob("data_dictionary/*")
list_of_data_dict = {
    str(i).split("\\")[-1].split(".")[0]: str(i) for i in list_of_data_dict
}
list_of_data_dict = {
    str(i).replace("_", " ").capitalize(): j for i, j in list_of_data_dict.items()
}
TEMP_LOC = "./temp/"
queue_list = []

# create sqlite connection and create an database and table
conn = sqlite3.connect("resume.sqlite", check_same_thread=False)
cur = conn.cursor()
query = 'Create table if not Exists performance_score ("Mail" text, "Mobile" text, "Degree" text, "Certification Count" text, "Skills" text,  "Experience" text, "Skill Score" text, "Degree Score" text, "Certification Score" text, "Experience Score" text, "Overall Score" text, "Type" text)'
conn.execute(query)

# streamlit works
st.set_page_config("AI-DRS", layout="wide", page_icon="./assets/icon_g.png")
st.header("AI Driven Recruitment System (AI-DRS)")

custom_data_dictionary_index = st.sidebar.radio(
    "Select Data Dictionary", list_of_data_dict.keys(), index=0
)

st.sidebar.divider()

custom_data_dictionary_path = st.sidebar.file_uploader(
    "Upload Custom Data Dictionary", type="xlsx", accept_multiple_files=False
)

st.sidebar.divider()

st.sidebar.header("Control Contribution")

# applied weigtage and calculation for sidebar to show data records
degree_weight = (
    st.sidebar.slider("Degree", min_value=0, max_value=100, step=25, value=25) / 100
)
skill_weight = (
    st.sidebar.slider("Skill", min_value=0, max_value=100, step=25, value=25) / 100
)
exp_weight = (
    st.sidebar.slider("Experience", min_value=0, max_value=100, step=25, value=25) / 100
)
cert_weight = (
    st.sidebar.slider("Certificate", min_value=0, max_value=100, step=25, value=25)
    / 100
)

if np.round(degree_weight + skill_weight + exp_weight + cert_weight, 2) != 1.0:
    st.sidebar.warning("Weights assigned are not equals to 100")

if custom_data_dictionary_path != None:
    print()
    custom_data_dictionary = pd.read_excel(
        custom_data_dictionary_path, sheet_name="Skills"
    )
    excl_dictionary = pd.read_excel(
        custom_data_dictionary_path, sheet_name="Exclusion Skills"
    )
    excl_comp_dictionary = pd.read_excel(
        custom_data_dictionary_path, sheet_name="Exclusion Company"
    )
else:
    custom_data_dictionary = pd.read_excel(
        list_of_data_dict[custom_data_dictionary_index], sheet_name="Skills"
    )
    excl_dictionary = pd.read_excel(
        list_of_data_dict[custom_data_dictionary_index], sheet_name="Exclusion Skills"
    )
    excl_comp_dictionary = pd.read_excel(
        list_of_data_dict[custom_data_dictionary_index], sheet_name="Exclusion Company"
    )

# both two tabs
tab1, tab2 = st.tabs(["Upload Resume", "View Existing Resumes"])

# tab 1 to upload resume i.e processed single and multi pdf
with tab1:
    col1, col2 = st.columns(2)
    thread_list = []
    with col1:
        list_of_files = st.file_uploader(
            "Upload Resumes", type="pdf", accept_multiple_files=True
        )
        for i in list_of_files:
            with open(TEMP_LOC + i.name + ".pdf", "wb") as output_temporary_file:
                output_temporary_file.write(i.read())
        # thread to show time to process file
        for i in list_of_files:
            thread_list.append(
                Thread(
                    target=extract_text,
                    args=(
                        TEMP_LOC + i.name + ".pdf",
                        queue_list,
                        custom_data_dictionary,
                        excl_dictionary["Skills"].tolist(),
                        excl_comp_dictionary["Company"].tolist(),
                    ),
                )
            )

        for i in thread_list:
            i.start()

    if len(list_of_files) > 0:
        with col2:
            start_time = time.time()
            st.write("Processing Status")
            with st.spinner("Extracting Information & Analyzing ...."):
                while sum([int(i.is_alive()) for i in thread_list]) > 0:
                    pass
            st.success(f"Time Taken : {np.round(time.time() - start_time, 2)} s")
        overall_df = pd.DataFrame(
            queue_list,
            columns=[
                "Mail",
                "Mobile",
                "Status",
                "Degree",
                "Score",
                "Degree Score",
                "Certification Count",
                "Experience",
            ],
        )
        overall_df["Mail"] = overall_df["Mail"].replace(" ", np.nan)
        overall_df["Mail"] = overall_df["Mail"].replace("", np.nan)
        overall_df.dropna(subset=["Mail"], inplace=True)
        overall_df.index = overall_df.Mail
        overall_df.drop(columns=["Mail"], inplace=True)
        overall_df["Skills"] = overall_df["Score"].map(
            lambda x: [
                k for i in x["Skills"].values() for k in str(i).split(",") if len(k) > 0
            ]
        )
        for index, val in enumerate(overall_df["Score"]):
            try:
                overall_df.loc[overall_df.index[index], val["Segment"].values()] = val[
                    "Score"
                ].values()
                overall_df.loc[overall_df.index[index], "Skill Count"] = sum(
                    list(val["Score"].values())
                )
            except:
                pass
        overall_df["Skill Score"] = np.round(
            overall_df["Skill Count"].rank()
            / overall_df["Skill Count"].rank().max()
            * 100,
            0,
        ).astype(int)
        overall_df["Degree Score"] = np.round(
            overall_df["Degree Score"].rank()
            / overall_df["Degree Score"].rank().max()
            * 100,
            0,
        ).astype(int)
        overall_df["Certification Score"] = np.round(
            overall_df["Certification Count"].rank()
            / overall_df["Certification Count"].rank().max()
            * 100,
            0,
        ).astype(int)
        overall_df["Experience Score"] = np.round(
            overall_df["Experience"].rank()
            / overall_df["Experience"].rank().max()
            * 100,
            0,
        ).astype(int)
        overall_df["Overall Score"] = (
            overall_df["Skill Score"] * skill_weight
            + overall_df["Degree Score"] * degree_weight
            + overall_df["Certification Score"] * cert_weight
            + overall_df["Experience Score"] * exp_weight
        )
        overall_df["Overall Score"] = np.round(overall_df["Overall Score"], 0).astype(
            int
        )

        overall_df.sort_values(
            ["Status", "Overall Score"], inplace=True, ascending=[False, False]
        )
        overall_df.drop(columns=["Score"], inplace=True)

        # all sub tabs rename
        sub_tab1, sub_tab2, sub_tab3, sub_tab4, sub_tab5, sub_tab6 = st.tabs(
            [
                "Table View",
                "Overall Score",
                "Skill Score",
                "Experience Score",
                "Degree Score",
                "Certifications Score",
            ]
        )

        # color conditions for verified and not verified
        def set_status_color(value):
            if value == "Verified":
                return "color: green; background-color: lightgreen; font: bold"
            else:
                return "color: red; background-color: pink; font: bold"
            return

        # tab2 to show existing resume in db present where 6 subtask for each fields according to which field we are extracting from resumes.
        with sub_tab1:
            st.dataframe(
                overall_df[
                    [
                        "Mobile",
                        "Status",
                        "Skills",
                        "Experience",
                        "Degree",
                        "Certification Count",
                        "Overall Score",
                        "Skill Score",
                        "Experience Score",
                        "Degree Score",
                        "Certification Score",
                    ]
                ].style.applymap(set_status_color, subset=["Status"]),
                use_container_width=True,
            )
            sub_tab1_col1, sub_tab1_col2, _ = st.columns([1, 1, 2])
            with sub_tab1_col1:
                button_push = st.button("Save", use_container_width=True)
                if button_push:
                    push_df = overall_df[overall_df["Status"] != "Rejected"][
                        [
                            "Mobile",
                            "Degree",
                            "Certification Count",
                            "Skills",
                            "Experience",
                            "Skill Score",
                            "Degree Score",
                            "Certification Score",
                            "Experience Score",
                            "Overall Score",
                        ]
                    ].copy()
                    push_df["Type"] = custom_data_dictionary_index
                    push_df = push_df.astype(str)
                    push_df.reset_index().to_sql(
                        "performance_score", conn, if_exists="append", index=False
                    )
                    conn.commit()
            with sub_tab1_col2:
                download_button = st.download_button(
                    "Download as CSV",
                    file_name="performance.csv",
                    mime="text/csv",
                    use_container_width=True,
                    data=overall_df[
                        [
                            "Mobile",
                            "Degree",
                            "Certification Count",
                            "Skills",
                            "Experience",
                            "Skill Score",
                            "Degree Score",
                            "Certification Score",
                            "Experience Score",
                            "Overall Score",
                        ]
                    ]
                    .to_csv()
                    .encode("utf-8"),
                )
        with sub_tab2:
            overall_rank_df = overall_df[overall_df["Status"] != "Rejected"][
                ["Overall Score"]
            ].copy()
            overall_rank_df = overall_rank_df.reset_index().sort_values(
                ["Overall Score"], ascending=True
            )
            fig = px.bar(overall_rank_df, x="Overall Score", y="Mail", orientation="h")
            st.plotly_chart(fig)
        with sub_tab3:
            skill_rank_df = overall_df[overall_df["Status"] != "Rejected"][
                list(custom_data_dictionary["Segment"].values)
            ].copy()
            skill_rank_df = pd.melt(
                skill_rank_df.reset_index(),
                id_vars="Mail",
                value_vars=list(custom_data_dictionary["Segment"].values),
            )
            skill_rank_df.rename(columns={"variable": "Skills"}, inplace=True)

            overall_skill_rank_df = overall_df[overall_df["Status"] != "Rejected"][
                ["Skill Score"]
            ].copy()
            overall_skill_rank_df = overall_skill_rank_df.reset_index().sort_values(
                ["Skill Score"], ascending=False
            )
            fig = px.bar(overall_skill_rank_df, x="Mail", y="Skill Score")
            st.plotly_chart(fig)

            fig = px.scatter(
                skill_rank_df, x="Mail", y="Skills", size="value", color="Skills"
            )
            st.plotly_chart(fig)

        with sub_tab4:
            exp_rank_df = overall_df[overall_df["Status"] != "Rejected"][
                ["Experience Score"]
            ].copy()
            exp_rank_df = exp_rank_df.reset_index().sort_values(
                ["Experience Score"], ascending=False
            )
            fig = px.bar(exp_rank_df, x="Mail", y="Experience Score")
            st.plotly_chart(fig)

        with sub_tab5:
            degree_rank_df = overall_df[overall_df["Status"] != "Rejected"][
                ["Degree Score"]
            ].copy()
            degree_rank_df = degree_rank_df.reset_index().sort_values(
                ["Degree Score"], ascending=False
            )
            fig = px.bar(degree_rank_df, x="Mail", y="Degree Score")
            st.plotly_chart(fig)

        with sub_tab6:
            cert_rank_df = overall_df[overall_df["Status"] != "Rejected"][
                ["Certification Score"]
            ].copy()
            cert_rank_df = cert_rank_df.reset_index().sort_values(
                ["Certification Score"], ascending=False
            )
            fig = px.bar(cert_rank_df, x="Mail", y="Certification Score")
            st.plotly_chart(fig)

# final statement that will show the result according to above conditions
with tab2:
    overall_fetch_df = pd.read_sql(
        f'SELECT * FROM performance_score where Type = "{custom_data_dictionary_index}"',
        conn,
    )
    user_list = st.multiselect("Select Users", options=overall_fetch_df.Mail)
    if len(user_list) != 0:
        overall_fetch_df = overall_fetch_df[overall_fetch_df["Mail"].isin(user_list)]
    overall_fetch_df.index = overall_fetch_df.Mail
    overall_fetch_df["Degree"] = overall_fetch_df["Degree"].map(lambda x: eval(x))
    overall_fetch_df["Skills"] = overall_fetch_df["Skills"].map(lambda x: eval(x))
    overall_fetch_df.sort_values(["Overall Score"], ascending=False, inplace=True)
    overall_fetch_df.drop_duplicates(["Mail"], keep="first", inplace=True)
    overall_fetch_df.drop(columns=["Type", "Mail"], inplace=True)
    overall_fetch_df = overall_fetch_df[
        ["Mobile", "Skills", "Experience", "Degree", "Certification Count"]
    ]
    st.dataframe(overall_fetch_df, use_container_width=True)
