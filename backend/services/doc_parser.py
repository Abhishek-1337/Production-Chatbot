import tempfile
import os
from pathlib import Path
from doc2docx import convert
from docx import Document


def doc_parser(file) -> str:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        doc_path = tmp_path / "input.doc"

        with open(doc_path, "wb") as f:
            f.write(file.file.read())

        convert(str(doc_path))

        docx_path = tmp_path / "input.docx"
        doc = Document(str(docx_path))
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])

    return text
