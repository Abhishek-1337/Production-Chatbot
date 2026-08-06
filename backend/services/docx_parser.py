from docx import Document


def docx_parser(file) -> str:
    doc = Document(file.file)
    text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
    return text
