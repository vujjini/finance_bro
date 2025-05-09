# we gotta take the text and clean it up, and then add it to a FAISS vector store database


# use regex to clear common filler shit in website articles like "sponsered", "author", etc.
# when adding it to FAISS database, keep the tags like symbol, data, title, to make retrieval efficient, also keep a tag like "stock", "forex", "real_estate", etc


# prompting strategy:
# we give the LLM two things: the retrieved stuff, the prompt (system and user), market trend. in user prompt, we end with based on the research analysis using the data provided
# provided a risk assesment level on a certain scale

# store that in the asset object
# we present that to the user
# if the user clicks portfolio adjustment, math is done it take the risk assessments of all the asset objects, put in a summary and also the vector store
# is given to the LLM and ask it to do the same calculation at the end.


# also add a feature for recommendations: for hackathon, lets just do forex recommendations -> same process: collect the news -> RAG -> get output for TOP K options
# in the current market -> along with reasoning provided by the LLM -> also present the graph of each recommended asset from an API
# pip3.13 install -qU "langchain[google-vertexai]"
# pip3.13 install -qU langchain-google-vertexai



import os
from dotenv import load_dotenv

# Ensure your VertexAI credentials are configured

from langchain.chat_models import init_chat_model

from langchain_google_vertexai import VertexAIEmbeddings
import bs4
from langchain import hub
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import START, StateGraph
from typing_extensions import List, TypedDict
from langchain_community.document_loaders import TextLoader
from typing_extensions import Annotated
from datetime import datetime, timedelta
import json

from polygon import RESTClient
from test import get_stock_news_articles

polygon_client = RESTClient("pPY2_xV3rxyz1G8mIbMEbx84lTb11CDf")


# Customize your time window
end_date = datetime.today()
start_date = end_date - timedelta(days=30)
print(type(start_date.strftime('%Y-%m-%d')), end_date.strftime('%Y-%m-%d'))



os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "sacred-reality-456221-i2-a2b09f2b43b9.json"

from pydantic import BaseModel, Field
# class ResponseFormatter(BaseModel):
#     """Always use this tool to structure your response to the user."""
#     answer: Annotated[List[str], Field(description="List of required financial data", json_schema_extra={"type": "array"})]
#     explaination: Annotated[str, Field(description="Explanation of the recommended financial data", json_schema_extra={"type": "string"})]


class AttributeExplanation(BaseModel):
    attribute: Annotated[str, Field(description="One of the allowed Polygon financial attributes like 'o', 'c', 'v', etc.")]
    reason: Annotated[str, Field(description="Why this attribute is useful based on the news")]

class ResponseFormatter(BaseModel):
    """Structure your response using this format."""
    recommendations: Annotated[
        List[AttributeExplanation],
        Field(description="List of recommended financial attributes with explanations", json_schema_extra={"type": "array"})
    ]

class FinancialAnalysis(BaseModel):
        qualitative_analysis: str = Field(..., description="Narrative about recent news, company events, and market sentiment.")
        quantitative_analysis: str = Field(..., description="Analysis of price trends, volumes, and any volatility in the stock.")
        user_portfolio_fit: str = Field(..., description="How well the stock aligns with the user's portfolio and risk preferences.")
        recommendation: str = Field(..., description="Final investment advice based on the combined qualitative and quantitative insights.")




load_dotenv("./.env")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = os.environ.get("langchain_api_token")


embeddings = VertexAIEmbeddings(model="text-embedding-004")

llm = init_chat_model("gemini-2.0-flash-001", model_provider="google_vertexai")

llm_structured_analysis = llm.with_structured_output(FinancialAnalysis)
llm_structured = llm.with_structured_output(ResponseFormatter)

from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from qdrant_client.http.models import Distance, VectorParams

client = QdrantClient(":memory:")

client.create_collection(
    collection_name="demo_collection",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
)



vector_store = QdrantVectorStore(
    client=client,
    collection_name="demo_collection",
    embedding=embeddings,
)



