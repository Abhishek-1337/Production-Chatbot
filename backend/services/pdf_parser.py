from pypdf import PdfReader

def pdf_parser(file) -> str:
    reader = PdfReader(file.file)
    number_of_pages = len(reader.pages)

    text : str = ""
    for page in reader.pages:
        text += page.extract_text()

    return text