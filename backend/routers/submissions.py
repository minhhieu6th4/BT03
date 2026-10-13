from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.services.submission_service import SubmissionService

router = APIRouter()

@router.post("/")
async def submit_bot(team_id: int = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    submission = await SubmissionService.create_submission(db, team_id, file)
    return {"message": "Nộp bài thành công!", "filename": file.filename, "submission_id": submission.id}

@router.get("/{id}")
def get_submission(id: int):
    return {"id": id, "status": "VALID"}
