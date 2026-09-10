# 🛒 AI-Powered Retail Insight Agent

A statistically-verified, AI-queryable analytics tool built on 3.4M+ real Instacart grocery orders. Instead of just displaying dashboards, this system lets users ask business questions in plain English and get AI-generated, statistically-grounded answers — combining traditional BI with a natural-language reasoning layer.

**[🔗 Live Demo](#)** *(add link after deployment)* | **[📊 GitHub](https://github.com/Bhaskar-Black/ai-insight-agent)**

---

## Why This Project

Most entry-level data analytics portfolios stop at "SQL + Power BI dashboard." This project goes further by asking: *what if the dashboard could reason about the data the way an analyst would?*

Instead of only using AI tools (like Power BI Copilot), this project **engineers** an AI layer from scratch — one that plans its own queries, validates patterns statistically, and gives business-language recommendations, not just raw numbers.

---

## What It Does

- 📊 **Interactive dashboard** — KPIs and visualizations on department-level ordering and reorder behavior
- 🧪 **Statistically validated insights** — findings are backed by hypothesis testing (Chi-square, T-test, ANOVA), not just eyeballed trends
- 💬 **AI-powered natural language querying** — ask a question in plain English; the system plans the right SQL queries, runs them, and synthesizes a business-focused answer
- 🧠 **Multi-step reasoning** — for strategic questions ("how do I increase sales of X"), the AI gathers multiple pieces of context before answering, rather than returning a single raw number

---

## Tech Stack

| Layer | Tools |
|---|---|
| Data processing | Python, Pandas |
| Statistics | SciPy (Chi-square, T-test, ANOVA) |
| Database | SQLite |
| AI / LLM | Google Gemini API |
| Dashboard / UI | Streamlit, Plotly |
| Version control | Git, GitHub |

---

## Dataset

[Instacart Market Basket Analysis](https://www.kaggle.com/competitions/instacart-market-basket-analysis) — 3.4M+ real, anonymized grocery orders across ~50,000 products, 21 departments, and 134 aisles.

---

## Key Statistical Findings

1. **Reorder behavior varies significantly by department** (Chi-square test, χ² = 9773.5, p < 0.001) — Dairy Eggs has a 67.5% reorder rate vs. 33.7% for Personal Care, showing fresh/perishable categories are habit-driven while discretionary categories are planned/infrequent purchases.

2. **Cart-addition order reflects shopping priorities** (T-test, p < 0.001) — Produce is added to cart significantly earlier than Snacks (avg. position 8.43 vs. 9.56), suggesting essentials are prioritized over discretionary items.

3. **Cart position differs significantly across departments** (ANOVA, F = 2494.29, p < 0.001) — Beverages and Dairy are added early (planned purchases); Frozen and Snacks are added late (impulse/secondary purchases).

**Business takeaway:** These patterns could inform personalization features — e.g., reorder reminders prioritized for high-reorder categories, or cart-suggestion ordering aligned with natural shopping sequence.

---

## How the AI Layer Works

1. User asks a question in plain English via the dashboard
2. Gemini plans the SQL query (or queries, for complex/strategic questions) needed to answer it
3. Queries run against the SQLite database
4. Results are passed back to Gemini, which synthesizes a clear, business-focused answer — with specific numbers and, for strategic questions, concrete recommendations

---

## Screenshots

*(Add 2–3 screenshots here: dashboard view, AI chat in action, a chart)*

---

## Running Locally

\`\`\`bash
# Clone the repo
git clone https://github.com/Bhaskar-Black/ai-insight-agent.git
cd ai-insight-agent

# Set up virtual environment
python -m venv venv
venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Add your Gemini API key
echo GEMINI_API_KEY=your-key-here > .env

# Download the Instacart dataset from Kaggle and place CSVs in /raw

# Run the notebook once to build the database (notebooks/01_eda.ipynb)

# Launch the app
streamlit run src/app.py
\`\`\`

---

## What I'd Improve Next

- Support for uploading any CSV dataset (auto schema detection) instead of a fixed dataset
- Connect to a live/streaming data source instead of a static snapshot
- Add conversation memory so follow-up questions build on prior context
- Deploy with a proper hosted database instead of a local SQLite file

---

## About Me

Built by **Bhaskar** , exploring the intersection of data analytics and applied AI.

📧 [sparsh4142@gmail.com](mailto:sparsh4142@gmail.com) · [GitHub](https://github.com/Bhaskar-Black) · [LinkedIn](https://linkedin.com/in/bhaskarstackanalyst)