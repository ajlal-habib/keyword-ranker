import streamlit as st
import pandas as pd
import requests
import json
import time
import plotly.express as px
import tldextract
from urllib.parse import urlparse

# --- SESSION STATE & INIT ---
def init_session_state():
    if "results_data" not in st.session_state:
        st.session_state.results_data = []
    if "domain" not in st.session_state:
        st.session_state.domain = ""

# --- CORE LOGIC ---
def get_clean_root(url_or_domain):
    """Extracts the base domain (e.g., folio3.com) regardless of subdomains or protocols."""
    ext = tldextract.extract(url_or_domain)
    return f"{ext.domain}.{ext.suffix}".lower()

def determine_page_type(url):
    if url == "N/A": return "N/A"
    url_lower = url.lower()
    if any(k in url_lower for k in ["/blog/", "/article/", "/post/", "/news/"]):
        return "Blog"
    return "Landing Page"

def get_search_results(keyword, target_input, api_key, gl="us", hl="en", device="desktop"):
    """
    Highly accurate real-time US search. 
    Prevents hallucinations by matching exact root domains.
    """
    target_root = get_clean_root(target_input)
    # Check if user is tracking a specific deep URL
    is_exact_url = "/" in target_input.replace("https://", "").replace("www.", "").strip("/")
    
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    # Request 100 results in one go for a full SERP snapshot
    payload = json.dumps({
        "q": keyword,
        "gl": gl,
        "hl": hl,
        "num": 100,
        "autocorrect": False,
        "device": device
    })
    
    try:
        response = requests.post("https://google.serper.dev/search", headers=headers, data=payload)
        
        if response.status_code == 403:
            return {"error": "API Key Error", "msg": "Unauthorized: Check your Serper.dev key."}
        elif response.status_code != 200:
            return {"error": "API Error", "msg": f"Status {response.status_code}"}
            
        results = response.json()
        organic_results = results.get("organic", [])
        
        found_matches = {} # URL -> Position

        for result in organic_results:
            link = result.get("link", "").lower()
            pos = result.get("position")
            
            # Extract root of the found result
            res_ext = tldextract.extract(link)
            res_root = f"{res_ext.domain}.{res_ext.suffix}".lower()

            match_found = False
            if is_exact_url:
                if target_input.lower().strip("/") in link.strip("/"):
                    match_found = True
            else:
                # This stops competitor.com/folio3-review from being counted
                if res_root == target_root:
                    match_found = True

            if match_found:
                if link not in found_matches or pos < found_matches[link]:
                    found_matches[link] = pos

        if not found_matches:
            return {"rank": "Not in Top 100", "url": "N/A", "all_ranks": "N/A"}

        # Sort matches by position
        sorted_matches = sorted(found_matches.items(), key=lambda x: x[1])
        
        return {
            "rank": sorted_matches[0][1],
            "url": sorted_matches[0][0],
            "all_ranks": ", ".join([f"Pos {p}" for u, p in sorted_matches])
        }
                        
    except Exception as e:
        return {"error": "System Error", "msg": str(e)}

# --- STYLING ---
def render_styling():
    st.markdown("""
        <style>
        .stApp { background-color: #0E1117; color: #FAFAFA; }
        .metric-container {
            background-color: #161A25; padding: 1.5rem; border-radius: 12px;
            border: 1px solid #2D333B; margin-bottom: 1rem;
        }
        .metric-value { font-size: 2.2rem; font-weight: 800; color: #FFFFFF; }
        .metric-label { font-size: 0.85rem; color: #8B949E; text-transform: uppercase; font-weight: 600; }
        </style>
    """, unsafe_allow_html=True)

def color_coding(val):
    if val == "Not in Top 100": return 'color: #ef4444;'
    try:
        v = int(str(val).replace("Pos", "").strip())
        if v <= 3: return 'color: #10b981; font-weight: bold;'
        if v <= 10: return 'color: #34d399;'
        return 'color: #f59e0b;'
    except: return ''

# --- MAIN APP ---
def main():
    st.set_page_config(page_title="SERP Pulse Pro", page_icon="🎯", layout="wide")
    init_session_state()
    render_styling()
    
    st.title("🎯 SERP Pulse: Real-Time US Tracker")

    with st.sidebar:
        st.header("⚙️ Configuration")
        target_domain = st.text_input("Target Domain/URL", placeholder="e.g. folio3.com", value=st.session_state.domain)
        serpapi_key = st.text_input("Serper.dev API Key", type="password")
        
        with st.expander("Regional Settings"):
            country_code = st.selectbox("Country", ["us", "uk", "ca", "au"], index=0)
            device_type = st.selectbox("Device", ["desktop", "mobile"], index=0)

        st.divider()
        input_method = st.radio("Input Method:", ["📄 Upload CSV", "⌨️ Paste Keywords"])
        
        keywords = []
        if input_method == "📄 Upload CSV":
            file = st.file_uploader("Upload CSV", type=["csv"])
            if file:
                df = pd.read_csv(file)
                col = next((c for c in df.columns if 'keyword' in c.lower()), None)
                if col: keywords = df[col].dropna().tolist()
        else:
            text = st.text_area("Paste Keywords (One per line)")
            keywords = [k.strip() for k in text.split('\n') if k.strip()]

        if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
            if not target_domain or not serpapi_key or not keywords:
                st.error("Missing credentials or keywords.")
            else:
                st.session_state.results_data = []
                progress = st.progress(0)
                
                for i, kw in enumerate(keywords):
                    res = get_search_results(kw, target_domain, serpapi_key, country_code, "en", device_type)
                    
                    if "error" in res:
                        st.error(res["msg"])
                        break
                    
                    st.session_state.results_data.append({
                        "Keyword": kw,
                        "Best Rank": res["rank"],
                        "All Listings": res["all_ranks"],
                        "URL": res["url"],
                        "Type": determine_page_type(res["url"])
                    })
                    progress.progress((i + 1) / len(keywords))
                st.success("Finished!")

    # --- DASHBOARD TABS ---
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🔍 Intelligence", "📥 Export"])

    with tab1:
        if st.session_state.results_data:
            df = pd.DataFrame(st.session_state.results_data)
            # Calculations
            valid_ranks = [int(r) for r in df["Best Rank"] if str(r).isdigit()]
            top_10 = len([r for r in valid_ranks if r <= 10])
            avg_pos = sum(valid_ranks)/len(valid_ranks) if valid_ranks else 0
            
            c1, c2, c3 = st.columns(3)
            c1.markdown(f'<div class="metric-container"><div class="metric-label">Top 10</div><div class="metric-value">{top_10}</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-container"><div class="metric-label">Avg Position</div><div class="metric-value">{avg_pos:.1f}</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-container"><div class="metric-label">Total Keywords</div><div class="metric-value">{len(df)}</div></div>', unsafe_allow_html=True)
            
            fig = px.histogram(df, x="Best Rank", title="Ranking Distribution", template="plotly_dark", color_discrete_sequence=['#34d399'])
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        if st.session_state.results_data:
            df_display = pd.DataFrame(st.session_state.results_data)
            st.dataframe(df_display.style.applymap(color_coding, subset=['Best Rank']), use_container_width=True)

    with tab3:
        if st.session_state.results_data:
            csv = pd.DataFrame(st.session_state.results_data).to_csv(index=False)
            st.download_button("Download CSV Report", csv, "report.csv", "text/csv")

if __name__ == "__main__":
    main()
