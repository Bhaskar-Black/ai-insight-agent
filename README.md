Readme · MD
# 🛒 AI-Powered Retail Insight Agent
 
A statistically-verified, AI-driven analytics tool. Ask business questions in plain English and get answers grounded in real SQL results, or upload your own CSV, Excel or PDF files, join them, visualize them and export a full AI-written report. It combines traditional BI with an AI reasoning layer that I engineered from scratch.
 
**[🔗 Live Demo](https://ai-insight-agent-dqswbdy4bysje2j8y6rhmr.streamlit.app/)**
 
---
 
## Why This Project
 
Most entry-level analytics portfolios stop at "SQL + a Power BI dashboard". This project asks a different question: *what if the dashboard could reason about the data the way an analyst does?*
 
Instead of only using AI tools (like Power BI Copilot), it **builds** the AI layer: one that plans its own queries, checks them for safety, runs them, and explains the result in business language using only the numbers it actually retrieved.
 
---
 
## What It Does
 
### 1. Instacart analytics dashboard
- KPIs and department-level charts built from 3.4M+ real grocery orders
- Findings backed by hypothesis testing (Chi-square, T-test, ANOVA), not eyeballed trends
### 2. Ask questions in plain English
- The AI plans one or more SQL queries, runs them, and writes a business-focused answer
- Strategic questions ("how do I increase snack sales?") trigger multi-step reasoning: the system gathers several pieces of context before recommending anything
- Every answer has an expandable view of the exact SQL and raw results, so nothing is a black box
### 3. Bring your own data
- **Upload CSV, Excel (multi-sheet) or PDF** files; tables inside PDFs are extracted automatically
- **Chain-join any number of tables** with a point-and-click join builder (choose base table, join column, join type)
- **AI-recommended chart**: the AI looks at your selected columns and picks the best chart type and axes; switch it off to build your own (Bar, Line, Scatter, Pie, Box Plot, with optional group-by)
- **Entity picker** for columns with many categories, so you compare exactly the values you care about
- **Ask AI about your own data**, with the same plan, run and explain pipeline as above
- **Detailed report**: overview, key findings, data-quality checks, relationships, next steps and a full column profile. Download as **PDF**, **Excel** or export the data as **CSV**
---
 
## Engineering Highlights
 
| Concern | What I did |
|---|---|
| **Safety** | AI-generated SQL is validated before it runs: read-only `SELECT`/`WITH` only, single statement, destructive keywords blocked (whole-word match, so a column like `created_at` still works) |
| **Honest AI** | The report is built from a locally computed statistical profile and chart insights from the exact numbers plotted. The AI explains real figures instead of inventing them |
| **Reliability** | Automatic retry with backoff on temporary AI overload or rate limits, plus graceful fallbacks: a statistics-only report if the AI is down, and a rule-based chart recommendation if the AI call fails |
| **Speed** | File parsing, joins, column profiles and the upload database are cached. Charts aggregate or sample before plotting, the AI is asked for low-latency responses, and the page renders before slower AI insights fill in. A built-in performance panel shows where time goes |
| **Cloud deployment** | Streamlit Community Cloud + Supabase (PostgreSQL), with secrets kept out of the repo |
| **Robustness on messy data** | CSV encoding fallback, duplicate or blank column names from PDFs fixed, text-numbers coerced to numeric, unsupported charts warn instead of crashing, and a warning when a join multiplies rows (usually a duplicate-key problem) |
 
---
 
## Tech Stack
 
| Layer | Tools |
|---|---|
| Data processing | Python, Pandas |
| Statistics | SciPy (Chi-square, T-test, ANOVA) |
| Databases | PostgreSQL on Supabase (default dataset), in-memory SQLite (uploaded data) |
| AI / LLM | Google Gemini API |
| Dashboard / UI | Streamlit, Plotly |
| File handling and reports | openpyxl, pdfplumber, ReportLab |
| Data access | SQLAlchemy |
 
---
 
## Dataset
 
[Instacart Market Basket Analysis](https://www.kaggle.com/competitions/instacart-market-basket-analysis): 3.4M+ real, anonymized grocery orders across ~50,000 products, 21 departments and 134 aisles.
 
> **Note on the live demo:** the hosted version runs on a representative sample (100K orders, 200K order-product rows) so it fits a free-tier database. The statistical findings below were computed on the **full dataset** locally.
 
---
 
## Key Statistical Findings
 
1. **Reorder behavior varies significantly by department** (Chi-square, χ² = 9773.5, p < 0.001): Dairy Eggs has a 67.5% reorder rate vs. 33.7% for Personal Care, which suggests fresh and perishable categories are habit-driven while discretionary ones are planned, infrequent purchases.
2. **Cart-addition order reflects shopping priorities** (T-test, p < 0.001): Produce is added to the cart significantly earlier than Snacks (average position 8.43 vs. 9.56), suggesting essentials come first and discretionary items later.
3. **Cart position differs significantly across departments** (ANOVA, F = 2494.29, p < 0.001): Beverages and Dairy are added early (planned purchases); Frozen and Snacks are added late (impulse or secondary purchases).
**Business takeaway:** these patterns could drive personalization, for example reorder reminders prioritized for high-reorder categories, or cart suggestions ordered to match the natural shopping sequence.
 
---
 
## How the AI Layer Works
 
1. The user asks a question in plain English
2. Gemini plans the SQL query (or several, for strategic questions) against the active schema
3. Each query passes the safety guard and runs against the right database (PostgreSQL for the default data, in-memory SQLite for uploaded data)
4. The results go back to Gemini, which writes a business-focused answer using only the returned numbers
The same engine serves both the default dataset and uploaded files; only the connection and schema change.
 
<!-- Screenshots: add images to a /screenshots folder, then uncomment.
## Screenshots
![Dashboard](screenshots/dashboard.png)
![AI chat](screenshots/ai-chat.png)
![Upload, join and chart](screenshots/upload.png)
![Report](screenshots/report.png)
-->
 
---
 
## Running Locally
 
```bash
# Clone the repo
git clone https://github.com/Bhaskar-Black/ai-insight-agent.git
cd ai-insight-agent
 
# Create and activate a virtual environment (Windows)
python -m venv venv
venv\Scripts\activate
 
# Install dependencies
pip install -r requirements.txt
 
# Add your keys to a .env file in the project root
#   GEMINI_API_KEY=your-gemini-key
#   DATABASE_URL=postgresql://user:password@host:5432/dbname   (optional)
 
# Launch the app
streamlit run src/app.py
```
 
`DATABASE_URL` is only needed for the default Instacart dashboard. Without it, the upload, join, chart, chat and report features still work.
 
To rebuild the Instacart database yourself, download the dataset from Kaggle, place the CSVs in `/raw`, and run `notebooks/01_eda.ipynb`.
 
---
 
## Known Limitations
 
- PDF extraction works best on simple, clearly bordered tables; scanned PDFs and complex merged-cell layouts are not supported
- Charts on very large uploads are aggregated or sampled for responsiveness (scatter up to 5,000 points, line and box up to 20,000)
- Excel reports include the first 10,000 rows and CSV exports the first 100,000 rows to keep downloads fast
- Joins are chained one table at a time
---
 
## What I'd Build Next
 
- Conversation memory so follow-up questions build on earlier answers
- A live or streaming data source instead of static snapshots
- Saved sessions and scheduled reports
- User accounts, so people can keep their own datasets and reports
---
 
## About Me
 
Built by **Bhaskar**, exploring the intersection of data analytics and applied AI.
 
📧 [sparsh4142@gmail.com](mailto:sparsh4142@gmail.com) · [LinkedIn](https://linkedin.com/in/bhaskarstackanalyst)
 
Claude finished the response
