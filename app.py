import streamlit as st
import pandas as pd
from serpapi import GoogleSearch
import time

def get_search_results(keyword, target_domain, api_key):
    # Clean the domain to improve matching accuracy
    clean_domain = target_domain.lower().replace("https://", "").replace("http://", "").replace("www.", "").strip()
    
    params = {
        "engine": "google",
        "q": keyword,
        "location": "United States",
        "gl": "us",
        "hl": "en",
        "num": 100, # Grabs the full top 100 results in one request
        "api_key": api_key
    }
    
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        
        if "error" in results:
            error_msg = results.get("error", "")
            if "Invalid API key" in error_msg:
                return "API Key Error", "Please provide a valid SerpApi Key."
            elif "out of bounds" in error_msg.lower() or "credits" in error_msg.lower():
                return "Quota Exceeded", "SerpApi account out of credits."
            else:
                return "API Error", error_msg
            
        organic_results = results.get("organic_results", [])
        
        # Cross-check results for the domain
        for result in organic_results:
            link = result.get("link", "").lower()
            # Accuracy fix: Check if the clean domain string exists anywhere in the URL
            if clean_domain in link:
                return result.get("position", "N/A"), result.get("link")
                
        return "Not in Top 100", "N/A"
    except Exception as e:
        return "Error", str(e)

def main():
    st.set_page_config(page_title="Keyword Rank Tracker Pro", page_icon="📊", layout="wide")
    
    st.title("📊 Keyword Rank Tracker Pro")
    st.markdown("Track your website's organic search rankings in the US region accurately.")

    # Sidebar for Settings
    with st.sidebar:
        st.header("⚙️ Settings")
        target_domain = st.text_input("Target Domain", placeholder="folio3.com", help="Domain to track (e.g., folio3.com)")
        serpapi_key = st.text_input("SerpApi Key", type="password", help="Your SerpApi private key")
        
        st.divider()
        
        st.markdown("### 📝 Instructions")
        st.markdown(
            "1. **Domain**: Enter your root domain (e.g., `folio3.com`).\n"
            "2. **API Key**: Get your key from [SerpApi.com](https://serpapi.com).\n"
            "3. **Upload**: Use a CSV with a 'Keyword' column.\n"
            "4. **Run**: Get authentic US rankings."
        )

    # UI Layout: Top Section
    metrics_container = st.container()
    
    st.subheader("1. Upload Keywords")
    uploaded_file = st.file_uploader("Upload CSV containing keywords", type=["csv"])
    
    keywords = []
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            kw_col = next((c for c in df.columns if c.lower() in ['keyword', 'keywords', 'search term', 'query', 'term']), None)
            
            if kw_col:
                keywords = df[kw_col].dropna().astype(str).tolist()
                st.success(f"✅ Loaded {len(keywords)} keywords.")
            else:
                st.error("❌ Could not find a 'Keyword' column in the CSV.")
        except Exception as e:
            st.error(f"Error reading CSV: {e}")

    st.divider()

    # 2. Execution
    st.subheader("2. Run Tracker")
    if st.button("▶ Start Tracking", type="primary", use_container_width=True):
        if not target_domain:
            st.error("Please provide a Target Domain in the sidebar.")
        elif not serpapi_key:
            st.error("Please provide a SerpApi Key in the sidebar.")
        elif not keywords:
            st.warning("Please upload a CSV with keywords first.")
        else:
            results_data = []
            
            with st.spinner("Analyzing Google Search Results..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, keyword in enumerate(keywords):
                    status_text.text(f"Processing: '{keyword}' ({i+1}/{len(keywords)})")
                    
                    rank, url = get_search_results(keyword, target_domain, serpapi_key)
                    
                    results_data.append({
                        "Keyword": keyword,
                        "Current Rank": rank,
                        "URL": url
                    })
                    
                    progress_bar.progress((i + 1) / len(keywords))
                    time.sleep(0.1) 
                    
                status_text.empty()
                progress_bar.empty()
            
            st.success("✅ Analysis Complete!")
            
            # Generate DataFrame
            results_df = pd.DataFrame(results_data)
            
            # Calculate Metrics for Dashboard
            total_kws = len(results_df)
            numeric_ranks = pd.to_numeric(results_df["Current Rank"], errors='coerce').dropna()
            top_3 = len(numeric_ranks[numeric_ranks <= 3])
            avg_pos = round(numeric_ranks.mean(), 1) if not numeric_ranks.empty else "N/A"
            
            # Display Metric Cards
            with metrics_container:
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Keywords", total_kws)
                m2.metric("Top 3 Rankings", top_3)
                m3.metric("Average Position", avg_pos)
            
            # Results Table
            st.subheader("3. Detailed Results")
            st.dataframe(results_df, use_container_width=True)
            
            # Download
            csv_data = results_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Results as CSV",
                data=csv_data,
                file_name=f"{target_domain.replace('.', '_')}_report.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
