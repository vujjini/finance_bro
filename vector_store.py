# we gotta take the text and clean it up, and then add it to a FAISS vector store database


# use regex to clear common filler shit in website articles like "sponsered", "author", etc.
# when adding it to FAISS database, keep the tags like symbol, data, title, to make retrieval efficient, also keep a tag like "stock", "forex", "real_estate", etc