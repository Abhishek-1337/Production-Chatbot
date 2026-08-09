from fastapi import HTTPException, UploadFile

from services import ingest, parser


async def upload_document_controller(file: UploadFile, user_id: str) -> dict:
    allowed_types = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    }

    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="File type is not allowed")

    text = parser.parser(file)
    ingest.ingest_doc(text)

    return {"message": "Document is successfully uploaded. You can start querying the data."}
