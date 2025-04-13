import os
import requests
import json
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings
from dotenv import load_dotenv
from googleapiclient.discovery import build
import re

load_dotenv("./.env")
tiingo_api_key = os.environ.get("tiinglo_api_key")


def extract_news_links_from_landing(url: str, keyword_filter):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    
    links = set()
    for a in soup.find_all("a", href=True):
        href = a['href']
        full_url = href if href.startswith("http") else f"https://{url.split('/')[2]}{href}"
        
        # Basic heuristic filters for finance article pages
        if re.search(r"(news|article|202\d)", full_url, re.IGNORECASE) and keyword_filter.lower() in full_url.lower():
            links.add(full_url)

    return list(links)

google_api_key = os.environ.get("google_search_api")
cse_id = os.environ.get("google_cse_id")

service = build("customsearch", "v1", developerKey=google_api_key)


# print(res_links)

def get_text_from_url(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # Try XML parser first if content type hints it's XML
        content_type = response.headers.get('Content-Type', '')
        if 'xml' in content_type:
            soup = BeautifulSoup(response.text, 'lxml-xml')
        else:
            # Suppress XMLParsedAsHTMLWarning if fallback needed
            warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
            soup = BeautifulSoup(response.text, 'html.parser')

        # Extract paragraph text
        paragraphs = soup.find_all('p')
        text = '\n'.join(p.get_text() for p in paragraphs if p.get_text().strip())
        return text

    except Exception as e:
        return f"Failed to fetch {url}: {str(e)}"
    

def google_search():
    pass

def get_stock_news_articles(company_name, symbol, dest_file):
    params = {
        'api_token': tiingo_api_key,
        'symbols': symbol,
        'filter_entities': 'true',
        'language': 'en'
    }
    requestResponse = requests.get("https://api.marketaux.com/v1/news/all", params=params)
    # print(requestResponse.json())
    # parse the response to get the news articles
    # how to parse json response in python to visually see the data
    # print the response in a readable format
    response = requestResponse.json()
    # print(json.dumps(response, indent=4))
    json_file_name = f"{dest_file}.json"
    # write the response to a json file
    with open(json_file_name, 'w') as f:
        json.dump(response, f, indent=4)
    query = f"{company_name} stock news"
    num_results = 10

    request = service.cse().list(q=query, cx=cse_id, num=num_results, sort='date')

    response_2 = request.execute()

    # with open("google_news.json", 'w') as f:
    #     json.dump(response, f, indent=4)

    res_links = []
    for item in response_2["items"]:
        links = extract_news_links_from_landing(item["link"], company_name)
        res_links.append(links)
    with open(f"{dest_file}.txt", "w", encoding="utf-8") as f:
        for link in res_links:
            for l in link:
                if len(l) > 0:
                    text = get_text_from_url(l)
                            # Only write if fetch was successful
                    if not text.startswith("Failed to fetch"):
                        f.write(f"=== ARTICLE FROM: {l} ===\n")
                        f.write(text + "\n\n")

                        # if len(article["similar"]) > 0:
                        #     f.write("=== SIMILAR ARTICLES ===\n")
                        #     for similar_article in article["similar"]:
                        #         similar_url = similar_article["url"]
                        #         similar_text = get_text_from_url(similar_url)
                        #         if not similar_text.startswith("Failed to fetch"):
                        #             f.write(f"Similar Article: {similar_url}\n")
                        #             f.write(similar_text + "\n\n")
        for article in response["data"]:
            url = article["url"]
            text = get_text_from_url(url)

            # Only write if fetch was successful
            if not text.startswith("Failed to fetch"):
                f.write(f"=== ARTICLE FROM: {url} ===\n")
                f.write(text + "\n\n")

                if len(article["similar"]) > 0:
                    f.write("=== SIMILAR ARTICLES ===\n")
                    for similar_article in article["similar"]:
                        similar_url = similar_article["url"]
                        similar_text = get_text_from_url(similar_url)
                        if not similar_text.startswith("Failed to fetch"):
                            f.write(f"Similar Article: {similar_url}\n")
                            f.write(similar_text + "\n\n")

# get_stock_news_articles("TSLA", "tesla_news")