# Load and chunk contents of the blog
# loader = WebBaseLoader(
#     web_paths=("https://finance.yahoo.com/news/apple-takes-biggest-hit-magnificent-164500958.html",),
#     bs_kwargs=dict(
#         parse_only=bs4.SoupStrainer(
#             class_=("post-content", "post-title", "post-header")
#         )
#     ),
# )

def get_analysis(company_name, stock_symbol, dest_file):
    get_stock_news_articles(company_name, stock_symbol, dest_file)
    loader = TextLoader(
        f"{dest_file}.txt",
        encoding="utf-8",
        autodetect_encoding=True,
    )
    docs = loader.load()

    # print(docs[0])

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    all_splits = text_splitter.split_documents(docs)


    # Index chunks
    _ = vector_store.add_documents(documents=all_splits)

    # Define prompt for question-answering
    prompt = hub.pull("rlm/rag-prompt")


    # Define state for application
    class State(TypedDict):
        question: str
        context: List[Document]
        answer: str


    # Define application steps
    def retrieve(state: State):
        retrieved_docs = vector_store.similarity_search(state["question"])
        # print("\n🔍 Retrieved Documents:\n")
        # for i, doc in enumerate(retrieved_docs):
        #     print(f"[{i+1}] {doc.page_content[:500]}...\n")
        return {"context": retrieved_docs}


    def generate(state: State):
        aggs = []
        for a in polygon_client.list_aggs(
            stock_symbol,
            1,
            "day",
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            adjusted="true",
            sort="asc",
            limit=120,
        ):
            aggs.append(a)
        docs_content = "\n\n".join(doc.page_content for doc in state["context"]) + '\n\n' + "\n".join(str(a) for a in aggs)
        print(docs_content)
        messages = prompt.invoke({"question": state["question"], "context": docs_content})
        # response = llm_structured.invoke(messages)
        # response = llm.invoke(messages)
        response = llm_structured_analysis.invoke(messages)
        # return {"answer": response.recommendations}
        return {"answer": response}


    # Compile application and test
    graph_builder = StateGraph(State).add_sequence([retrieve, generate])
    graph_builder.add_edge(START, "retrieve")
    graph = graph_builder.compile()

    # response = graph.invoke({
    #     "question": f"""
    # You are a financial assistant that recommends data based on available sources.

    # Based on given recent news related to **Nvidia (NVDA)**, you are tasked with identifying what **quantitative financial data** would be helpful to make an informed investment decision.

    # You can only suggest financial data from the following **Polygon.io API fields** for a stock between **{start_date.strftime('%Y-%m-%d')}** and **{end_date.strftime('%Y-%m-%d')}**:

    # - `open`: Open price  
    # - `high`: High price  
    # - `low`: Low price  
    # - `close`: Close price  
    # - `volume`: Volume of shares traded  
    # - `vwap`: Volume-weighted average price (VWAP)  
    # - `transactions`: Number of transactions  
    # - `timestamp`: Unix timestamp of the data point    
    # - `otc`: Whether the data is from over-the-counter markets  

    # **Task:**  
    # Based on the given news and the investment context, select the most relevant attributes from the above list.  
    # For each selected attribute, provide a brief explanation of why it is useful and how it relates to the news.

    # Only use attributes from the list. Do not invent any new ones. """ })
    # response = graph.invoke({
    #     "question": f"""
    # You are a financial analyst tasked with evaluating **{company_name} ({stock_symbol})** stock.

    # Based on the summary of recent news articles provided about the company, as well as key quantitative financial metrics for the stock from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}.

    # **Task:**  
    # Using both the qualitative information (news content) and the quantitative data (stock performance metrics), provide a comprehensive analysis of the stock.

    # Your analysis should include:
    # 1. **Qualitative Insights**: Interpret the market sentiment, company events, and any external factors mentioned in the news.
    # 2. **Quantitative Insights**: Assess price trends, trading volume, volatility, or any other relevant metrics from the financial data.
    # 3. **Risk & Recommendation**: Summarize whether the stock appears to be a safe or risky investment in the current market climate, and whether it is suitable for short-term or long-term investors.

    # **Do not hallucinate or fabricate data. Only reason based on the provided information.**
    # """ })

