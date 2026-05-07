import streamlit as st
import pandas as pd
import requests
import json
import time
import plotly.express as px
import tldextract
from urllib.parse import urlparse

# --- CORE SEO LOGIC ---
def get_clean_root(url_or_domain):
    ext = tldextract.extract(url_or_domain)
    return f"{ext.domain}.{ext.suffix}".lower()

def determine_page_type(url):
    if url == "N/A": return "N/A"
    url_lower = url.lower()
    if any(k in url_lower for k in ["/blog/", "/article/", "/post/", "/news/"]):
        return "Blog"
    return "Landing Page"

# --- STYLING (Fixed for Dark/Light Mode) ---
def render_styling():
    st.markdown("""
        <style>
        /* Container that adapts to Streamlit's theme */
        .metric-container {
            background-color: var(--secondary-bg-color);
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            margin-bottom: 1rem;
            transition: all 0.3s ease;
        }
        /* Text that adapts to theme primary text color */
        .metric-value {
            font-size: 2rem;
            font-weight: 800;
            color: var(--text-color);
        }
        .metric-label {
            font-size: 0.8rem;
            color: var(--text-color);
            opacity: 0.7;
            text-transform: uppercase;
            font-weight: 600;
        }
        /* Simple fix for Tab readability */
        .stTabs [data-baseweb="tab"] {
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)

def color_coding(val):
    if val == "Not in Top 100" or val == ">50": 
        return 'background-color: rgba(239, 68, 68, 0.1); color: #ef4444;'
    try:
        # Extract first number if multiple exist
        v = int(str(val).split(',')[0].replace('Pos', '').strip())
        if v <= 3: return 'background-color: rgba(16, 185, 129, 0.2); color: #10b981; font-weight: bold;'
        if v <= 10: return 'background-color: rgba(52, 211, 153, 0.1); color: #34d399;'
        return 'color: #f59e0b;' # Orange for page 2+
    except: return ''

# --- UPDATED SEARCH LOGIC (US Accuracy) ---
def get_search_results(keyword, target_input, api_key, gl="us", hl="en", device="desktop"):
    target_root = get_clean_root(target_input)
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
    
    payload = json.dumps({
        "q": keyword, "gl": gl, "hl": hl, "num": 100, 
        "autocorrect": False, "device": device
    })
    
    try:
        response = requests.post("https://google.serper.dev/search", headers=headers, data=payload)
        if response.status_code != 200: return {"error": "API Error"}
            
        data = response.json()
        organic = data.get("organic", [])
        found_matches = {} 

        for result in organic:
            link = result.get("link", "").lower()
            pos = result.get("position")
            res_root = get_clean_root(link)

            if res_root == target_root:
                if link not in found_matches or pos < found_matches[link]:
                    found_matches[link] = pos

        if not found_matches:
            return {"rank": "Not in Top 100", "url": "N/A", "all_ranks": "N/A"}

        sorted_matches = sorted(found_matches.items(), key=lambda x: x[1])
        return {
            "rank": sorted_matches[0][1],
            "url": sorted_matches[0][0],
            "all_ranks": ", ".join([f"Pos {p}" for u, p in sorted_matches])
        }
    except: return {"error": "System Error"}

# --- MAIN APP ---
def main():
    st.set_page_config(page_title="AI Keyword Tracker", page_icon="🎯", layout="wide")
    if "results_data" not in st.session_state: st.session_state.results_data = []
    render_styling()
    
    st.title("🎯 AI Keyword Tracker")

    with st.sidebar:
        st.header("⚙️ Configuration")
        target_domain = st.text_input("Target Domain", placeholder="e.g. folio3.com")
        serpapi_key = st.text_input("Serper.dev API Key", type="password")
        country = st.selectbox("Country", ["us", "uk", "ca"], index=0)
        
        text = st.text_area("Paste Keywords")
        keywords = [k.strip() for k in text.split('\n') if k.strip()]

        if st.button("🚀 Analyze SERP", type="primary"):
            st.session_state.results_data = []
            p_bar = st.progress(0)
            for i, kw in enumerate(keywords):
                res = get_search_results(kw, target_domain, serpapi_key, country)
                st.session_state.results_data.append({
                    "Keyword": kw, "Best Rank": res.get("rank"), 
                    "URL": res.get("url"), "All Rankings": res.get("all_ranks")
                })
                p_bar.progress((i + 1) / len(keywords))

    tab1, tab2 = st.tabs(["📊 Dashboard", "🔍 Intelligence"])

    with tab1:
        if st.session_state.results_data:
            df = pd.DataFrame(st.session_state.results_data)
            valid = [int(r) for r in df["Best Rank"] if str(r).isdigit()]
            
            c1, c2, c3 = st.columns(3)
            # These now use var(--text-color) so they work in Light Mode
            c1.markdown(f'<div class="metric-container"><div class="metric-label">Top 10</div><div class="metric-value">{len([r for r in valid if r <= 10])}</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-container"><div class="metric-label">Avg Rank</div><div class="metric-value">{(sum(valid)/len(valid)) if valid else 0 :.1f}</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-container"><div class="metric-label">Keywords</div><div class="metric-value">{len(df)}</div></div>', unsafe_allow_html=True)
            
            # Use 'streamlit' theme for Plotly to automatically swap colors
            fig = px.histogram(df, x="Best Rank", template="plotly_white" if st.get_option("theme.base") == "light" else "plotly_dark")
            st.plotly_chart(fig, use_container_width=True, theme="streamlit")

    with tab2:
        if st.session_state.results_data:
            df_display = pd.DataFrame(st.session_state.results_data)
            # Use .map for newer pandas versions
            st.dataframe(df_display.style.map(color_coding, subset=['Best Rank']), use_container_width=True)

if __name__ == "__main__":
    main()
