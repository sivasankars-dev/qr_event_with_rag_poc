from fastapi import FastAPI, Request, Form
import qrcode
from io import BytesIO
from fastapi.responses import StreamingResponse
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.database import engine, SessionLocal
from app.models import Submission, Base
import os
from app.embedding import generate_embedding, client
from app.chroma import collection
from app.schemas import ChatRequest


APP_HOST = os.getenv("APP_HOST", "http://192.168.1.2:8000")
TOP_K = int(os.getenv("TOP_K", "8"))


Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")


def get_event_summaries(db, event_id: int, limit: int = 50) -> list[str]:
    rows = (
        db.query(Submission.summary)
        .filter(Submission.event_id == event_id, Submission.summary.isnot(None))
        .order_by(Submission.id.desc())
        .limit(limit)
        .all()
    )
    return [row[0].strip() for row in rows if row[0] and row[0].strip()]


@app.get("/generate_qr/{event_id}")
def generate_qr(request: Request, event_id: int):
    form_url = f"{APP_HOST}/form/{event_id}"

    qr = qrcode.make(form_url)

    img_io = BytesIO()
    qr.save(img_io, "PNG")
    img_io.seek(0)

    return StreamingResponse(img_io, media_type="image/png")


@app.get("/form/{event_id}", response_class=HTMLResponse)
def show_form(request: Request, event_id: int):
    print("show form", request)
    return templates.TemplateResponse(
        request,
        "form.html",
        {"request": request, "event_id": event_id},
    )


@app.post("/submit/")
def submit_form(
    request: Request,
    event_id: int = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    summary: str = Form(...),
):
    db = SessionLocal()
    submission = Submission(event_id=event_id, name=name, email=email, summary=summary)
    db.add(submission)
    db.commit()
    db.refresh(submission)

    embedding = generate_embedding(summary)

    collection.add(
        documents=[summary],
        embeddings=[embedding],
        ids=[str(submission.id)],
        metadatas=[{"event_id": int(event_id), "name": name}],
    )

    print("CHROMA COUNT:", collection.count())

    # Return thank you page
    return templates.TemplateResponse(
        request,
        "thank_you.html",
        {
            "request": request,
            "event_id": event_id,  # You can pass more data if needed
        },
    )


@app.get("/analytics/{event_id}/total")
def total_registrations(event_id: int):
    db = SessionLocal()
    count = db.query(Submission).filter(Submission.event_id == event_id).count()
    db.close()
    return {"event_id": event_id, "total": count}


@app.get("/organizer/chat/{event_id}", response_class=HTMLResponse)
def organizer_chat_ui(request: Request, event_id: int):
    return templates.TemplateResponse(
        request,
        "chat.html",
        {"request": request, "event_id": event_id},
    )


@app.post("/chat/{event_id}")
def organizer_chat(event_id: int, req: ChatRequest):

    question = req.question.strip()
    if not question:
        return {"answer": f"Please ask a question about event {event_id}."}

    db = SessionLocal()
    try:
        query_embedding = generate_embedding(question)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=TOP_K,
            where={"event_id": event_id},
            include=["documents", "metadatas", "distances"],
        )

        documents = (results.get("documents") or [[]])[0]
        if not documents:
            documents = get_event_summaries(db, event_id, limit=20)

        if not documents:
            return {
                "answer": (
                    "I don't have any participant feedback for this event yet, so I can't answer from data.\n\n"
                    "If you paste a few feedback comments here, I can analyze them. "
                    "Or tell me what you want to optimize (content, food, venue, timing, speakers), and I can suggest a checklist."
                )
            }

        context = "\n\n---\n\n".join(documents)

        system_prompt = """
            You are a helpful, human-sounding event ops assistant.

            You have access to participant feedback snippets as context. Prefer answering using that context.

            Rules:
            - First decide if the organizer message is about the event/feedback. If it is small talk or unrelated (e.g., greetings, chit-chat, general questions), reply naturally and briefly, and ask what they want to know about the event. Do NOT analyze the feedback in that case.
            - Never refuse with "not implemented" or "out of scope". Always be helpful.
            - Do not invent facts about this event. If something is not mentioned in feedback, say it's not mentioned.
            - You MAY provide general best-practice advice, but label it clearly as "General advice (not from feedback)".
            - If the question is unclear, ask 1 clarifying question and still provide what you can.

            Format:
            Event insight: (2–4 sentences, direct and conversational summary of the organizer’s question)

            Key feedback themes:
            - Bullet points summarizing patterns from participant feedback
            - If nothing relevant is mentioned: "No direct mentions in participant feedback"

            Recommended actions:
            Immediate:
            - 1–3 practical actions the organizer can take now

            Next event:
            - 1–3 improvements for future events
            """
            
        user_prompt = f"""
            Event ID: {event_id}

            Organizer Question:
            {question}

            Participant Feedback Data:
            {context}

            Instructions:
            - If the organizer question is small talk/unrelated, ignore the feedback and respond as a normal assistant, then ask what event question they have.
            - First, look for direct mentions in the feedback that answer the question.
            - If there are no direct mentions, say that clearly, then provide general advice and what to ask/measure next.
            - If the organizer asks about problems (e.g., food issues), extract any relevant complaints and quantify loosely (e.g., "mentioned in 2 comments") when possible.
            """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        return {"answer": response.choices[0].message.content}
    finally:
        db.close()


@app.get("/debug/chroma/{event_id}")
def debug_chroma_event(event_id: int):
    return collection.query(
        query_texts=["backend"], n_results=5, where={"event_id": event_id}
    )


@app.get("/debug/chroma")
def debug_chroma_all():
    return collection.get()
