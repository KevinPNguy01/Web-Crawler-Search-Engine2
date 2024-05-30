from pathlib import Path
from bs4 import BeautifulSoup
import msgspec
import lxml
from typing import List
import re
from openai import OpenAI

OPENAI_AI_KEY = ""
CLIENT = OpenAI(api_key=OPENAI_AI_KEY)

class WebPage(msgspec.Struct, gc=False):
	url: str
	content: str
	encoding: str
	soup: BeautifulSoup = None

	def __post_init__(self):
		self.soup = BeautifulSoup(self.content, "lxml")
	
	def get_title(self) -> str:
		title = self.soup.find("title")
		title = title.string if title else ""
		title = re.sub(r'\s+',' ', title if title else "").strip()
		return title
	
	def get_text(self) -> List[str]:
		[s.decompose() for s in self.soup(['style', 'script', '[document]', 'head', 'title'])]
		return [re.sub(r'\s+',' ', string) for string in self.soup.stripped_strings if string]
	
	def get_summary(self) -> str:
		response = CLIENT.chat.completions.create(
			model="gpt-3.5-turbo",
			messages=[
				{"role": "system", "content": "Summarize following webpage content using 30 completion_tokens or less. Not complete sentence, don't mention the word summary"},
				{"role": "user", "content": "\n".join(s for s in self.get_text() if len(s) >= 5)}
			]
		)
		return response.choices[0].message.content
	
	@classmethod
	def from_path(cls, path: Path):
		with open(path, "r", encoding="utf-8") as f:
			return decoder.decode(f.read())

decoder = msgspec.json.Decoder(type=WebPage)

if __name__ == "__main__":
	webpage = WebPage.from_path(Path("DEV\\ngs_ics_uci_edu\\f46429fcd2d984473eac85f30165384427dbd4471e7750f7989fc79b2a70ddb2.json"))
	print(webpage.url)
	print(webpage.get_title())
	print(webpage.get_text())
	print(webpage.get_summary())