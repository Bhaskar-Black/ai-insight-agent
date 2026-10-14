import streamlit as st
import pandas as pd
import os
import time
import json
import re
import sqlite3
from io import BytesIO
from xml.sax.saxutils import escape
from dotenv import load_dotenv
from google import genai
from google.genai import types
from sqlalchemy import create_engine, event
import plotly.express as px
import pdfplumber
from openpyxl.styles import Alignment
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

_SCRIPT_START = time.time()
PERF = {}   # step -> seconds (sidebar ke 'Performance' panel mein dikhta hai)

# ============================================================
# FILE MAP (kaunsa section kya karta hai)
#   SECTION 1  : Page setup + styling (CSS)
#   SECTION 2  : Settings, API key, database connection
#   SECTION 3  : SQL safety guard
#   SECTION 4  : AI helpers (retry, query engine, chart recommendation, insights)
#   SECTION 5  : Data helpers (file parsing, join, upload DB, profiling)
#   SECTION 6  : Report builders (UI, PDF, Excel)
#   SECTION 7  : Chart rendering
#   SECTION 8  : Page: header + default Instacart dashboard
#   SECTION 9  : Sidebar
#   SECTION 10 : Page: upload -> join -> chart -> AI chat -> report
#   SECTION 11 : Page: AI chat on default Instacart data
#   SECTION 12 : Deferred AI chart insight + performance panel
# ============================================================

