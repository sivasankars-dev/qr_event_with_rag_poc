from fastapi import FastAPI, Request, Form, UploadFile, File
import qrcode
from io import BytesIO
from fastapi.responses import StreamingResponse
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.database import engine, SessionLocal
from app.models import Submission, Base, SubmissionEmbedding
import os
from app.embedding import generate_embedding, client
from app.chroma import collection
from app.schemas import ChatRequest


APP_HOST = os.getenv("APP_HOST", "http://192.168.1.2:8000")


Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

@app.get("/generate_qr/{event_id}")
def generate_qr(request: Request, event_id: int):
    form_url = f"{APP_HOST}/form/{event_id}"

    qr = qrcode.make(form_url)

    img_io = BytesIO()
    qr.save(img_io, 'PNG')
    img_io.seek(0)

    return StreamingResponse(img_io, media_type="image/png")

@app.post("/scan_qr/")
def scan_qr(file: UploadFile = File(...)):
    print("entered scan_qr")
    image = Image.open(file.file).convert("RGB")

    image_np = np.array(image)
    image_cv = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)

    dectector = cv2.QRCodeDetector()
    data, points, _ = dectector.detectAndDecode(image_cv)

    if not data:
        return {"error": "No QR code found"}

    return {"data": data}

@app.get("/form/{event_id}", response_class=HTMLResponse)
def show_form(request: Request, event_id: int):
    print("show form", request)
    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "event_id": event_id
        }
    )

@app.post("/submit/")
def submit_form(
    request: Request,
    event_id: int = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    summary: str = Form(...)
):
    db = SessionLocal()
    submission = Submission(
        event_id=event_id,
        name=name,
        email=email,
        summary=summary
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    embedding = generate_embedding(summary)

    collection.add(
        documents=[summary],
        embeddings=[embedding],
        ids=[str(submission.id)],
        metadatas=[{"event_id": int(event_id), "name": name}]
    )

    chroma_client.persist()

    print("CHROMA COUNT:", collection.count())

    # Return thank you page
    return templates.TemplateResponse(
        "thank_you.html",
        {"request": request, "event_id": event_id}  # You can pass more data if needed
    )

@app.get("/analytics/{event_id}/total")
def total_registrations(event_id: int):
    db = SessionLocal()
    count = db.query(Submission).filter(
        Submission.event_id == event_id
    ).count()
    db.close()
    return {"event_id": event_id, "total": count}

@app.get("/organizer/chat/{event_id}", response_class=HTMLResponse)
def organizer_chat_ui(request: Request, event_id: int):
    return templates.TemplateResponse(
        "chat.html",
        {"request": request, "event_id": event_id}
    )

@app.post("/chat/{event_id}")
def organizer_chat(event_id: int, req: ChatRequest):

    question = req.question

    query_embedding = generate_embedding(question)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=2,
        where={"event_id": event_id}  
    )

    documents = results["documents"][0]

    if not documents:
        return {"answer": "No relevant data found for this event."}

    context = "\n".join(documents)

    prompt = f"""
    You are an assistant answering ONLY from event participant data.
    if participant asked improvision tips or guide provide that.

    Participant inputs:
    {context}

    Question:
    {question}
    """

    print("profmts", context)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    print("answers", response.choices[0].message.content)

    return {"answer": response.choices[0].message.content}

def is_analytics_question(q: str):
    keywords = ["how many", "count", "total", "number"]
    return any(k in q.lower() for k in keywords)

@app.get("/debug/chroma/{event_id}")
def debug_chroma_event(event_id: int):
    return collection.query(
        query_texts=["backend"],
        n_results=5,
        where={"event_id": event_id}
    )

@app.get("/debug/chroma")
def debug_chroma_all():
    return collection.get()
