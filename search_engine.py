from collections import defaultdict
import difflib
import json
import streamlit as st
from typing import Dict, List
from src.posting import Posting
from bs4 import BeautifulSoup
import time
from thefuzz import fuzz


from nltk.stem import PorterStemmer

def stem_tokens(tokens: List[str]) -> List[str]:
    stemmer = PorterStemmer()
    return [stemmer.stem(token) for token in tokens]

def get_postings(tokens: List[str], index_of_index: Dict[str, int]) -> List[List[Posting]]:
    token_postings = []  # List to store postings for each token

    with open("indices/index.txt", "r") as index:
        for token in tokens:
            #similar_tokens = [key for key in index_of_index.keys() if fuzz.ratio(token, key) >= 100]
            #print(f"Token: {token}, Similar Tokens: {similar_tokens}")

        #for similar_token in similar_tokens:
            index_position = index_of_index.get(token, -1)
            if index_position > -1:
                index.seek(index_position)
                line = index.readline()
                token, postings_string = line.split(":", 1)
                postings = [Posting.from_string(p) for p in postings_string.split(";")]
                token_postings.append(postings)
    return token_postings

def filter(token_postings, tokens, index_of_crawled):
    results = []
    doc_tf_idf = defaultdict(float)
    doc_to_postings = defaultdict(list)

    for postings in token_postings:
        for posting in postings:
            doc_to_postings[posting.id].append(posting)
    
    token_doc_ids = [set(posting.id for posting in postings) for postings in token_postings]
    
    # Find common document IDs that appear in all token_doc_ids sets
    if token_doc_ids:
        common_doc_ids = set.intersection(*token_doc_ids)
    else:
        common_doc_ids = set()

    with open("indices/crawled.txt", "r", encoding="utf-8") as crawled_file:
        for doc_id in common_doc_ids:
            crawled_file.seek(index_of_crawled[doc_id])
            path = crawled_file.readline().strip()
            with open(path, "r") as file:
                data = json.load(file)
                tf_idf_score = calc_doc_relevance(doc_to_postings[doc_id], tokens, data)
                document = Posting(id=doc_id, tf_idf=tf_idf_score)
                results.append(document)
    
    return results

def calc_doc_relevance(postings: List[Posting], tokens: List[str], data: Dict) -> float:
    # inital tf_idf from the summings 
    tf_idf_score = sum(posting.tf_idf for posting in postings)
    
    # parsing content and extracting title 
    soup = BeautifulSoup(data["content"], "lxml")
    title_tag = soup.title
    title = title_tag.string if title_tag and title_tag.string else ""

    # Split the title into individual words and lowercase each word
    split_title = [word.lower() for word in title.split()]

    # check for the posting title if the query matches up 
    for each_word in split_title:
        for token in tokens:
            if token in each_word:
                #print(f"match found for the token {token} and the word {each_word}")
                tf_idf_score += 30

    return tf_idf_score

def collect_and_display_results(results: List[Posting], index_of_crawled: Dict[int, int], tokens: List[str], num_of_results: int = 5):
    with open("indices/crawled.txt", "r", encoding="utf-8") as crawled_file:
        for index, posting in enumerate(sorted(results, key=lambda x: x.tf_idf, reverse=True)[:num_of_results], start=1):
            crawled_file.seek(index_of_crawled[posting.id])
            path = crawled_file.readline().strip()
            with open(path, "r") as file:
                data = json.load(file)
                url = data["url"]
                soup = BeautifulSoup(data["content"], "lxml")
                text = soup.get_text()
            contexts = []
            for token in tokens:
                pos = text.lower().find(token)
                if pos == -1:
                    continue
                size = 32
                sentence_before = text[max(pos-size, 0):pos]
                token_text = f"**:blue-background[{text[pos:pos+len(token)]}]**"
                sentence_after = text[pos+len(token):pos+len(token)+size]
                full_sentence = f"{sentence_before}{token_text}{sentence_after}"
                contexts.append(full_sentence.replace("\n", "").replace("\r\n", "").replace("#", ""))
            st.write(f"{index}.\t{soup.title.string}")
            st.write(f"{url}")
            for context in contexts:
                st.markdown(f"...{context}...")

def read_index_files(file_name: str) -> Dict:
    index_dict = {}

    with open(f"indices/{file_name}", "r") as file:
        for line in file:
            key, position = line.split(",")
            if file_name == 'index_of_index.txt':
                index_dict[key] = int(position)
            else:
                index_dict[int(key)] = int(position)

    return index_dict

def correct_spelling(tokens: List[str], posting_keys: Dict[str, List[str]]) -> List[str]:
    corrected_tokens = []
    for token in tokens:
        first_letter = token[0]
        if first_letter in posting_keys:
            possible_tokens = posting_keys[first_letter]
            best_match = difflib.get_close_matches(token, possible_tokens, n=1)
            corrected_tokens.append(best_match[0] if best_match else token)
        else:
            corrected_tokens.append(token)
    return corrected_tokens

def main():
    index_of_index = read_index_files("index_of_index.txt")
    index_of_crawled = read_index_files("index_of_crawled.txt")

    with open("posting_keys.json", "r") as file:
        posting_keys = json.load(file)

    st.title("Search Engine")
    user_input = st.text_input("Enter a query: ")

    if st.button("Search"):
        if user_input:
            start = time.time()
            tokens= user_input.lower().split()
            corrected_tokens = correct_spelling(tokens, posting_keys)
            print(f"Corrected Tokens: {corrected_tokens}")

            # stemming the corrected tokens
            stemmed_tokens = stem_tokens(corrected_tokens)
            print(f"Stemmed Tokens: {stemmed_tokens}")

            # getting postings for normal + stemmed tokens 
            normal_postings = get_postings(corrected_tokens, index_of_index)
            stemmed_postings = get_postings(stemmed_tokens, index_of_index)

            # filtering results 
            normal_results = filter(normal_postings, corrected_tokens, index_of_crawled)
            stemmed_results = filter(stemmed_postings, stemmed_tokens, index_of_crawled)

            # Combine results and remove duplicates
            combined_results = {posting.id: posting for posting in normal_results + stemmed_results}.values()

            if combined_results:
                collect_and_display_results(combined_results, index_of_crawled, corrected_tokens + stemmed_tokens)
            else:
                st.write("No matching tokens found.")

            end = time.time()
            st.write(f"Search completed in {end - start:.2f} seconds")

if __name__ == "__main__":
    main()
