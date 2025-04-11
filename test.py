import os
import requests
import json
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings
from dotenv import load_dotenv

load_dotenv("./.env")
tiingo_api_key = os.environ.get("tiinglo_api_key")


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

def get_stock_news_articles(symbol, dest_file):
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
    with open(f"{dest_file}.txt", "w", encoding="utf-8") as f:
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

get_stock_news_articles("TSLA", "tesla_news")
