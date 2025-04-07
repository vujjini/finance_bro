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