#     
    response = graph.invoke({
        "question": f"""
    You are a financial advisor analyzing the stock **{company_name} ({stock_symbol})**, which is either a part of a user's investment portfolio or something the user is researching about buying.

    You are provided with:
    - Recent news articles about the stock
    - Quantitative stock performance data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}
    - The user's portfolio profile and asset allocation (see below)

    ---


    User Investment Profile:

    - Risk Tolerance: High
    - Investment Horizon: Long-term (5+ years)
    - Primary Goal: Aggressive growth with exposure to emerging technologies
    - Liquidity Preference: Low (comfortable with short-term losses and lock-ins)
    - Investment Style: Tech-heavy, disruption-focused, willing to weather volatility


    ---

    | Ticker | Company                         | Weight (%) | Sector             |
    |--------|----------------------------------|------------|--------------------|
    | TSLA   | Tesla Inc.                      | 40         | Consumer/Auto      |
    | COIN   | Coinbase Global Inc.           | 25         | Cryptocurrency     |
    | RIVN   | Rivian Automotive Inc.         | 15         | Electric Vehicles  |
    | SQ     | Block Inc.                     | 10         | FinTech            |
    | PLUG   | Plug Power Inc.                | 10         | Renewable Energy   |



    Task:

    Using all the information provided, deliver a structured analysis broken into the following four sections:

    1. Qualitative Analysis  
    - Summarize sentiment, events, or outlook from recent news articles.
    - Mention analyst opinions, product announcements, or risks.

    2. Quantitative Analysis  
    - Discuss the recent trend of stock price, volume, and volatility.
    - Mention if it's rising, falling, or fluctuating, with any key data points or patterns.

    3. User Portfolio Fit  
    - Assess how this stock fits into the current portfolio (sector overlap, diversification).
    - Does it increase or reduce risk?
    - Is its weighting appropriate?

    4. Final Recommendation  
    - Based on all above, should the user hold, trim, increase, or remove this stock?
    - Justify clearly with a balance of qualitative, quantitative, and portfolio-level reasoning.

    Do not fabricate data. Only use the information in the context provided. Format your answer clearly under each section heading.
    """
    })




    res = response["answer"]


    # req = set()

    # for AttributeExplanation in res:
    #     req.add(AttributeExplanation.attribute)

    # return res
    return {"qualitative": res.qualitative_analysis, "quantitative": res.quantitative_analysis, "user_portfolio_fit": res.user_portfolio_fit, "recommendation": res.recommendation}


    # aggs = []
    # for a in polygon_client.list_aggs(
    #     "NVDA",
    #     1,
    #     "day",
    #     start_date.strftime('%Y-%m-%d'),
    #     end_date.strftime('%Y-%m-%d'),
    #     adjusted="true",
    #     sort="asc",
    #     limit=120,
    # ):
    #     aggs.append(a)

    # req_aggs = []
    # for agg in aggs:
    #     req_info = {"unix_millisecond_timestamp": getattr(agg, "timestamp", None)}
    #     for att in req:
    #         req_info[att] = getattr(agg, att, None)
    #     req_aggs.append(req_info)

    # print(aggs)
    # print("\n\n")
    # print(req_aggs)

# print(get_analysis("TAKE-TWO INTERACTIVE SOFTWARE", "TTWO", "take_two_news"))
analysis = get_analysis("Nvidia", "NVDA", "nvidia_news")

print(json.dumps(analysis, indent=4))

# perplexity AI API would be great for this task, as it would be able to get the news articles and then do the RAG process for us.
# https://vectorize.io/how-i-finally-got-agentic-rag-to-work-right/

# Build a pipeline to get the news articles from google


# allow user to ask follow up questions. provide a recommended action button that has a custom prompt from the user.