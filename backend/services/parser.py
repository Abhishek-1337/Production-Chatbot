from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from services.pdf_parser import pdf_parser

def parser(file: UploadFile = File(...)):
    if file.content_type == "application/pdf":
        print("got here")
        pdf_parser(file)