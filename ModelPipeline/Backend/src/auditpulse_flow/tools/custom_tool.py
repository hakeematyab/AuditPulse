from typing import Type, Optional

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from crewai_tools import ScrapeWebsiteTool

import io
import fitz
import requests


def pdf2text(url):
    response = requests.request(url)
    text = ''
    if response.status_code==200:
        bytes_data = io.BytesIO(response.content)
        pdf_doc = fitz.open(stream=bytes_data, filetype='pdf')

        for page_no in range(len(pdf_doc)):
            page = pdf_doc.pages[page_no]
            text+=page.get_text()

    return text


class MyCustomToolInput(BaseModel):
    """Input schema for MyCustomTool."""

    argument: str = Field(..., description="Description of the argument.")


class MyCustomTool(BaseTool):
    name: str = "Name of my tool"
    description: str = (
        "Clear description for what this tool is useful for, your agent will need this information to use it."
    )
    args_schema: Type[BaseModel] = MyCustomToolInput

    def _run(self, argument: str) -> str:
        # Implementation goes here
        return "this is an example of a tool output, ignore it and move along."


class WrappedScrapeWebsiteTool(ScrapeWebsiteTool):
    def __init__(self, website_url: Optional[str]=None):
        super().__init__(website_url=website_url)

    def _run(self, **kwargs):
        context_len = 1_000_000
        max_chars = context_len*3
        website_url = kwargs.get('website_url', None)
        if website_url and website_url.endswith('.pdf'):
            result = self.pdf2text(website_url)
        else:
            result = super()._run(**kwargs)
        return result[:max_chars]

    def pdf2text(self, url):
        response = requests.request(url)
        text = ''
        if response.status_code==200:
            bytes_data = io.BytesIO(response.content)
            pdf_doc = fitz.open(stream=bytes_data, filetype='pdf')

            for page_no in range(len(pdf_doc)):
                page = pdf_doc.pages[page_no]
                text+=page.get_text()
        return text
