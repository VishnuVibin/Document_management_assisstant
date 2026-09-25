from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import os
import uuid
from datetime import datetime

import fitz
from docx import Document

import requests
from dotenv import load_dotenv


load_dotenv()

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY"
)


app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DATABASE = os.path.join(BASE_DIR, "database.db")

# Maximum file size = 10 MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

# Supported file extensions
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt"
}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ============================================================
# DATABASE
# ============================================================

def get_db_connection():
    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


def init_database():

    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            extracted_text TEXT,
            created_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


# ============================================================
# FILE VALIDATION
# ============================================================

def is_allowed_file(filename):

    if not filename:
        return False

    extension = os.path.splitext(filename)[1].lower()

    return extension in ALLOWED_EXTENSIONS


# ============================================================
# TEXT EXTRACTION
# ============================================================

def extract_text(filepath, extension):

    try:

        # -------------------------
        # PDF
        # -------------------------

        if extension == ".pdf":

            text = ""

            pdf = fitz.open(filepath)

            for page in pdf:

                text += page.get_text()

                text += "\n"

            pdf.close()

            return text.strip()


        # -------------------------
        # DOCX
        # -------------------------

        elif extension == ".docx":

            document = Document(filepath)

            paragraphs = []

            for paragraph in document.paragraphs:

                paragraphs.append(paragraph.text)

            return "\n".join(paragraphs).strip()


        # -------------------------
        # TXT
        # -------------------------

        elif extension == ".txt":

            with open(
                filepath,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as file:

                return file.read().strip()


        return ""


    except Exception as error:

        print("Text extraction error:", error)

        return ""


# ============================================================
# SERIALIZE DOCUMENT
# ============================================================

def document_to_dict(document):

    return {
        "id": document["id"],
        "filename": document["filename"],
        "file_type": document["file_type"],
        "file_size": document["file_size"],
        "created_at": document["created_at"]
    }


#AI Integration

def chunk_text(text, chunk_size=1000, overlap=200):

    if not text:
        return []

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end]

        chunks.append(chunk)

        start += chunk_size - overlap

    return chunks

def search_documents(question, documents, top_k=5):

    question_words = set(
        question.lower().split()
    )

    results = []

    for document in documents:

        text = document["extracted_text"] or ""

        chunks = chunk_text(text)

        for chunk in chunks:

            chunk_words = set(
                chunk.lower().split()
            )

            common_words = (
                question_words & chunk_words
            )

            score = len(common_words)

            if score > 0:

                results.append({
                    "score": score,
                    "filename": document["filename"],
                    "document_id": document["id"],
                    "text": chunk
                })

    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return results[:top_k]

def generate_ai_answer(question, context):

    if not OPENROUTER_API_KEY:

        raise Exception(
            "OPENROUTER_API_KEY is not configured"
        )


    prompt = f"""
You are a document question-answering assistant.

Answer the user's question using ONLY the
information provided in the document context.

If the answer cannot be found in the documents,
say:

"I could not find the answer in the uploaded documents."

Do not invent information.

DOCUMENT CONTEXT:

{context}

USER QUESTION:

{question}

Provide a clear and concise answer.
"""


    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",

        headers={
            "Authorization":
                f"Bearer {OPENROUTER_API_KEY}",

            "Content-Type":
                "application/json"
        },

        json={
            "model":
                "meta-llama/llama-3.1-8b-instruct",

            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            "temperature": 0.2
        },

        timeout=60
    )


    if response.status_code != 200:

        print(
            "OpenRouter error:",
            response.text
        )

        raise Exception(
            "AI service request failed"
        )


    data = response.json()


    return (
        data["choices"][0]
        ["message"]["content"]
    )

# ============================================================
# UPLOAD DOCUMENT
# ============================================================


