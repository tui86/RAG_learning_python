from __future__ import annotations

from typing import List, Tuple

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter

import pickle

class TextSplitter:
    '''Lớp để tách văn bản thành các chunks nhỏ hơn, phục vụ cho việc truy xuất thông tin và xây dựng chỉ mục.'''
    def __init__(self, chunk_size: int = 1200, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_texts(self, texts: List[str], names: List[str] | None = None) -> Tuple[List[str], List[str]]:
        '''Tách danh sách văn bản thành các chunks nhỏ hơn dựa trên kích thước và độ chồng lấp đã định nghĩa.
        Args:
            texts: Danh sách các văn bản cần tách.
            names: Danh sách tên tương ứng với mỗi văn bản (tùy chọn). '''
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            add_start_index=True,
            strip_whitespace=True,
            separators=[
                "\n#{1,6} ",
                "```\n",
                "\n\\*\\*\\**\n",
                "\n---+\n",
                "\n___+\n",
                "\n\n",
                "\n",
                " ",
                "",
            ],
            is_separator_regex=True,
        )

        chunks: List[str] = []
        sources: List[str] = []
        resolved_names = names or ["unknown"] * len(texts)

        for text, name in zip(texts, resolved_names):
            parts = splitter.split_text(text)
            chunks.extend(parts)
            sources.extend([name] * len(parts))

        with open("./data/chunks.pkl", "wb") as f:
            pickle.dump({"chunks": chunks, "sources": sources}, f)

        return chunks, sources

    def split_markdown(self, texts: List[str], names: List[str] | None = None) -> Tuple[List[Document], List[str]]:
        '''Tách danh sách văn bản Markdown thành các chunks nhỏ hơn dựa trên tiêu đề và cấu trúc Markdown.
        Args:
            texts: Danh sách các văn bản Markdown cần tách.
            names: Danh sách tên tương ứng với mỗi văn bản (tùy chọn). '''
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
        )

        chunks: List[Document] = []
        sources: List[str] = []
        resolved_names = names or ["unknown"] * len(texts)

        for text, name in zip(texts, resolved_names):
            header_documents = header_splitter.split_text(text)
            chunks.extend(header_documents)
            sources.extend([name] * len(header_documents))

        with open("./data/markdown_chunks.pkl", "wb") as f:
            pickle.dump({"chunks": chunks, "sources": sources}, f)

        return chunks, sources