# ============================================================
# SECTION 1: PAGE SETUP + STYLING
# ============================================================
st.set_page_config(page_title="AI Insight Agent", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700;800&display=swap');

* { font-family: 'Space Grotesk', sans-serif; }

/* Static gradient background (fast). Animation is opt-in from the sidebar toggle. */
.stApp {
    background: linear-gradient(135deg, #0a0e27 0%, #1e0a3c 50%, #0a1e3c 100%);
}

/* Static glow orbs (no blur filter / no animation = much lighter on the browser) */
.stApp::before {
    content: ""; position: fixed; top: 10%; left: 5%;
    width: 420px; height: 420px;
    background: radial-gradient(circle, rgba(139, 92, 246, 0.22) 0%, transparent 70%);
    pointer-events: none; z-index: 0;
}
.stApp::after {
    content: ""; position: fixed; bottom: 10%; right: 5%;
    width: 460px; height: 460px;
    background: radial-gradient(circle, rgba(59, 130, 246, 0.22) 0%, transparent 70%);
    pointer-events: none; z-index: 0;
}

[data-testid="stAppViewContainer"] > .main {
    background-image:
        linear-gradient(rgba(139, 92, 246, 0.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(139, 92, 246, 0.06) 1px, transparent 1px);
    background-size: 35px 35px;
}

h1 {
    background: linear-gradient(90deg, #a78bfa, #60a5fa);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    font-weight: 800 !important; font-size: 3rem !important;
}

h2, h3, h4 { color: #c4b5fd !important; font-weight: 700 !important; }
p, .stMarkdown { color: #cbd5e1; }

[data-testid="stMetric"] {
    background: rgba(139, 92, 246, 0.10);
    border: 1px solid rgba(139, 92, 246, 0.3);
    border-radius: 16px; padding: 24px;
    transition: all 0.3s ease;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}
[data-testid="stMetric"]:hover {
    border: 1px solid rgba(167, 139, 250, 0.8);
    box-shadow: 0 0 30px rgba(139, 92, 246, 0.4);
    transform: translateY(-3px);
}
[data-testid="stMetricValue"] {
    background: linear-gradient(90deg, #a78bfa, #60a5fa);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    font-weight: 800 !important;
}

.stButton > button, .stDownloadButton > button {
    background: linear-gradient(90deg, #7c3aed, #3b82f6);
    color: white; border: none; border-radius: 10px;
    font-weight: 700; padding: 12px 32px;
    box-shadow: 0 4px 15px rgba(124, 58, 237, 0.4);
    transition: all 0.3s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    box-shadow: 0 0 30px rgba(124, 58, 237, 0.7);
    transform: translateY(-2px);
}

.stTextInput > div > div > input {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(139, 92, 246, 0.4);
    color: white; border-radius: 10px; padding: 12px; font-size: 1rem;
}
.stTextInput > div > div > input:focus {
    border: 1px solid rgba(167, 139, 250, 1);
    box-shadow: 0 0 20px rgba(139, 92, 246, 0.3);
}

hr {
    border: none !important; height: 1px !important;
    background: linear-gradient(90deg, transparent, rgba(139, 92, 246, 0.6), transparent) !important;
}

[data-testid="stSidebar"] {
    background: rgba(10, 14, 39, 0.92);
    border-right: 1px solid rgba(139, 92, 246, 0.25);
}
[data-testid="stSidebar"] a { color: #a78bfa !important; }

.streamlit-expanderHeader {
    background: rgba(139, 92, 246, 0.1);
    border-radius: 10px; border: 1px solid rgba(139, 92, 246, 0.2);
}
[data-testid="stDataFrame"] {
    border: 1px solid rgba(139, 92, 246, 0.2); border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    animated_bg = st.toggle("✨ Animated background", value=False,
                            help="Looks cooler but keeps the CPU busy. Leave it off on slower computers.")
if animated_bg:
    st.markdown("""
<style>
.stApp {
    background: linear-gradient(-45deg, #0a0e27, #1e0a3c, #0a1e3c, #1a0a2e);
    background-size: 400% 400%;
    animation: gradientShift 20s ease infinite;
}
@keyframes gradientShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
h1 { background: linear-gradient(90deg, #a78bfa, #60a5fa, #a78bfa); background-size: 200% auto;
     -webkit-background-clip: text; -webkit-text-fill-color: transparent; animation: shine 4s linear infinite; }
@keyframes shine { to { background-position: 200% center; } }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SECTION 2: SETTINGS, API KEY, DATABASE CONNECTION
# ============================================================
MODEL_NAME = "gemini-3.6-flash"
MAX_SCATTER_POINTS = 5000      # scatter plot par max points (browser fast rahe)
MAX_PLOT_POINTS = 20000        # line/box plot par max points
MAX_EXCEL_ROWS = 10000         # Excel report ke "Data" sheet mein max rows
MAX_CSV_ROWS = 100000          # CSV download mein max rows
MAX_PROFILE_COLUMNS = 30       # report profile mein max columns
MAX_RESULT_ROWS_FOR_AI = 50    # AI ko query result ki max itni rows dikhengi
DB_STATEMENT_TIMEOUT_MS = 20000  # koi query 20s se zyada chale to cancel (page freeze nahi hota)
DB_CONNECT_TIMEOUT_S = 10        # database connect hone ka max wait

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    db_url = st.secrets["DATABASE_URL"]
except (FileNotFoundError, KeyError):
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    db_url = os.getenv("DATABASE_URL")

if not api_key:
    st.error("GEMINI_API_KEY not found. Add it to your .env file (local) or Streamlit Secrets (deployed).")
    st.stop()


@st.cache_resource
def get_client(key):
    return genai.Client(api_key=key)


def normalize_db_url(url):
    """'postgresql://' ko explicitly psycopg2 par pin karta hai (naye SQLAlchemy ka default driver alag hai)."""
    url = url.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


@st.cache_resource
def get_main_engine(url):
    # Ek hi engine reuse hota hai (har rerun pe naya connection nahi banta)
    engine = create_engine(normalize_db_url(url), pool_pre_ping=True, pool_recycle=300,
                           connect_args={"connect_timeout": DB_CONNECT_TIMEOUT_S})
    if engine.dialect.name == "postgresql":
        @event.listens_for(engine, "connect")
        def _set_statement_timeout(dbapi_conn, _record):
            try:
                cur = dbapi_conn.cursor()
                cur.execute(f"SET statement_timeout = {int(DB_STATEMENT_TIMEOUT_MS)}")
                cur.close()
                dbapi_conn.commit()
            except Exception:
                pass
    return engine


client = get_client(api_key)

main_conn, db_error = None, ""
if db_url:
    try:
        main_conn = get_main_engine(db_url)
    except Exception as e:
        db_error = f"{type(e).__name__}: {str(e)[:300]}"
else:
    db_error = "DATABASE_URL is not set."

MAIN_SCHEMA = """
Tables:
1. order_products_full(order_id, product_id, add_to_cart_order, reordered, product_name, aisle_id, department_id, aisle, department)
2. orders(order_id, user_id, eval_set, order_number, order_dow, order_hour_of_day, days_since_prior_order)
3. products(product_id, product_name, aisle_id, department_id)
4. aisles(aisle_id, aisle)
5. departments(department_id, department)
"""

# ============================================================
# SECTION 3: SQL SAFETY GUARD
# Sirf read-only SELECT queries allowed hain.
# ============================================================
_DANGEROUS_KEYWORDS = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE",
                       "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE", "ATTACH", "PRAGMA"]


def is_safe_sql(query):
    normalized = query.strip().rstrip(";").strip().upper()
    if not (normalized.startswith("SELECT") or normalized.startswith("WITH")):
        return False
    if ";" in normalized:                      # multiple statements not allowed
        return False
    # Whole-word match: "created_at" / "last_updated" jaise column names block nahi hote
    return not any(re.search(rf"\b{kw}\b", normalized) for kw in _DANGEROUS_KEYWORDS)


# ============================================================
# SECTION 4: AI HELPERS
# ============================================================
@st.cache_resource
def _ai_flags():
    return {"fast_ok": True}


def _is_transient(e):
    return any(code in str(e) for code in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED"))


def _fast_config():
    # Gemini ko kam "thinking" karne ko kehta hai (is app ke tasks simple hain) -> calls kaafi tez
    return types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )


def _generate(prompt, model):
    flags = _ai_flags()
    if flags["fast_ok"]:
        try:
            return client.models.generate_content(model=model, contents=prompt, config=_fast_config())
        except Exception as e:
            if _is_transient(e):
                raise
            # shayad ye model/SDK yeh setting nahi leta: plain call try karo, chal gaya to yaad rakho
            result = client.models.generate_content(model=model, contents=prompt)
            flags["fast_ok"] = False
            return result
    return client.models.generate_content(model=model, contents=prompt)


def safe_ai_call(prompt, model=MODEL_NAME, retries=2):
    """Gemini call: fast config + automatic retry on temporary overload / rate-limit."""
    last_error = None
    for attempt in range(retries + 1):
        try:
            return _generate(prompt, model)
        except Exception as e:
            last_error = e
            if _is_transient(e) and attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            raise Exception(f"AI service error: {last_error}")


def parse_json_loose(text):
    """Parses JSON even if the model wrapped it in ```fences``` or added extra text."""
    text = text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    for open_c, close_c in (("{", "}"), ("[", "]")):
        start, end = text.find(open_c), text.rfind(close_c)
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except Exception:
                continue
    raise ValueError("No valid JSON in AI response")


def md_safe(text):
    """'$' ko escape karta hai, warna Streamlit paise wale text ko math samajh leta hai."""
    return str(text).replace("$", "\\$")


def describe_schema(df, table="uploaded_data"):
    parts = []
    for c in df.columns:
        kind = "number" if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c]) else "text"
        parts.append(f'"{c}" ({kind})')
    return f"Table: {table}(" + ", ".join(parts) + ")"


def run_ai_query(question, query_conn, schema_description, dialect="SQLite"):
    """
    UNIFIED query engine (default Instacart DB aur uploaded data dono ke liye).
    Plan queries -> safety check -> run -> synthesize final answer.
    Returns (queries, results, answer, timings).
    """
    timings = {}
    planning_prompt = f"""You are a senior data analyst. Given this database schema:
{schema_description}

The user asked: "{question}"

Write queries in {dialect} syntax. Wrap column names that contain spaces or special characters in double quotes.
Simple factual questions need 1 query. Strategic/advisory questions need 2-4 queries to gather enough context.
Only use tables and columns that exist in the schema above.

Return ONLY a JSON list of SQL query strings, nothing else. No markdown, no explanation.
Example format: ["SELECT ...", "SELECT ..."]
"""
    t = time.time()
    try:
        plan_text = safe_ai_call(planning_prompt).text
    except Exception:
        return [], [], "⚠️ Couldn't reach the AI service right now. Please try again in a moment.", timings
    timings["AI planning"] = time.time() - t

    try:
        queries = parse_json_loose(plan_text)
        if isinstance(queries, str):
            queries = [queries]
        queries = [q for q in queries if isinstance(q, str)][:4]
    except Exception:
        queries = [plan_text.strip().replace("```sql", "").replace("```", "").strip()]

    t = time.time()
    all_results = []
    for q in queries:
        if not is_safe_sql(q):
            all_results.append((q, "Blocked: only read-only SELECT queries are allowed for safety."))
            continue
        try:
            all_results.append((q, pd.read_sql_query(q, query_conn)))
        except Exception as e:
            all_results.append((q, f"Error: {e}"))
    timings["database"] = time.time() - t

    combined_data = ""
    for q, res in all_results:
        body = res if isinstance(res, str) else res.head(MAX_RESULT_ROWS_FOR_AI).to_string(index=False)
        combined_data += f"\nQuery: {q}\nResult:\n{body}\n"

    final_prompt = f"""The user asked: "{question}"

Here is the data gathered to answer this:
{combined_data}

Write a clear, business-focused answer using only the numbers shown above. If the question is strategic,
give 2-3 specific, data-backed recommendations. If it's a simple factual question, answer in one direct sentence.
Do not mention SQL or databases."""
    t = time.time()
    try:
        answer = safe_ai_call(final_prompt).text.strip()
    except Exception:
        answer = "⚠️ Got the data but couldn't write the final answer right now. Try again shortly."
    timings["AI answer"] = time.time() - t
    return queries, all_results, answer, timings


# NOTE: Cached functions neeche jaan-bhoojh ke failure par EXCEPTION raise karte hain
# (error string return nahi karte) -- warna ek baar ka temporary AI failure cache ho jaata hai.
@st.cache_data(show_spinner=False)
def get_chart_insight(chart_title, chart_type, facts):
    """AI insight jo sirf plotted numbers par based hai (invented numbers nahi)."""
    prompt = f"""You are a data analyst. A {chart_type} chart titled "{chart_title}" shows this data:
{facts}

In 2 short sentences, state the most notable pattern or comparison in this data, using specific numbers
from it. Do not invent numbers that are not shown. Business-friendly language."""
    return safe_ai_call(prompt).text.strip()


def build_col_profiles(df, cols):
    return {c: {"dtype": str(df[c].dtype),
                "sample": df[c].dropna().head(5).tolist(),
                "unique_count": int(df[c].nunique())} for c in cols}


@st.cache_data(show_spinner=False)
def _recommend_chart_cached(profiles_json):
    profiles = json.loads(profiles_json)
    cols = list(profiles.keys())
    prompt = f"""You are a data visualization expert. Given these columns from a dataset:
{profiles_json}

Recommend the SINGLE best chart for the relationship or pattern in this data.
chart_type must be one of: Bar, Line, Scatter, Pie, Box Plot.
x and y must be column names from above (y may be "(count)" if a frequency chart fits best).
color_by is optional: another column name or null.

Return ONLY valid JSON: {{"chart_type": "...", "x": "...", "y": "...", "color_by": null}}"""
    rec = parse_json_loose(safe_ai_call(prompt).text)
    if rec.get("x") in cols and rec.get("chart_type") in ["Bar", "Line", "Scatter", "Pie", "Box Plot"]:
        if rec.get("y") not in cols + ["(count)"]:
            rec["y"] = "(count)"
        if rec.get("color_by") not in cols:
            rec["color_by"] = None
        return rec
    raise ValueError("Unusable chart recommendation")


@st.cache_data(show_spinner=False, max_entries=50)
def cached_col_profiles_json(data_key, cols, _df):
    """Column profile ek baar compute hota hai (nunique 5 lakh rows par har click pe nahi chalta)."""
    return json.dumps(build_col_profiles(_df, list(cols)), default=str)


@st.cache_data(show_spinner=False, max_entries=30)
def cached_unique_values(data_key, col, _df):
    values = _df[col].dropna().unique()
    return len(values), values[:5000].tolist()


def recommend_chart(working_df, candidate_cols, data_key):
    """AI chart recommendation (cached). AI fail ho to simple heuristic fallback."""
    try:
        return _recommend_chart_cached(cached_col_profiles_json(data_key, tuple(candidate_cols), working_df))
    except Exception:
        pass
    numeric_cols = [c for c in candidate_cols
                    if pd.api.types.is_numeric_dtype(working_df[c]) and not pd.api.types.is_bool_dtype(working_df[c])]
    other_cols = [c for c in candidate_cols if c not in numeric_cols]
    if len(numeric_cols) >= 2:
        return {"chart_type": "Scatter", "x": numeric_cols[0], "y": numeric_cols[1], "color_by": None}
    if other_cols and numeric_cols:
        return {"chart_type": "Bar", "x": other_cols[0], "y": numeric_cols[0], "color_by": None}
    return {"chart_type": "Bar", "x": candidate_cols[0], "y": "(count)", "color_by": None}


# ============================================================
# SECTION 5: DATA HELPERS (file parsing, join, upload DB, profiling)
# ============================================================
def clean_columns(cols):
    """None / duplicate column names ko fix karta hai (PDF tables mein aam hai)."""
    seen, out = {}, []
    for i, c in enumerate(cols):
        name = str(c).strip().replace("\n", " ") if c not in (None, "") else f"col_{i + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        out.append(name)
    return out


def coerce_numeric_columns(df):
    """PDF se aaye text-numbers ko numeric banata hai jahan possible ho."""
    for c in df.columns:
        try:
            df[c] = pd.to_numeric(df[c])
        except (ValueError, TypeError):
            pass
    return df


@st.cache_resource(show_spinner="Reading your file...", max_entries=4)
def parse_uploaded_file(file_id, file_name, _file_bytes):
    """File ek baar parse hoti hai aur cache ho jaati hai (har rerun pe dobara nahi padhi jaati)."""
    ext = file_name.rsplit(".", 1)[-1].lower()
    base = file_name.rsplit(".", 1)[0]
    tables, notes = {}, []

    if ext == "csv":
        try:
            tables[base] = pd.read_csv(BytesIO(_file_bytes))
        except UnicodeDecodeError:
            tables[base] = pd.read_csv(BytesIO(_file_bytes), encoding="latin-1")

    elif ext in ("xlsx", "xls"):
        sheets = pd.read_excel(BytesIO(_file_bytes), sheet_name=None)
        if len(sheets) == 1:
            tables[base] = next(iter(sheets.values()))
        else:
            for sheet_name, sheet_df in sheets.items():
                tables[f"{base}_{sheet_name}"] = sheet_df

    elif ext == "pdf":
        found = 0
        with pdfplumber.open(BytesIO(_file_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                for t_idx, raw in enumerate(page.extract_tables()):
                    if raw and len(raw) > 1:
                        pdf_df = pd.DataFrame(raw[1:], columns=clean_columns(raw[0]))
                        tables[f"{base}_p{page_num + 1}_t{t_idx + 1}"] = coerce_numeric_columns(pdf_df)
                        found += 1
        if found == 0:
            notes.append(f"⚠️ No tables detected in '{file_name}'. PDF extraction works best on simple, clearly-bordered tables.")
    return tables, notes


@st.cache_resource(show_spinner="Joining tables...", max_entries=3)
def compute_join(cache_key, _tables, base_table, steps_json):
    """Chain-join ek baar compute hota hai; widgets badalne par dobara nahi chalta."""
    steps = json.loads(steps_json)
    result = _tables[base_table]
    cols_per_step = []
    for i, step in enumerate(steps):
        try:
            result = result.merge(_tables[step["table"]], left_on=step["left_key"],
                                  right_on=step["right_key"], how=step["join_type"])
        except Exception as e:
            raise ValueError(f"Join step {i + 1} failed: {e}")
        cols_per_step.append(result.columns.tolist())
    return result, cols_per_step


@st.cache_resource(show_spinner="Preparing your data for AI questions...", max_entries=2)
def get_upload_connection(data_key, _df):
    """Uploaded data ka in-memory SQLite ek baar banta hai, har 'Ask' click pe nahi."""
    conn_ = sqlite3.connect(":memory:", check_same_thread=False)
    _df.to_sql("uploaded_data", conn_, index=False, if_exists="replace", chunksize=5000)
    return conn_


def profile_dataframe(df):
    """Fast local statistical profile -- AI report isi par based hoti hai (real numbers)."""
    n_rows, n_cols = df.shape
    sample = df.sample(50000, random_state=42) if n_rows > 50000 else df

    column_profiles = []
    for c in list(df.columns)[:MAX_PROFILE_COLUMNS]:
        s = df[c]
        try:
            unique = int(s.nunique())
        except Exception:
            unique = -1
        info = {"column": str(c), "type": str(s.dtype),
                "missing_pct": round(float(s.isna().mean()) * 100, 1), "unique": unique}
        try:
            if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
                ss = sample[c].dropna()
                if len(ss):
                    q1, q3 = ss.quantile(0.25), ss.quantile(0.75)
                    iqr = q3 - q1
                    outliers = int(((ss < q1 - 1.5 * iqr) | (ss > q3 + 1.5 * iqr)).sum()) if iqr > 0 else 0
                    info.update({"min": round(float(ss.min()), 2), "max": round(float(ss.max()), 2),
                                 "mean": round(float(ss.mean()), 2), "median": round(float(ss.median()), 2),
                                 "outliers_in_sample": outliers})
            elif pd.api.types.is_datetime64_any_dtype(s):
                ss = s.dropna()
                if len(ss):
                    info["range"] = f"{ss.min()} to {ss.max()}"
            else:
                top = s.value_counts().head(3)
                info["top_values"] = {str(k)[:40]: int(v) for k, v in top.items()}
        except Exception:
            pass
        column_profiles.append(info)

    num_cols = [c for c in sample.columns
                if pd.api.types.is_numeric_dtype(sample[c]) and not pd.api.types.is_bool_dtype(sample[c])][:15]
    corr_pairs = []
    if len(num_cols) >= 2:
        try:
            corr = sample[num_cols].corr()
            for i, a in enumerate(num_cols):
                for b in num_cols[i + 1:]:
                    v = corr.loc[a, b]
                    if pd.notna(v):
                        corr_pairs.append({"a": str(a), "b": str(b), "r": round(float(v), 2)})
            corr_pairs = sorted(corr_pairs, key=lambda p: abs(p["r"]), reverse=True)[:5]
        except Exception:
            corr_pairs = []

    dup_base = df if n_rows <= 200000 else sample
    try:
        duplicate_rows = int(dup_base.duplicated().sum())
    except Exception:
        duplicate_rows = 0

    return {
        "rows": int(n_rows), "columns": int(n_cols), "columns_profiled": len(column_profiles),
        "missing_cells": int(df.isna().sum().sum()),
        "duplicate_rows": duplicate_rows,
        "duplicates_basis": "all rows" if n_rows <= 200000 else "a 50,000-row sample",
        "column_profiles": column_profiles, "top_correlations": corr_pairs,
    }


def _column_detail(c):
    if "top_values" in c:
        return "Top: " + ", ".join(f"{k} ({v:,})" for k, v in c["top_values"].items())
    if "mean" in c:
        text = f"min {c['min']}, max {c['max']}, mean {c['mean']}, median {c['median']}"
        if c.get("outliers_in_sample"):
            text += f", ~{c['outliers_in_sample']} outliers"
        return text
    if "range" in c:
        return c["range"]
    return "-"


def profile_to_table(profile):
    return pd.DataFrame([{"Column": c["column"], "Type": c["type"], "Missing %": c["missing_pct"],
                          "Unique": c["unique"], "Details": _column_detail(c)}
                         for c in profile["column_profiles"]])


# ============================================================
# SECTION 6: REPORT BUILDERS (AI report, UI, PDF, Excel)
# ============================================================
REPORT_SECTIONS = [
    ("key_findings", "Key Findings"),
    ("data_quality", "Data Quality"),
    ("relationships", "Relationships & Patterns"),
    ("recommendations", "Recommended Next Steps"),
]


@st.cache_data(show_spinner=False)
def generate_data_report(profile_json):
    """Structured AI report. Failure par exception raise hota hai (cache nahi hota)."""
    prompt = f"""You are a senior data analyst writing a detailed report for a business reader.

Here is a statistical profile of the dataset (JSON):
{profile_json}

Return ONLY valid JSON with exactly these keys:
{{
  "overview": "3-4 sentences: what this dataset likely represents, its size, and what questions it can answer",
  "key_findings": ["4-6 specific findings that quote real numbers from the profile"],
  "data_quality": ["2-4 observations about missing values, duplicates, outliers, or suspicious ranges"],
  "relationships": ["2-4 notable relationships or patterns between columns; say clearly if no strong ones exist"],
  "recommendations": ["3-5 concrete next steps: analyses to run, charts to build, or cleaning to do"]
}}
Use ONLY facts present in the profile. Never invent numbers. Plain text strings only, no markdown."""
    report = parse_json_loose(safe_ai_call(prompt).text)
    if not isinstance(report, dict):
        raise ValueError("Report is not a JSON object")
    report["overview"] = str(report.get("overview", ""))
    for key, _ in REPORT_SECTIONS:
        value = report.get(key, [])
        report[key] = [str(i) for i in (value if isinstance(value, list) else [value])]
    return report


def fallback_report(profile):
    """AI na chale tab bhi statistics-based report mil jaaye."""
    cols = profile["column_profiles"]
    missing = [f"{c['column']} has {c['missing_pct']}% missing values" for c in cols if c["missing_pct"] > 0][:6]
    if profile["duplicate_rows"]:
        missing.append(f"{profile['duplicate_rows']:,} duplicate rows found (checked on {profile['duplicates_basis']}).")
    return {
        "overview": (f"This dataset has {profile['rows']:,} rows and {profile['columns']} columns. "
                     "The AI-written narrative is unavailable right now, so this report shows statistics only."),
        "key_findings": [f"{c['column']}: {_column_detail(c)}" for c in cols[:6]],
        "data_quality": missing or ["No missing values or duplicates detected."],
        "relationships": [f"{p['a']} and {p['b']}: correlation {p['r']}" for p in profile["top_correlations"]]
                         or ["No numeric correlations to report."],
        "recommendations": ["Click 'Generate Report' again in a minute to get the AI-written analysis."],
    }


def show_report(report, profile):
    """Report ko UI mein dikhata hai (metrics + tabs)."""
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", f"{profile['rows']:,}")
    c2.metric("Columns", f"{profile['columns']}")
    c3.metric("Missing cells", f"{profile['missing_cells']:,}")
    c4.metric("Duplicate rows", f"{profile['duplicate_rows']:,}", help=f"Checked on {profile['duplicates_basis']}")

    st.markdown("#### Overview")
    st.write(md_safe(report["overview"]))

    tab_titles = ["🔎 Key Findings", "🧹 Data Quality", "🔗 Relationships", "✅ Next Steps", "📋 Column Profile"]
    tabs = st.tabs(tab_titles)
    for tab, (key, _) in zip(tabs[:4], REPORT_SECTIONS):
        with tab:
            for item in (report.get(key) or ["Nothing notable."]):
                st.markdown(f"- {md_safe(item)}")
    with tabs[4]:
        st.dataframe(profile_to_table(profile), width="stretch", hide_index=True)


_PDF_REPLACEMENTS = {"≈": "~", "→": "->", "≥": ">=", "≤": "<=", "…": "...", "\u2011": "-", "\u00a0": " "}


def pdf_safe(text):
    """PDF ke standard font ke liye text safe + XML-escaped banata hai."""
    text = str(text)
    for a, b in _PDF_REPLACEMENTS.items():
        text = text.replace(a, b)
    text = text.encode("cp1252", "replace").decode("cp1252")
    return escape(text)


def build_pdf_export(working_df, report, profile):
    """Formatted PDF: overview + sections + column profile + data preview. Returns bytes."""
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("T", parent=styles["Heading1"], textColor=colors.HexColor("#7c3aed"))
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], textColor=colors.HexColor("#4c1d95"), spaceBefore=12)
    body = ParagraphStyle("B", parent=styles["BodyText"], leading=14)
    bullet = ParagraphStyle("Bul", parent=body, leftIndent=14, bulletIndent=2, spaceAfter=3)
    cell = ParagraphStyle("Cell", parent=styles["BodyText"], fontSize=7, leading=9)
    cell_head = ParagraphStyle("CellH", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")

    def styled_table(rows, widths):
        t = Table(rows, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7c3aed")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c4b5fd")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f0ff")]),
        ]))
        return t

    el = [Paragraph("Data Insight Report", title), Spacer(1, 6),
          Paragraph(pdf_safe(f"{profile['rows']:,} rows x {profile['columns']} columns | "
                             f"{profile['missing_cells']:,} missing cells | "
                             f"{profile['duplicate_rows']:,} duplicate rows"), body),
          Paragraph("Overview", h2), Paragraph(pdf_safe(report["overview"]), body)]

    for key, label in REPORT_SECTIONS:
        el.append(Paragraph(label, h2))
        for item in (report.get(key) or ["Nothing notable."]):
            el.append(Paragraph(pdf_safe(item), bullet, bulletText="\u2022"))

    el.append(Paragraph("Column Profile", h2))
    prof = profile_to_table(profile)
    rows = [[Paragraph(h, cell_head) for h in prof.columns]]
    for rec in prof.values.tolist():
        rows.append([Paragraph(pdf_safe(v), cell) for v in rec])
    el.append(styled_table(rows, [105, 55, 50, 45, 255]))

    preview = working_df.iloc[:10, :8]
    el.append(Paragraph(f"Data Preview (first 10 rows, first {preview.shape[1]} columns)", h2))
    width = 510 / max(preview.shape[1], 1)
    rows = [[Paragraph(pdf_safe(str(c)[:16]), cell_head) for c in preview.columns]]
    for rec in preview.values.tolist():
        rows.append([Paragraph(pdf_safe("" if pd.isna(v) else str(v)[:16]), cell) for v in rec])
    el.append(styled_table(rows, [width] * preview.shape[1]))

    doc.build(el)
    return output.getvalue()


def build_excel_export(working_df, report, profile):
    """Excel: Summary + Column Profile + Data (capped). Returns bytes."""
    rows = [("Overview", report["overview"])]
    for key, label in REPORT_SECTIONS:
        rows += [(label, item) for item in report.get(key, [])]

    export_df = working_df.head(MAX_EXCEL_ROWS).copy()
    for c in export_df.columns:
        if isinstance(export_df[c].dtype, pd.DatetimeTZDtype):
            export_df[c] = export_df[c].dt.tz_localize(None)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(rows, columns=["Section", "Detail"]).to_excel(writer, sheet_name="Summary", index=False)
        profile_to_table(profile).to_excel(writer, sheet_name="Column Profile", index=False)
        export_df.to_excel(writer, sheet_name="Data", index=False)

        ws = writer.sheets["Summary"]
        ws.column_dimensions["A"].width = 26
        ws.column_dimensions["B"].width = 120
        for row in ws.iter_rows(min_row=2):
            row[1].alignment = Alignment(wrap_text=True, vertical="top")
        wp = writer.sheets["Column Profile"]
        for letter_, width in zip("ABCDE", (28, 14, 12, 10, 90)):
            wp.column_dimensions[letter_].width = width
    return output.getvalue()


# ============================================================
# SECTION 7: CHART RENDERING
# Heavy data par bhi fast: aggregate / sample karke hi plot hota hai.
# ============================================================
def _text(d, n=10):
    return d.head(n).round(2).to_string(index=False)


def render_chart(working_df, chart_type, x_axis, y_axis, color_arg):
    """Returns (figure, facts). facts = exactly jo plot hua uska chhota summary (AI insight ke liye)."""
    fig, facts = None, ""
    if color_arg in (x_axis, y_axis):
        color_arg = None
    group_cols = [x_axis] + ([color_arg] if color_arg else [])

    try:
        if chart_type == "Bar":
            if y_axis == "(count)":
                data = working_df.groupby(group_cols).size().reset_index(name="count")
                fig = px.bar(data, x=x_axis, y="count", color=color_arg, barmode="group", title=f"Count by {x_axis}")
                facts = _text(data.sort_values("count", ascending=False))
            else:
                data = working_df.groupby(group_cols)[y_axis].mean().reset_index()
                fig = px.bar(data, x=x_axis, y=y_axis, color=color_arg, barmode="group",
                             title=f"Average {y_axis} by {x_axis}")
                facts = _text(data.sort_values(y_axis, ascending=False))

        elif chart_type == "Line":
            if y_axis == "(count)":
                data = working_df.groupby(x_axis).size().reset_index(name="count").sort_values(x_axis)
                fig = px.line(data, x=x_axis, y="count", title=f"Count by {x_axis}")
                facts = _text(data)
            else:
                data = working_df.groupby(group_cols)[y_axis].mean().reset_index()
                if len(data) > MAX_PLOT_POINTS:
                    data = data.sample(MAX_PLOT_POINTS, random_state=42)
                data = data.sort_values(x_axis)
                fig = px.line(data, x=x_axis, y=y_axis, color=color_arg, title=f"Average {y_axis} over {x_axis}")
                facts = (f"{len(data)} points. {y_axis} stats: {data[y_axis].describe().round(2).to_dict()}. "
                         f"First x={data[x_axis].iloc[0]}, last x={data[x_axis].iloc[-1]}")

        elif chart_type == "Scatter":
            if y_axis == "(count)":
                st.warning("Scatter plot needs a numeric Y-axis, not count.")
            else:
                data = working_df if len(working_df) <= MAX_SCATTER_POINTS else working_df.sample(MAX_SCATTER_POINTS, random_state=42)
                fig = px.scatter(data, x=x_axis, y=y_axis, color=color_arg, title=f"{y_axis} vs {x_axis}",
                                 render_mode="svg")
                facts = f"{len(data)} points plotted. "
                if all(pd.api.types.is_numeric_dtype(data[c]) for c in (x_axis, y_axis)):
                    facts += f"Correlation between {x_axis} and {y_axis}: {data[x_axis].corr(data[y_axis]):.2f}. "
                facts += data[[x_axis, y_axis]].describe().round(2).to_string()

        elif chart_type == "Pie":
            data = working_df[x_axis].value_counts().reset_index().head(10)
            data.columns = [x_axis, "count"]
            fig = px.pie(data, names=x_axis, values="count", title=f"Distribution of {x_axis}")
            facts = _text(data)

        elif chart_type == "Box Plot":
            if y_axis == "(count)":
                st.warning("Box plot needs a numeric Y-axis.")
            else:
                data = working_df if len(working_df) <= MAX_PLOT_POINTS else working_df.sample(MAX_PLOT_POINTS, random_state=42)
                fig = px.box(data, x=x_axis, y=y_axis, color=color_arg, title=f"{y_axis} distribution by {x_axis}")
                stats = data.groupby(x_axis)[y_axis].describe()[["count", "mean", "50%", "min", "max"]].reset_index()
                facts = _text(stats.sort_values("count", ascending=False))

    except Exception as e:
        st.warning(f"⚠️ Couldn't build this chart: {e}")
        return None, ""
    return fig, facts


def show_answer(answer, all_results, timings=None):
    st.markdown(f"**💡 Answer:** {md_safe(answer)}")
    if timings:
        st.caption("⏱ " + " · ".join(f"{k} {v:.1f}s" for k, v in timings.items())
                   + f" · total {sum(timings.values()):.1f}s")
    with st.expander("See analysis details"):
        for q, res in all_results:
            st.code(q, language="sql")
            if isinstance(res, pd.DataFrame):
                st.dataframe(res, width="stretch")
            else:
                st.write(res)


# ============================================================
# SECTION 8: PAGE -- HEADER + DEFAULT INSTACART DASHBOARD
# Dashboard pehle saved snapshot (src/dashboard_snapshot.json) se aata hai: instant, aur free-tier
# database par koi load nahi. Snapshot na ho to live database se chhote aggregate queries chalti hain.
# Snapshot banane ke liye: python make_dashboard_snapshot.py
# ============================================================
SNAPSHOT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard_snapshot.json")


def load_snapshot():
    try:
        with open(SNAPSHOT_PATH, encoding="utf-8") as f:
            data = json.load(f)
        dept = pd.DataFrame(data["departments"])
        dept["order_count"] = dept["order_count"].astype(int)
        dept["reorder_rate"] = dept["reorder_rate"].astype(float)
        k = data["kpis"]
        kpis = {"total_orders": int(k["total_orders"]), "total_products": int(k["total_products"]),
                "reorder_rate": float(k["reorder_rate"])}
        return kpis, dept, str(data.get("created", ""))
    except Exception:
        return None


@st.cache_data(ttl=86400, show_spinner="Loading dashboard...")
def load_dashboard_stats(_engine):
    kpis = pd.read_sql_query(
        "SELECT COUNT(DISTINCT order_id) AS total_orders, COUNT(DISTINCT product_id) AS total_products, "
        "AVG(reordered) AS reorder_rate FROM order_products_full", _engine)
    dept = pd.read_sql_query(
        "SELECT department, COUNT(*) AS order_count, AVG(reordered) AS reorder_rate "
        "FROM order_products_full GROUP BY department", _engine)
    dept["order_count"] = dept["order_count"].astype(int)
    dept["reorder_rate"] = dept["reorder_rate"].astype(float)
    row = kpis.iloc[0]
    return {"total_orders": int(row["total_orders"]), "total_products": int(row["total_products"]),
            "reorder_rate": float(row["reorder_rate"])}, dept


st.title("🛒 AI-Powered Retail Insight Agent")
st.write("Statistical + AI-driven analytics on Instacart data")

dashboard, dashboard_note, dashboard_error = None, "", ""
_t_dash = time.time()
_snapshot = load_snapshot()
if _snapshot is not None:
    dashboard = _snapshot[:2]
    dashboard_note = (f"⚡ Pre-computed snapshot of the Instacart sample ({_snapshot[2] or 'saved'}): loads instantly and "
                      "spares the free-tier database. The AI chat below queries the live database.")
elif main_conn is not None:
    try:
        dashboard = load_dashboard_stats(main_conn)
    except Exception as e:
        dashboard_error = f"{type(e).__name__}: {str(e)[:400]}"
else:
    dashboard_error = db_error or "Database is not configured."
PERF["dashboard data"] = time.time() - _t_dash

if dashboard is not None:
    kpis, dept_stats = dashboard
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Orders", f"{kpis['total_orders']:,}")
    col2.metric("Total Products", f"{kpis['total_products']:,}")
    col3.metric("Overall Reorder Rate", f"{kpis['reorder_rate'] * 100:.1f}%")
    if dashboard_note:
        st.caption(dashboard_note)

    st.divider()
    st.subheader("📊 Department Insights")
    col1, col2 = st.columns(2)
    with col1:
        top_volume = dept_stats.sort_values("order_count", ascending=False).head(10)
        st.plotly_chart(px.bar(top_volume, x="department", y="order_count",
                               title="Top 10 Departments by Order Volume"), width="stretch")
    with col2:
        top_reorder = dept_stats.sort_values("reorder_rate", ascending=False).head(10)
        st.plotly_chart(px.bar(top_reorder, x="department", y="reorder_rate",
                               title="Top 10 Departments by Reorder Rate"), width="stretch")
else:
    st.info("The default Instacart dashboard is unavailable right now. You can still upload your own data below.")
    with st.expander("Technical details"):
        st.code(dashboard_error or db_error or "No dashboard snapshot found and no database connection.")

# ============================================================
# SECTION 9: SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("### About")
    st.write("Built by Bhaskar — AI-powered retail analytics")
    st.markdown("📧 [sparsh4142@gmail.com](mailto:sparsh4142@gmail.com)")
    st.markdown("🔗 [GitHub](https://github.com/Bhaskar-Black)")
    st.markdown("🔗 [LinkedIn](https://linkedin.com/in/bhaskarstackanalyst)")

# ============================================================
# SECTION 10: UPLOAD YOUR OWN DATA
# upload -> (join) -> AI chart -> AI chat -> detailed report
# ============================================================
st.divider()
st.header("📁 Upload Your Own Data")
st.write("Upload one or more files (CSV, Excel, or PDF) — join them, visualize, ask AI questions, and export a report.")

working_df = None  # active uploaded / joined dataframe
pending_insight = None  # AI chart insight page ke END mein fill hota hai (UI pehle dikh jaata hai)
insight_slot = None

uploaded_files = st.file_uploader("Choose file(s) — CSV, Excel, or PDF",
                                  type=["csv", "xlsx", "xls", "pdf"], accept_multiple_files=True)

if uploaded_files:
    # ---- 10a: unique id for this exact set of uploaded files ----
    signature = tuple(sorted(getattr(f, "file_id", None) or f"{f.name}-{f.size}" for f in uploaded_files))
    sig_id = abs(hash(signature)) % 10**8

    # ---- 10b: parse files (cached) ----
    tables = {}
    _t_parse = time.time()
    for f in uploaded_files:
        try:
            fid = getattr(f, "file_id", None) or f"{f.name}-{f.size}"
            file_tables, notes = parse_uploaded_file(fid, f.name, f.getvalue())
            tables.update(file_tables)
            for note in notes:
                st.warning(note)
        except Exception as e:
            st.error(f"⚠️ Couldn't read '{f.name}': {e}")

    PERF["file parse (cached after 1st)"] = time.time() - _t_parse

    if not tables:
        st.stop()

    st.success(f"Loaded {len(tables)} table(s): {', '.join(tables.keys())}")
    with st.expander("Preview tables"):
        for name, tdf in tables.items():
            st.markdown(f"**{name}** ({len(tdf):,} rows)")
            st.dataframe(tdf.head(5), width="stretch")

    # ---- 10c: single table ya multi-table chain join ----
    if len(tables) == 1:
        working_df = next(iter(tables.values()))
        steps_json = ""
        wk = str(sig_id)
        st.info("Only one table uploaded — using it directly.")
    else:
        st.subheader("🔗 Join Your Tables")
        st.write("Start with a base table, then add tables one by one by choosing the join column each time.")

        table_names = list(tables.keys())
        base_table = st.selectbox("Start with base table", table_names, key=f"base_table_{sig_id}")
        wk = f"{sig_id}_{abs(hash(base_table)) % 10**6}"

        # naya upload / naya base table => purane join steps clear
        if st.session_state.get("last_base") != (sig_id, base_table):
            st.session_state["join_steps"] = []
            st.session_state["last_base"] = (sig_id, base_table)
        steps = st.session_state["join_steps"]
        steps_json = json.dumps(steps)

        try:
            joined_df, cols_per_step = compute_join(f"{sig_id}|{base_table}", tables, base_table, steps_json)
        except Exception as e:
            st.error(f"⚠️ {e}")
            joined_df, cols_per_step = None, []

        current_cols = cols_per_step[-1] if cols_per_step else tables[base_table].columns.tolist()
        already = {base_table} | {s["table"] for s in steps}
        remaining_tables = [t for t in table_names if t not in already]

        if remaining_tables and joined_df is not None:
            st.markdown("**Add a table to join:**")
            n = len(steps)
            c1, c2, c3 = st.columns(3)
            with c1:
                next_table = st.selectbox("Join with", remaining_tables, key=f"next_table_{wk}_{n}")
            with c2:
                left_key = st.selectbox("Column from current data", current_cols, key=f"left_key_{wk}_{n}")
            with c3:
                right_key = st.selectbox(f"Column from {next_table}", tables[next_table].columns.tolist(),
                                         key=f"right_key_{wk}_{n}_{abs(hash(next_table)) % 10**6}")
            join_type = st.selectbox("Join type", ["left", "inner", "right", "outer"], index=0,
                                     key=f"join_type_{wk}_{n}")
            if st.button("➕ Add This Join", key=f"add_join_{wk}_{n}"):
                st.session_state["join_steps"].append({"table": next_table, "left_key": left_key,
                                                       "right_key": right_key, "join_type": join_type})
                st.rerun()
        elif joined_df is not None:
            st.caption("All uploaded tables are already joined.")

        if steps:
            if joined_df is not None:
                st.success(f"Joined {len(steps) + 1} tables → {len(joined_df):,} rows, {len(joined_df.columns)} columns.")
                biggest_input = max([len(tables[base_table])] + [len(tables[s["table"]]) for s in steps])
                if len(joined_df) > 5 * biggest_input:
                    st.warning("⚠️ The joined table is much larger than the inputs — the join column probably has "
                               "duplicate values. Check the join keys.")
                with st.expander("Preview joined data"):
                    st.dataframe(joined_df.head(10), width="stretch")
            if st.button("🔄 Reset Joins", key=f"reset_{wk}"):
                st.session_state["join_steps"] = []
                st.rerun()
        else:
            st.info("Only the base table is active. Add a join above to combine tables, or visualize it as-is.")

        working_df = joined_df

    data_key = f"{signature}|{steps_json}"

    # ---- 10d: column selection + AI-recommended chart + manual override ----
    if working_df is not None and not working_df.empty:

        st.subheader("📊 Choose up to 4 columns to visualize")
        selected_cols = st.multiselect("Select columns", options=working_df.columns.tolist(),
                                       max_selections=4, key=f"viz_cols_{wk}")

        if selected_cols:
            ck = f"{wk}_{abs(hash(tuple(selected_cols))) % 10**6}"
            st.markdown("#### 🤖 AI-Recommended Chart")
            _t_rec = time.time()
            with st.spinner("Picking the best chart for this data..."):
                recommendation = recommend_chart(working_df, selected_cols, data_key)
            PERF["chart recommendation (AI; cached after 1st)"] = time.time() - _t_rec

            use_recommended = st.toggle("Use AI recommendation", value=True, key="use_ai_chart")

            if use_recommended:
                chart_type = recommendation["chart_type"]
                x_axis = recommendation["x"]
                y_axis = recommendation["y"] if recommendation["y"] in (selected_cols + ["(count)"]) else "(count)"
                color_by = recommendation.get("color_by")
                color_arg = color_by if color_by in selected_cols else None
                st.caption(f"AI picked: **{chart_type}** — X: `{x_axis}`, Y: `{y_axis}`"
                           + (f", grouped by `{color_arg}`" if color_arg else ""))
            else:
                st.markdown("##### 🎨 Build Your Own Chart")
                chart_type = st.selectbox("Chart type", ["Bar", "Line", "Scatter", "Pie", "Box Plot"], key="chart_type")
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    x_axis = st.selectbox("X-axis", selected_cols, key=f"x_axis_{ck}")
                with col_b:
                    y_axis = st.selectbox("Y-axis", ["(count)"] + [c for c in selected_cols if c != x_axis],
                                          key=f"y_axis_{ck}_{abs(hash(x_axis)) % 10**6}")
                with col_c:
                    color_options = ["(none)"] + [c for c in selected_cols if c not in [x_axis, y_axis]]
                    color_by = st.selectbox("Group/Color by (optional)", color_options,
                                            key=f"color_by_{ck}_{abs(hash((x_axis, y_axis))) % 10**6}")
                color_arg = None if color_by == "(none)" else color_by

            # X-axis mein bahut saari unique values hon to user khud choose kare kin ko compare karna hai
            unique_count, unique_vals = cached_unique_values(data_key, x_axis, working_df)
            if unique_count > 15 and chart_type in ["Bar", "Pie", "Box Plot"]:
                st.write(f"'{x_axis}' has {unique_count:,} unique values — pick specific ones to compare:")
                chosen = st.multiselect(f"Select values of {x_axis} to compare", options=unique_vals,
                                        default=unique_vals[:5], key=f"entity_filter_{ck}_{abs(hash(x_axis)) % 10**6}")
                chart_df = working_df[working_df[x_axis].isin(chosen)] if chosen else working_df.head(0)
                if not chosen:
                    st.info("Select at least one value to draw the chart.")
            else:
                chart_df = working_df

            if not chart_df.empty:
                fig, facts = render_chart(chart_df, chart_type, x_axis, y_axis, color_arg)
                if fig:
                    st.plotly_chart(fig, width="stretch")
                    insight_slot = st.empty()
                    pending_insight = (f"{y_axis} by {x_axis}", chart_type, facts)

        # ---- 10e: AI chat on uploaded data ----
        st.divider()
        st.subheader("💬 Ask AI About Your Uploaded Data")
        upload_question = st.text_input("Ask a question about your uploaded data", key="upload_question")

        if st.button("Ask", key="upload_ask_button") and upload_question:
            with st.spinner("Analyzing..."):
                try:
                    upload_conn = get_upload_connection(data_key, working_df)
                    queries, all_results, answer, timings = run_ai_query(
                        upload_question, upload_conn, describe_schema(working_df), dialect="SQLite")
                    show_answer(answer, all_results, timings)
                except Exception as e:
                    st.error(f"⚠️ Something went wrong: {e}")

        # ---- 10f: detailed report (UI + PDF + Excel + CSV) ----
        st.divider()
        st.subheader("📄 Detailed Data Report")
        st.write("Get a full AI-written report — overview, findings, data quality, relationships, next steps — "
                 "and download it as PDF or Excel, or export the data as CSV.")

        report_key = f"{data_key}|{working_df.shape}"

        if st.button("Generate Report", key="generate_report"):
            with st.spinner("Profiling your data and writing the report (about 10 seconds)..."):
                profile = profile_dataframe(working_df)
                try:
                    report, ai_ok = generate_data_report(json.dumps(profile, default=str)), True
                except Exception:
                    report, ai_ok = fallback_report(profile), False
                st.session_state["report"] = {
                    "key": report_key, "ai_ok": ai_ok, "profile": profile, "report": report,
                    "pdf": build_pdf_export(working_df, report, profile),
                    "excel": build_excel_export(working_df, report, profile),
                    "csv": working_df.head(MAX_CSV_ROWS).to_csv(index=False).encode("utf-8"),
                }

        saved = st.session_state.get("report")
        if saved and saved["key"] == report_key:
            if not saved["ai_ok"]:
                st.warning("AI narrative is unavailable right now, so this is a statistics-only report. "
                           "Click 'Generate Report' again in a minute.")
            show_report(saved["report"], saved["profile"])

            d1, d2, d3 = st.columns(3)
            with d1:
                st.download_button("⬇️ Download PDF Report", data=saved["pdf"],
                                   file_name="data_insight_report.pdf", mime="application/pdf")
            with d2:
                st.download_button("⬇️ Download Excel Report", data=saved["excel"],
                                   file_name="data_insight_report.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            with d3:
                st.download_button("⬇️ Download Data (CSV)", data=saved["csv"],
                                   file_name="data_export.csv", mime="text/csv")
            st.caption(f"Excel includes the first {MAX_EXCEL_ROWS:,} rows and the CSV the first {MAX_CSV_ROWS:,} rows "
                       "to keep downloads fast.")

# ============================================================
# SECTION 11: AI CHAT ON DEFAULT INSTACART DATA
# (sirf tab dikhta hai jab user ne apna data upload nahi kiya)
# ============================================================
if working_df is None:
    st.divider()
    st.subheader("💬 Ask the Default Instacart Data (AI-Powered)")

    if main_conn is None:
        st.info("Default database is unavailable right now.")
    else:
        default_question = st.text_input("Ask a question about the Instacart data", key="default_question")
        if st.button("Ask", key="default_ask_button") and default_question:
            with st.spinner("Analyzing..."):
                queries, all_results, answer, timings = run_ai_query(
                    default_question, main_conn, MAIN_SCHEMA, dialect="PostgreSQL")
            show_answer(answer, all_results, timings)

# ============================================================
# SECTION 12: DEFERRED AI CHART INSIGHT + PERFORMANCE PANEL
# Page pehle poora dikh jaata hai; AI insight bad mein chart ke neeche aa jaata hai.
# ============================================================
PERF["page ready (before AI insight)"] = time.time() - _SCRIPT_START

if pending_insight and insight_slot is not None:
    _t_ins = time.time()
    with insight_slot.container():
        with st.spinner("AI is reading your chart..."):
            try:
                _insight_text = get_chart_insight(*pending_insight)
            except Exception:
                _insight_text = "AI insight unavailable right now — try again in a moment."
        st.info(f"💡 {md_safe(_insight_text)}")
    PERF["chart insight (AI; cached after 1st)"] = time.time() - _t_ins

with st.sidebar.expander("⚡ Performance (last run)"):
    for _step, _sec in PERF.items():
        st.write(f"{_step}: **{_sec:.2f}s**")