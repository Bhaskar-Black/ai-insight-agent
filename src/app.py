import streamlit as st
import pandas as pd
import sqlite3
import os
from dotenv import load_dotenv
from google import genai
import plotly.express as px

# ---------- Page Setup ----------
st.set_page_config(page_title="AI Insight Agent", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700;800&display=swap');

* {
    font-family: 'Space Grotesk', sans-serif;
}

/* Animated gradient background */
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

/* Glowing orbs floating in background */
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

/* Grid pattern overlay */
[data-testid="stAppViewContainer"] > .main {
    background-image: 
        linear-gradient(rgba(139, 92, 246, 0.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(139, 92, 246, 0.06) 1px, transparent 1px);
    background-size: 35px 35px;
}

/* Title - big glowing gradient text */
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

/* KPI metric cards - glassmorphism with glow border */
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

/* Buttons - vibrant glow */
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

/* Text input */
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

/* Divider glow */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, rgba(139, 92, 246, 0.6), transparent) !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: rgba(10, 14, 39, 0.9);
    border-right: 1px solid rgba(139, 92, 246, 0.25);
}

[data-testid="stSidebar"] a {
    color: #a78bfa !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: rgba(139, 92, 246, 0.1);
    border-radius: 10px;
    border: 1px solid rgba(139, 92, 246, 0.2);
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(139, 92, 246, 0.2);
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# ---------- Backend Setup ----------
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)
conn = sqlite3.connect(r'C:\Projects\Insights Agent\insights_agent.db', check_same_thread=False)

schema_info = """
Tables:
1. order_products_full(order_id, product_id, add_to_cart_order, reordered, product_name, aisle_id, department_id, aisle, department)
2. orders(order_id, user_id, eval_set, order_number, order_dow, order_hour_of_day, days_since_prior_order)
3. products(product_id, product_name, aisle_id, department_id)
4. aisles(aisle_id, aisle)
5. departments(department_id, department)
"""

def ask_question(question):
    # Step 1: AI decide kare kitni queries chahiye
    planning_prompt = f"""You are a senior data analyst. Given this database schema:
{schema_info}

The user asked: "{question}"

Decide what SQL queries are needed to answer this well. Simple factual questions need 1 query. Strategic/advisory questions (like "how to increase sales", "why is X underperforming") need 2-4 queries to gather enough context (e.g. reorder rate, cart position, department trends, volume) before giving a recommendation.

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

    # Step 2: Saari queries run karo
    all_results = []
    for q in queries:
        try:
            res = pd.read_sql_query(q, conn)
            all_results.append((q, res))
        except Exception as e:
            all_results.append((q, f"Error: {e}"))

    # Step 3: Sab results combine karke final answer banao
    combined_data = ""
    for q, res in all_results:
        combined_data += f"\nQuery: {q}\nResult:\n{res if isinstance(res, str) else res.to_string(index=False)}\n"

    final_prompt = f"""The user asked: "{question}"

Here is the data gathered to answer this:
{combined_data}

Write a clear, business-focused answer. If the question is strategic (e.g. asking how to improve something), give 2-3 specific, data-backed recommendations, not just raw numbers. If it's a simple factual question, answer in one direct sentence. Do not mention SQL or databases."""

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

user_question = st.text_input("Ask a question about the data (e.g. 'Which department has the highest reorder rate?')")

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
st.divider()
st.markdown("📧 **Get in touch:** [sparsh4142@gmail.com](mailto:sparsh4142@gmail.com)")
with st.sidebar:
    st.markdown("### About")
    st.write("Built by Bhaskar — AI-powered retail analytics")
    st.markdown("📧 [sparsh4142@gmail.com](mailto:sparsh4142@gmail.com)")
    st.markdown("🔗 [GitHub](https://github.com/Bhaskar-Black)")
    st.markdown("🔗 [LinkedIn](https://linkedin.com/in/bhaskarstackanalyst)")