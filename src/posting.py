from pathlib import Path
from typing import Dict, Self
from src.tokenizer import *
import msgspec

class WebPage(msgspec.Struct, gc=False):
    url: str
    content: str
    encoding: str

decoder = msgspec.json.Decoder(type=WebPage)

class Posting: 
    @staticmethod
    def get_postings(file_path: Path, id: int) -> Dict[str, Self]:
        # Returns a dict of tokens to postings for this file.
        with open(file_path) as file:
            page = decoder.decode(file.read())
            # Extract text from webpage content.
            text = extract_text(page.content)
            # Tokenize text.
            frequencies = computeWordFrequencies(tokenize(text))
            # Create postings for each token and return dict.
            return {token: Posting(id, frequency) for token, frequency in frequencies.items()}

    def __init__(self, id: int, tf_idf: float) -> Self: 
        self.id = id
        self.tf_idf = tf_idf

    def __str__(self) -> str:
        return f"{self.id},{self.tf_idf}"
        
    @classmethod
    def from_string(cls: Self, string: str) -> Self:
        data = string.split(",")
        id = int(data[0])
        tf_idf = float(data[1])
        return cls(id, tf_idf)