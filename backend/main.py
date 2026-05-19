from fastapi import FastAPI, UploadFile, File

app = FastAPI()

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    allowed_types = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    }
    # if file.upload_type not in allowed_types:
    #     raise HTTPException(status = 400, description = "File type is not allowed")
    
    contents = await file.read()
    print(contents)

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(contents),
    }