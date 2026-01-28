import os
from dotenv import load_dotenv
from openai import OpenAI
import chromadb

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
chroma_client = chromadb.Client()

# Create a collection (like a table in SQL)
collection = chroma_client.create_collection(
    name="documentation",
    metadata={"description": "Product documentation embeddings"}
)

def get_embedding(text, model="text-embedding-3-small"):
    """Generate embedding for a piece of text."""
    text = text.replace("\n", " ")
    response = client.embeddings.create(
        input=[text],
        model=model
    )
    return response.data[0].embedding

def semantic_search(query, n_results=3):
    """Search for documents similar to the query."""
    # Generate embedding for the query
    query_embedding = get_embedding(query)
    
    # Search in vector database
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    
    return results

# Sample documentation
documents = [
    "To reset your password, go to Settings > Security > Change Password. Enter your current password and then your new password twice.",
    "You can update your email address in the Account section. Click on Profile, then Edit Email, and verify the change via the confirmation link.",
    "To delete your account, navigate to Settings > Privacy > Delete Account. This action is permanent and cannot be undone.",
    "Enable two-factor authentication in Security settings. You'll need a mobile app like Google Authenticator or Authy.",
    "Export your data by going to Settings > Data & Privacy > Download Data. Processing may take up to 48 hours.",
    "Change your username in Profile settings. Note that usernames must be unique and can only be changed once every 30 days.",
    "To recover a deleted item, check your Trash folder within 30 days. After 30 days, items are permanently removed.",
    "Manage notification preferences in Settings > Notifications. You can customize alerts for email, push, and SMS."
]

# Metadata for each document
metadata = [
    {"category": "security", "topic": "password"},
    {"category": "account", "topic": "email"},
    {"category": "account", "topic": "deletion"},
    {"category": "security", "topic": "2fa"},
    {"category": "privacy", "topic": "data-export"},
    {"category": "account", "topic": "username"},
    {"category": "recovery", "topic": "trash"},
    {"category": "settings", "topic": "notifications"}
]

print("Generating embeddings and storing documents...")

# Generate embeddings for all documents
embeddings = [get_embedding(doc) for doc in documents]

# Store in vector database
collection.add(
    embeddings=embeddings,
    documents=documents,
    metadatas=metadata,
    ids=[f"doc_{i}" for i in range(len(documents))]
)

print(f"✓ Stored {len(documents)} documents in vector database!")

def optimized_rag(user_question: str, max_context_tokens: int = 2000):
    """
    RAG with context window management.
    Ranks and selects best chunks within token budget.
    """
    # Retrieve more candidates than we'll use
    results = semantic_search(user_question, n_results=10)
    
    # Rank by similarity (distance)
    ranked_docs = sorted(
        zip(results['documents'][0], results['distances'][0]),
        key=lambda x: x[1]  # Lower distance = higher similarity
    )
    
    # Select documents within token budget
    selected_docs = []
    total_tokens = 0
    
    for doc, distance in ranked_docs:
        # Rough token estimate (1 token ≈ 4 characters)
        doc_tokens = len(doc) // 4
        
        if total_tokens + doc_tokens <= max_context_tokens:
            selected_docs.append({
                'text': doc,
                'similarity': 1 - distance
            })
            total_tokens += doc_tokens
        else:
            break
    
    print(f"📊 Retrieved {len(ranked_docs)} candidates")
    print(f"✂️  Selected {len(selected_docs)} docs ({total_tokens} tokens)")
    
    # Build optimized context
    context = "\n\n".join([
        f"[Relevance: {doc['similarity']:.2f}] {doc['text']}"
        for doc in selected_docs
    ])
    
    # Generate answer
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Answer using the provided context."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {user_question}"}
        ]
    )
    
    return response.choices[0].message.content, selected_docs

# Demo
print("\n" + "="*60)
print("CONTEXT OPTIMIZATION DEMO")
print("="*60 + "\n")

answer, selected = optimized_rag("How can I manage my account security?", max_context_tokens=200)

print(f"Selected documents:")
for i, doc in enumerate(selected, 1):
    print(f"{i}. Similarity: {doc['similarity']:.3f}")
    print(f"   {doc['text'][:80]}...\n")

print(f"Answer:\n{answer}")