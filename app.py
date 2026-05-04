import streamlit as st
import pandas as pd
from serpapi import GoogleSearch
import time

def get_search_results(keyword, target_domain, api_key):
    params = {
        "engine": "google",
        "q": keyword,
        "location": "United States",
        "gl": "us",
        "hl": "en",
        "num": 100,
        "api_key": api_key
    }
    
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        
        if "error" in results:
            return "Error", results["error"]
            
        organic_results = results.get("organic_results", [])
        
        for result in organic_results:
            link = result.get("link", "")
            if target_domain.lower() in link.lower():
                return result.get("position", "N/A"), link
                
        return "Not in Top 100", "N/A"
    except Exception as e:
        return "Error", str(e)

def main():
    st.set_page_config(page_title="Keyword Rank Tracker", page_icon="📈", layout="centered")
    
    st.title("📈 Keyword Rank Tracker")
    st.markdown("Track your website's keyword rankings in the US region using SerpApi.")

    # 1. Setup
    st.header("1. Setup")
    target_domain = st.text_input("Target Domain (e.g., mysite.com)", placeholder="mysite.com")
    serpapi_key = st.text_input("SerpApi Key", type="password")

    # 2. Upload Keywords
    st.header("2. Upload Keywords")
    st.markdown("Upload a CSV file containing your keywords. Ensure there is a column named **Keyword** or **Keywords**.")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    
    df = None
    keywords = []
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            kw_col = next((c for c in df.columns if c.lower() in ['keyword', 'keywords', 'search term', 'query', 'term']), None)
            
            if kw_col:
                keywords = df[kw_col].dropna().astype(str).tolist()
                st.success(f"Successfully loaded {len(keywords)} keywords from the '{kw_col}' column.")
            else:
                st.error("Error: Could not find a column named 'Keyword' in the uploaded CSV. Please check your headers.")
        except Exception as e:
            st.error(f"Error reading CSV: {e}")

    # 3. Execution
    st.header("3. Execution")
    if st.button("Run Tracker", type="primary"):
        if not target_domain:
            st.warning("Please provide a Target Domain.")
        elif not serpapi_key:
            st.warning("Please provide a SerpApi Key.")
        elif not keywords:
            st.warning("Please upload a valid CSV with keywords.")
        else:
            st.info("Tracker started. Please wait...")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results_data = []
            
            for i, keyword in enumerate(keywords):
                status_text.text(f"Fetching results for: '{keyword}' ({i+1}/{len(keywords)})")
                
                rank, url = get_search_results(keyword, target_domain, serpapi_key)
                
                results_data.append({
                    "Keyword": keyword,
                    "Current Rank": rank,
                    "URL": url
                })
                
                progress_bar.progress((i + 1) / len(keywords))
                time.sleep(0.2) 
                
            status_text.text("Tracking complete!")
            st.success("Successfully fetched all keyword rankings.")
            
            # 4. Output
            st.header("4. Output")
            results_df = pd.DataFrame(results_data)
            
            st.dataframe(results_df, use_container_width=True)
            
            csv_data = results_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download Results as CSV",
                data=csv_data,
                file_name=f"{target_domain.replace('.', '_')}_rankings.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
