from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from services.pdf_parser import pdf_parser

def parser(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    return pdf_parser(file)