import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# Headers to simulate a browser request
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Image extensions to filter out
image_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg', '.bmp', '.tiff', '.ico')

# Function to extract category from sitemap URL
def get_category(sitemap_url):
    if re.search(r'post-sitemap(\d*).xml', sitemap_url):
        return "post"
    elif "page-sitemap" in sitemap_url:
        return "page"
    else:
        filename = sitemap_url.split('/')[-1].replace('.xml', '')
        clean_category = filename.replace('-sitemap', '')
        return clean_category.replace('-', ' ')

# Function to fetch and parse page data
def fetch_page_data(url, category):
    try:
        page_response = requests.get(url, headers=headers, timeout=10)
        page_soup = BeautifulSoup(page_response.text, 'html.parser')
        page_title = page_soup.find('title').text.strip() if page_soup.find('title') else "No title found"
        return (url, page_title, category)
    except Exception as e:
        return (url, f"Error fetching title: {e}", category)

# Function to extract URLs and page titles
def extract_urls_and_titles(sitemap_url):
    response = requests.get(sitemap_url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, 'xml')

    urls_data = []
    is_sitemap = soup.find_all('sitemap')

    if is_sitemap:
        for sitemap in soup.find_all('loc'):
            sub_sitemap_url = sitemap.text
            urls_data.extend(extract_urls_and_titles(sub_sitemap_url))
    else:
        urls = [loc.text for loc in soup.find_all('loc') if not loc.text.lower().endswith(image_extensions)]
        category = get_category(sitemap_url)
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = executor.map(lambda url: fetch_page_data(url, category), urls)
            urls_data.extend(results)

    return urls_data

# Function to check and determine which sitemap file exists
def determine_sitemap(user_site):
    sitemap_index = user_site.rstrip('/') + '/sitemap_index.xml'
    sitemap = user_site.rstrip('/') + '/sitemap.xml'

    try:
        response = requests.get(sitemap_index, headers=headers, timeout=10)
        if response.status_code == 200:
            return sitemap_index
    except requests.RequestException:
        pass

    try:
        response = requests.get(sitemap, headers=headers, timeout=10)
        if response.status_code == 200:
            return sitemap
    except requests.RequestException:
        pass

    return None

# Streamlit UI code
st.title("Sitemap URL Extractor")

# Input box for user to enter website URL
user_site = st.text_input("Enter the website URL (e.g., https://example.com):")

if st.button('Fetch Sitemap Data'):
    if user_site:
        sitemap_url_to_use = determine_sitemap(user_site)
        if sitemap_url_to_use:
            try:
                response = requests.get(sitemap_url_to_use, headers=headers, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'xml')
                urls = [loc.text for loc in soup.find_all('loc')]

                all_data = []
                progress_bar = st.progress(0)
                total_sitemaps = len(urls)
                for idx, sitemap_url in enumerate(urls):
                    sitemap_data = extract_urls_and_titles(sitemap_url)
                    all_data.extend(sitemap_data)
                    progress_bar.progress((idx + 1) / total_sitemaps)

                if all_data:
                    df = pd.DataFrame(all_data, columns=['URL', 'Page Title', 'Category'])
                    df.index = df.index + 1
                    st.dataframe(df)  # Display the DataFrame in a table format
                    st.success(f"Data fetched successfully!")
                else:
                    st.warning("No data found in the sitemap.")
            except requests.RequestException as e:
                st.error(f"Error fetching sitemap: {e}")
        else:
            st.error("No valid sitemap found.")
    else:
        st.error("Please enter a valid website URL.")
