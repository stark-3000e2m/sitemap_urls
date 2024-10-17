import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd

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

# Function to extract URLs and page titles
def extract_urls_and_titles(sitemap_url):
    response = requests.get(sitemap_url, headers=headers)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'xml')

    urls_data = []
    is_sitemap = soup.find_all('sitemap')

    if is_sitemap:
        for sitemap in soup.find_all('loc'):
            sub_sitemap_url = sitemap.text
            urls_data.extend(extract_urls_and_titles(sub_sitemap_url))
    else:
        for loc in soup.find_all('loc'):
            url = loc.text
            if url.lower().endswith(image_extensions):
                continue

            try:
                page_response = requests.get(url, headers=headers)
                page_response.encoding = 'utf-8'
                page_soup = BeautifulSoup(page_response.text, 'html.parser')
                page_title = page_soup.find('title').text if page_soup.find('title') else "No title found"
            except Exception as e:
                page_title = f"Error fetching title: {e}"

            category = get_category(sitemap_url)
            urls_data.append((url, page_title, category))

    return urls_data

# Function to check and determine which sitemap file exists
def determine_sitemap(user_site):
    sitemap_index = user_site + '/sitemap_index.xml'
    sitemap = user_site + '/sitemap.xml'

    try:
        response = requests.get(sitemap_index, headers=headers)
        if response.status_code == 200:
            return sitemap_index
    except requests.RequestException:
        pass

    try:
        response = requests.get(sitemap, headers=headers)
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
                response = requests.get(sitemap_url_to_use, headers=headers)
                response.raise_for_status()
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.text, 'xml')
                urls = [loc.text for loc in soup.find_all('loc')]

                all_data = []
                for sitemap_url in urls:
                    sitemap_data = extract_urls_and_titles(sitemap_url)
                    all_data.extend(sitemap_data)

                if all_data:
                    df = pd.DataFrame(all_data, columns=['URL', 'Page Title', 'Category'])
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
