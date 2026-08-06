from fastapi import File, HTTPException, UploadFile
from services.pdf_parser import pdf_parser
from services.docx_parser import docx_parser
from services.doc_parser import doc_parser


def parser(file: UploadFile = File(...)):
    content_type = file.content_type

    if content_type == "application/pdf":
        return pdf_parser(file)
    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return docx_parser(file)
    elif content_type == "application/msword":
        return doc_parser(file)
    elif content_type == "text/plain":
        return file.file.read().decode("utf-8")
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type}"
        )