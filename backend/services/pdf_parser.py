from pypdf import PdfReader

def pdf_parser(file):
    reader = PdfReader(file.file)
    number_of_pages = len(reader.pages)
    page = reader.pages[0]
    text = page.extract_text()
    print(text)