from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Tuple

import pypdf

import pymupdf4llm


class ReadData:
    '''Lớp được dùng để đọc dữ liệu từ các file PDF trong một thư mục, làm sạch văn bản và lưu trữ nội dung đã đọc.'''
    def __init__(self, folder_path: str):
        self.folder_path = Path(folder_path)
        self.all_text: List[str] = []
        self.name_vector: List[str] = []
        self.folder_out_path: str | None = None

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"(?<![.:!?])\n", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def read_pdf(self) -> Tuple[List[str], List[str]]:
        """Đọc tất cả file PDF trong thư mục và trả về nội dung đã làm sạch."""
        all_text: List[str] = []
        name_vector: List[str] = []

        for filename in sorted(os.listdir(self.folder_path)):
            if not filename.endswith(".pdf"):
                continue

            file_path = self.folder_path / filename
            extracted_text = ""
            with open(file_path, "rb") as handle:
                pdf_reader = pypdf.PdfReader(handle)
                for page in pdf_reader.pages:
                    extracted_text += page.extract_text() or ""

            cleaned_text = self._clean_text(extracted_text)
            if cleaned_text:
                all_text.append(cleaned_text)
                name_vector.append(filename)

        self.all_text = all_text
        self.name_vector = name_vector
        return all_text, name_vector

    def read_pdf_as_markdown(self) -> Tuple[List[str], List[str]]:
        """Đọc PDF thành Markdown để giữ lại cấu trúc tiêu đề cho knowledge graph."""
        markdown_texts: List[str] = []
        names: List[str] = []

        for filename in sorted(os.listdir(self.folder_path)):
            if not filename.lower().endswith(".pdf"):
                continue

            markdown_text = pymupdf4llm.to_markdown(str(self.folder_path / filename))
            if markdown_text.strip():
                markdown_texts.append(markdown_text)
                names.append(filename)

        return markdown_texts, names

    def write_text_to_file(self, output_folder: str) -> None:
        """Ghi text đã đọc ra thư mục txt để tiện tra cứu."""
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)

        if not self.all_text:
            raise ValueError("Không có dữ liệu để ghi. Hãy gọi read_pdf() trước.")

        for text, name in zip(self.all_text, self.name_vector):
            output_file = output_path / f"{Path(name).stem}.txt"
            output_file.write_text(text, encoding="utf-8")

        self.folder_out_path = str(output_path)

    def write_text_to_markdown(self, input_folder: str, output_folder: str) -> None:
        """Chuyển đổi tất cả file txt trong thư mục đầu vào sang định dạng markdown và lưu vào thư mục đầu ra."""
        input_path = Path(input_folder)
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)

        for txt_file in sorted(input_path.glob("*.pdf")):
            md_text = pymupdf4llm.to_markdown(str(txt_file))
            output_file = output_path / f"{txt_file.stem}.md"
            output_file.write_text(md_text, encoding="utf-8")

        self.folder_out_path = str(output_path)

    def read_out_text(self, folder_out_path: str | None = None):
        '''Đọc tất cả file txt trong thư mục đầu ra và trả về nội dung và tên file.'''
        if folder_out_path:
            self.folder_out_path = folder_out_path
        if not self.folder_out_path:
            raise ValueError("Chưa chỉ định thư mục đầu ra.")

        files = sorted(Path(self.folder_out_path).glob("*.txt"))
        texts = []
        names = []
        for file in files:
            texts.append(file.read_text(encoding="utf-8"))
            names.append(file.name)
        return texts, names

