import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from google import genai
from sqlalchemy import create_engine
import plotly.express as px
import sqlite3
import json

# ---------- Page Setup ----------
st.set_page_config(page_title="AI Insight Agent", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700;800&display=swap');

* {
    font-family: 'Space Grotesk', sans-serif;
}

.stApp {
    background: linear-gradient(-45deg, #0a0e27, #1e0a3c, #0a1e3c, #1a0a2e);
    background-size: 400% 400%;
    animation: gradientShift 15s ease infinite;
}

@keyframes gradientShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

.stApp::before {
    content: "";
    position: fixed;
    top: 10%; left: 5%;
    width: 400px; height: 400px;
    background: radial-gradient(circle, rgba(139, 92, 246, 0.25) 0%, transparent 70%);
    border-radius: 50%;
    filter: blur(40px);
    animation: float1 8s ease-in-out infinite;
    pointer-events: none;
    z-index: 0;
}

.stApp::after {
    content: "";
    position: fixed;
    bottom: 10%; right: 5%;
    width: 450px; height: 450px;
    background: radial-gradient(circle, rgba(59, 130, 246, 0.25) 0%, transparent 70%);
    border-radius: 50%;
    filter: blur(40px);
    animation: float2 10s ease-in-out infinite;
    pointer-events: none;
    z-index: 0;
}

@keyframes float1 {
    0%, 100% { transform: translate(0, 0); }
    50% { transform: translate(50px, 30px); }
}

@keyframes float2 {
    0%, 100% { transform: translate(0, 0); }
    50% { transform: translate(-40px, -40px); }
}

[data-testid="stAppViewContainer"] > .main {
    background-image: 
        linear-gradient(rgba(139, 92, 246, 0.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(139, 92, 246, 0.06) 1px, transparent 1px);
    background-size: 35px 35px;
}

h1 {
    background: linear-gradient(90deg, #a78bfa, #60a5fa, #a78bfa);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: shine 4s linear infinite;
    font-weight: 800 !important;
    font-size: 3rem !important;
    text-shadow: 0 0 40px rgba(139, 92, 246, 0.3);
}

@keyframes shine {
    to { background-position: 200% center; }
}

h2, h3 {
    color: #c4b5fd !important;
    font-weight: 700 !important;
}

p, .stMarkdown {
    color: #cbd5e1;
}

[data-testid="stMetric"] {
    background: rgba(139, 92, 246, 0.08);
    border: 1px solid rgba(139, 92, 246, 0.3);
    border-radius: 16px;
    padding: 24px;
    backdrop-filter: blur(12px);
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

[data-testid="stMetric"]:hover {
    border: 1px solid rgba(167, 139, 250, 0.8);
    box-shadow: 0 0 30px rgba(139, 92, 246, 0.4), inset 0 0 20px rgba(139, 92, 246, 0.05);
    transform: translateY(-4px);
}

[data-testid="stMetricValue"] {
    background: linear-gradient(90deg, #a78bfa, #60a5fa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800 !important;
}

.stButton > button {
    background: linear-gradient(90deg, #7c3aed, #3b82f6);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 700;
    padding: 12px 32px;
    box-shadow: 0 4px 15px rgba(124, 58, 237, 0.4);
    transition: all 0.3s ease;
}

.stButton > button:hover {
    box-shadow: 0 0 35px rgba(124, 58, 237, 0.7);
    transform: translateY(-2px) scale(1.02);
}

.stTextInput > div > div > input {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(139, 92, 246, 0.4);
    color: white;
    border-radius: 10px;
    padding: 12px;
    font-size: 1rem;
}

.stTextInput > div > div > input:focus {
    border: 1px solid rgba(167, 139, 250, 1);
    box-shadow: 0 0 20px rgba(139, 92, 246, 0.3);
}

hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, rgba(139, 92, 246, 0.6), transparent) !important;
}

[data-testid="stSidebar"] {
    background: rgba(10, 14, 39, 0.9);
    border-right: 1px solid rgba(139, 92, 246, 0.25);
}

[data-testid="stSidebar"] a {
    color: #a78bfa !important;
}

.streamlit-expanderHeader {
    background: rgba(139, 92, 246, 0.1);
    border-radius: 10px;
    border: 1px solid rgba(139, 92, 246, 0.2);
}

[data-testid="stDataFrame"] {
    border: 1px solid rgba(139, 92, 246, 0.2);
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# ---------- Backend Setup ----------
import streamlit as st

# Local mein .env se, deployed mein st.secrets se
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    db_url = st.secrets["DATABASE_URL"]
except (FileNotFoundError, KeyError):
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    db_url = os.getenv("DATABASE_URL")

client = genai.Client(api_key=api_key)
conn = create_engine(db_url)

schema_info = """
Tables:
1. order_products_full(order_id, product_id, add_to_cart_order, reordered, product_name, aisle_id, department_id, aisle, department)
2. orders(order_id, user_id, eval_set, order_number, order_dow, order_hour_of_day, days_since_prior_order)
3. products(product_id, product_name, aisle_id, department_id)
4. aisles(aisle_id, aisle)
5. departments(department_id, department)
"""


def ask_question(question):
    planning_prompt = f"""You are a senior data analyst. Given this database schema:
{schema_info}

The user asked: "{question}"

Decide what SQL queries are needed to answer this well. Simple factual questions need 1 query. Strategic/advisory questions need 2-4 queries to gather enough context before giving a recommendation.

Return ONLY a JSON list of SQL queries needed, nothing else. No markdown, no explanation.
Example format: ["SELECT ...", "SELECT ..."]
"""
    plan_response = client.models.generate_content(model="gemini-3.6-flash", contents=planning_prompt)
    plan_text = plan_response.text.strip().replace("```json", "").replace("```", "").strip()

    import json
    try:
        queries = json.loads(plan_text)
    except Exception:
        queries = [plan_text]

    all_results = []
    for q in queries:
        try:
            res = pd.read_sql_query(q, conn)
            all_results.append((q, res))
        except Exception as e:
            all_results.append((q, f"Error: {e}"))

    combined_data = ""
    for q, res in all_results:
        combined_data += f"\nQuery: {q}\nResult:\n{res if isinstance(res, str) else res.to_string(index=False)}\n"

    final_prompt = f"""The user asked: "{question}"

Here is the data gathered to answer this:
{combined_data}

Write a clear, business-focused answer. If the question is strategic, give 2-3 specific, data-backed recommendations, not just raw numbers. If it's a simple factual question, answer in one direct sentence. Do not mention SQL or databases."""

    final_response = client.models.generate_content(model="gemini-3.6-flash", contents=final_prompt)
    return queries, all_results, final_response.text.strip()


# ---------- Load Data ----------
df = pd.read_sql_query("SELECT * FROM order_products_full", conn)

# ---------- Header ----------
st.title("🛒 AI-Powered Retail Insight Agent")
st.write("Statistical + AI-driven analytics on Instacart data")

# ---------- KPIs ----------
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Orders", f"{df['order_id'].nunique():,}")
with col2:
    st.metric("Total Products", f"{df['product_id'].nunique():,}")
with col3:
    reorder_rate = df['reordered'].mean() * 100
    st.metric("Overall Reorder Rate", f"{reorder_rate:.1f}%")

# ---------- Charts ----------
st.divider()
st.subheader("📊 Department Insights")

col1, col2 = st.columns(2)
with col1:
    dept_volume = df['department'].value_counts().reset_index()
    dept_volume.columns = ['department', 'order_count']
    fig1 = px.bar(dept_volume.head(10), x='department', y='order_count',
                   title="Top 10 Departments by Order Volume")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    reorder_by_dept = df.groupby('department')['reordered'].mean().sort_values(ascending=False).reset_index()
    reorder_by_dept.columns = ['department', 'reorder_rate']
    fig2 = px.bar(reorder_by_dept.head(10), x='department', y='reorder_rate',
                   title="Top 10 Departments by Reorder Rate")
    st.plotly_chart(fig2, use_container_width=True)

# ---------- AI Chat ----------
st.divider()
st.subheader("💬 Ask the Data (AI-Powered)")

user_question = st.text_input("Ask a question about the data")

if st.button("Ask") and user_question:
    with st.spinner("Analyzing..."):
        queries, all_results, answer = ask_question(user_question)

    st.markdown(f"**💡 Answer:** {answer}")

    with st.expander("See analysis details"):
        for q, res in all_results:
            st.code(q, language="sql")
            if isinstance(res, pd.DataFrame):
                st.dataframe(res)
            else:
                st.write(res)

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("### About")
    st.write("Built by Bhaskar — AI-powered retail analytics")
    st.markdown("📧 [sparsh4142@gmail.com](mailto:sparsh4142@gmail.com)")
    st.markdown("🔗 [GitHub](https://github.com/Bhaskar-Black)")
    st.markdown("🔗 [LinkedIn](https://linkedin.com/in/bhaskarstackanalyst)")

# ============================================================
# SECTION: Upload Your Own Data
# ============================================================
st.divider()
st.header("📁 Upload Your Own Data")
st.write("Upload one or more CSVs — join them, visualize, and ask AI questions.")

uploaded_files = st.file_uploader("Choose CSV file(s)", type="csv", accept_multiple_files=True)

if uploaded_files:
    tables = {}
    for f in uploaded_files:
        table_name = f.name.replace(".csv", "")
        tables[table_name] = pd.read_csv(f)

    st.success(f"Loaded {len(tables)} table(s): {', '.join(tables.keys())}")

    with st.expander("Preview tables"):
        for name, tdf in tables.items():
            st.markdown(f"**{name}** ({len(tdf):,} rows)")
            st.dataframe(tdf.head(5))

    working_df = None

    if len(tables) == 1:
        working_df = list(tables.values())[0]
        st.info("Only one table uploaded — using it directly.")
    else:
        st.subheader("🔗 Join Your Tables")
        st.write("Start with a base table, then add tables one by one by choosing the join column each time.")

        table_names = list(tables.keys())
        base_table = st.selectbox("Start with base table", table_names, key="base_table")

        if "join_steps" not in st.session_state:
            st.session_state["join_steps"] = []

        remaining_tables = [t for t in table_names if t != base_table]

        if remaining_tables:
            st.markdown("**Add a table to join:**")
            col1, col2, col3 = st.columns(3)

            with col1:
                next_table = st.selectbox("Join with", remaining_tables, key="next_table")

            current_cols = tables[base_table].columns.tolist()
            for step in st.session_state["join_steps"]:
                if step["result_cols"]:
                    current_cols = step["result_cols"]

            with col2:
                left_key = st.selectbox("Column from current data", current_cols, key=f"left_key_{len(st.session_state['join_steps'])}")
            with col3:
                right_key = st.selectbox(f"Column from {next_table}", tables[next_table].columns.tolist(), key=f"right_key_{len(st.session_state['join_steps'])}")

            join_type = st.selectbox("Join type", ["left", "inner", "right", "outer"], index=0, key=f"join_type_{len(st.session_state['join_steps'])}")

            if st.button("➕ Add This Join"):
                st.session_state["join_steps"].append({
                    "table": next_table,
                    "left_key": left_key,
                    "right_key": right_key,
                    "join_type": join_type,
                    "result_cols": None
                })
                st.rerun()

        working_df = tables[base_table].copy()
        for i, step in enumerate(st.session_state["join_steps"]):
            try:
                working_df = working_df.merge(
                    tables[step["table"]],
                    left_on=step["left_key"],
                    right_on=step["right_key"],
                    how=step["join_type"]
                )
                st.session_state["join_steps"][i]["result_cols"] = working_df.columns.tolist()
            except Exception as e:
                st.error(f"Join step {i+1} failed: {e}")
                working_df = None
                break

        if st.session_state["join_steps"] and working_df is not None:
            st.success(f"Joined {len(st.session_state['join_steps'])+1} tables → {len(working_df):,} rows, {len(working_df.columns)} columns.")
            with st.expander("Preview joined data"):
                st.dataframe(working_df.head(10))

            if st.button("🔄 Reset Joins"):
                st.session_state["join_steps"] = []
                st.rerun()
        elif not st.session_state["join_steps"]:
            st.info("Add at least one join above to combine tables.")
            working_df = None

    # ---------- Only proceed if we have working_df ----------
    if working_df is not None:

        st.subheader("📊 Choose up to 4 columns to visualize")
        selected_cols = st.multiselect(
            "Select columns",
            options=working_df.columns.tolist(),
            max_selections=4,
            key="viz_cols"
        )

        if selected_cols:
            for col in selected_cols:
                st.markdown(f"#### {col}")

                if pd.api.types.is_numeric_dtype(working_df[col]):
                    fig = px.histogram(working_df, x=col, title=f"Distribution of {col}")
                else:
                    value_counts = working_df[col].value_counts().reset_index().head(15)
                    value_counts.columns = [col, 'count']
                    fig = px.bar(value_counts, x=col, y='count', title=f"Top values in {col}")

                st.plotly_chart(fig, use_container_width=True)

                explain_prompt = f"""Column name: {col}
Data type: {working_df[col].dtype}
Sample values: {working_df[col].dropna().head(5).tolist()}
Basic stats: {working_df[col].describe().to_dict()}

In 1-2 short sentences, explain what this data likely represents and one notable pattern in it. Be concise and business-friendly."""

                insight = client.models.generate_content(model="gemini-3.6-flash", contents=explain_prompt)
                st.info(f"💡 {insight.text.strip()}")

        st.divider()
        st.subheader("💬 Ask AI About This Data")

        user_conn = sqlite3.connect(":memory:")
        working_df.to_sql("uploaded_data", user_conn, index=False, if_exists="replace")

        dynamic_schema = f"Table: uploaded_data({', '.join(working_df.columns.tolist())})"

        user_question_upload = st.text_input("Ask a question about your data", key="upload_question")

        if st.button("Ask", key="upload_ask_button") and user_question_upload:
            with st.spinner("Analyzing..."):
                plan_prompt = f"""You are a data analyst. Given this table schema:
{dynamic_schema}

The user asked: "{user_question_upload}"

Return ONLY a valid SQLite query to answer this. No markdown, no explanation."""

                plan_resp = client.models.generate_content(model="gemini-3.6-flash", contents=plan_prompt)
                sql_q = plan_resp.text.strip().replace("```sql", "").replace("```", "").strip()

                try:
                    result_df = pd.read_sql_query(sql_q, user_conn)
                    explain_prompt2 = f"""The user asked: "{user_question_upload}"
Result:
{result_df.to_string(index=False)}

Answer in one clear, business-friendly sentence with specific numbers. Do not mention SQL."""
                    final_ans = client.models.generate_content(model="gemini-3.6-flash", contents=explain_prompt2)

                    st.markdown(f"**💡 Answer:** {final_ans.text.strip()}")
                    with st.expander("See query and raw result"):
                        st.code(sql_q, language="sql")
                        st.dataframe(result_df)
                except Exception as e:
                    st.error(f"Couldn't process that question: {e}")