@app.route("/api/documents/upload", methods=["POST"])
def upload_document():

    # Check if file was provided
    if "file" not in request.files:

        return jsonify({
            "error": "No file provided"
        }), 400


    file = request.files["file"]


    # Check filename
    if file.filename == "":

        return jsonify({
            "error": "No file selected"
        }), 400


    original_filename = file.filename

    # Validate extension
    if not is_allowed_file(original_filename):

        return jsonify({
            "error": "Invalid file type. Only PDF, DOCX and TXT files are allowed."
        }), 400


    # Get extension
    extension = os.path.splitext(
        original_filename
    )[1].lower()


    # Generate unique filename
    stored_filename = (
        str(uuid.uuid4()) + extension
    )


    filepath = os.path.join(
        UPLOAD_FOLDER,
        stored_filename
    )


    try:

        # Save file
        file.save(filepath)


        # Get file size
        file_size = os.path.getsize(filepath)


        # Extract text
        extracted_text = extract_text(
            filepath,
            extension
        )


        # Current timestamp
        created_at = datetime.now().isoformat()


        # Store metadata
        connection = get_db_connection()

        cursor = connection.execute(
            """
            INSERT INTO documents
            (
                filename,
                stored_filename,
                filepath,
                file_type,
                file_size,
                extracted_text,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                original_filename,
                stored_filename,
                filepath,
                extension.replace(".", ""),
                file_size,
                extracted_text,
                created_at
            )
        )


        document_id = cursor.lastrowid

        connection.commit()


        # Get inserted document
        document = connection.execute(
            """
            SELECT *
            FROM documents
            WHERE id = ?
            """,
            (document_id,)
        ).fetchone()


        connection.close()


        return jsonify({
            "message": "Document uploaded successfully",
            "document": document_to_dict(document)
        }), 201


    except Exception as error:

        # If database operation fails,
        # remove the uploaded file
        if os.path.exists(filepath):

            os.remove(filepath)


        print("Upload error:", error)


        return jsonify({
            "error": "Failed to upload document"
        }), 500


# ============================================================
# LIST DOCUMENTS
# ============================================================

@app.route("/api/documents", methods=["GET"])
def get_documents():

    try:

        connection = get_db_connection()


        documents = connection.execute(
            """
            SELECT
                id,
                filename,
                file_type,
                file_size,
                created_at
            FROM documents
            ORDER BY created_at DESC
            """
        ).fetchall()


        connection.close()


        return jsonify({
            "documents": [
                document_to_dict(document)
                for document in documents
            ]
        }), 200


    except Exception as error:

        print("List error:", error)


        return jsonify({
            "error": "Failed to retrieve documents"
        }), 500


# ============================================================
# DOWNLOAD DOCUMENT
# ============================================================

@app.route(
    "/api/documents/<document_id>/download",
    methods=["GET"]
)
def download_document(document_id):

    # Validate document ID
    try:

        document_id = int(document_id)

    except ValueError:

        return jsonify({
            "error": "Invalid document ID"
        }), 400


    connection = get_db_connection()


    document = connection.execute(
        """
        SELECT *
        FROM documents
        WHERE id = ?
        """,
        (document_id,)
    ).fetchone()


    connection.close()


    # Document doesn't exist
    if document is None:

        return jsonify({
            "error": "Document not found"
        }), 404


    # Physical file doesn't exist
    if not os.path.exists(document["filepath"]):

        return jsonify({
            "error": "Document file not found"
        }), 404


    try:

        return send_file(
            document["filepath"],
            as_attachment=True,
            download_name=document["filename"]
        )


    except Exception as error:

        print("Download error:", error)


        return jsonify({
            "error": "Failed to download document"
        }), 500


# ============================================================
# DELETE DOCUMENT
# ============================================================

@app.route(
    "/api/documents/<document_id>",
    methods=["DELETE"]
)
def delete_document(document_id):

    # Validate ID
    try:

        document_id = int(document_id)

    except ValueError:

        return jsonify({
            "error": "Invalid document ID"
        }), 400


    connection = get_db_connection()


    document = connection.execute(
        """
        SELECT *
        FROM documents
        WHERE id = ?
        """,
        (document_id,)
    ).fetchone()


    # Document doesn't exist
    if document is None:

        connection.close()

        return jsonify({
            "error": "Document not found"
        }), 404


    try:

        # Delete physical file
        if os.path.exists(document["filepath"]):

            os.remove(document["filepath"])


        # Delete database metadata
        connection.execute(
            """
            DELETE FROM documents
            WHERE id = ?
            """,
            (document_id,)
        )


        connection.commit()

        connection.close()


        return jsonify({
            "message": "Document deleted successfully"
        }), 200


    except Exception as error:

        connection.close()

        print("Delete error:", error)


        return jsonify({
            "error": "Failed to delete document"
        }), 500


# ============================================================
# GET DOCUMENT TEXT
# ============================================================

@app.route(
    "/api/documents/<document_id>/text",
    methods=["GET"]
)
def get_document_text(document_id):

    try:

        document_id = int(document_id)

    except ValueError:

        return jsonify({
            "error": "Invalid document ID"
        }), 400


    connection = get_db_connection()


    document = connection.execute(
        """
        SELECT id, filename, extracted_text
        FROM documents
        WHERE id = ?
        """,
        (document_id,)
    ).fetchone()


    connection.close()


    if document is None:

        return jsonify({
            "error": "Document not found"
        }), 404


    return jsonify({
        "id": document["id"],
        "filename": document["filename"],
        "text": document["extracted_text"] or ""
    }), 200


# ============================================================
# GLOBAL ERROR FOR LARGE FILES
# ============================================================

@app.errorhandler(413)
def file_too_large(error):

    return jsonify({
        "error": "File too large. Maximum size is 10 MB."
    }), 413


@app.route("/api/chat", methods=["POST"])
def chat():

    data = request.get_json()


    # --------------------------------
    # Validate request
    # --------------------------------

    if not data:

        return jsonify({
            "error": "Request body is required"
        }), 400


    question = data.get("question")


    if not question:

        return jsonify({
            "error": "Question is required"
        }), 400


    question = question.strip()


    if not question:

        return jsonify({
            "error": "Question cannot be empty"
        }), 400


    # --------------------------------
    # Get documents
    # --------------------------------

    connection = get_db_connection()


    documents = connection.execute(
        """
        SELECT
            id,
            filename,
            extracted_text
        FROM documents
        WHERE extracted_text IS NOT NULL
        AND extracted_text != ''
        """
    ).fetchall()


    connection.close()


    if not documents:

        return jsonify({
            "answer":
                "There are no documents with extracted text available.",
            "sources": []
        }), 200


    # --------------------------------
    # Search documents
    # --------------------------------

    search_results = search_documents(
        question,
        documents,
        top_k=5
    )


    # --------------------------------
    # No relevant context
    # --------------------------------

    if not search_results:

        return jsonify({
            "answer":
                "I could not find the answer in the uploaded documents.",
            "sources": []
        }), 200


    # --------------------------------
    # Build context
    # --------------------------------

    context_parts = []


    for index, result in enumerate(
        search_results
    ):

        context_parts.append(
            f"""
SOURCE {index + 1}

Document:
{result['filename']}

Content:
{result['text']}
"""
        )


    context = "\n".join(
        context_parts
    )


    # --------------------------------
    # Generate AI answer
    # --------------------------------

    try:

        answer = generate_ai_answer(
            question,
            context
        )


    except Exception as error:

        print(
            "AI error:",
            error
        )

        return jsonify({
            "error":
                "Failed to generate AI answer"
        }), 500


    # --------------------------------
    # Prepare sources
    # --------------------------------

    sources = []


    for result in search_results:

        sources.append({
            "document_id":
                result["document_id"],

            "filename":
                result["filename"],

            "text":
                result["text"]
        })


    # --------------------------------
    # Return response
    # --------------------------------

    return jsonify({

        "answer": answer

    }), 200

# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/api/health", methods=["GET"])
def health():

    return jsonify({
        "status": "Backend is running"
    }), 200


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    init_database()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )