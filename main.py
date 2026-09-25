from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
from docx import Document
import io
import re


app = FastAPI()


# Allow the HTML frontend to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "Braille Generator Backend is running"
    }


# ---------------------------------------------------------
# PDF TEXT CLEANING
# ---------------------------------------------------------

def clean_pdf_text(text):
    """
    Clean PDF extraction while preserving:

    - paragraphs
    - numbered lists
    - bullet lists
    - measurements
    - equations
    - symbol examples
    - intentional separate lines

    while joining normal visual line wraps.
    """

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    lines = text.split("\n")

    output = []
    current_paragraph = []

    def flush_paragraph():
        if current_paragraph:
            output.append(
                " ".join(current_paragraph)
            )
            current_paragraph.clear()

    for line in lines:

        line = line.strip()

        # Blank line
        if not line:
            flush_paragraph()

            if output and output[-1] != "":
                output.append("")

            continue

        # Numbered list
        if re.match(r"^\d+\.\s", line):
            flush_paragraph()
            output.append(line)
            continue

        # Bullet list
        if line.startswith("•"):
            flush_paragraph()
            output.append(line)
            continue

        # Dash / star list
        if line.startswith("- ") or line.startswith("* "):
            flush_paragraph()
            output.append(line)
            continue

        # Measurements / standalone numbers
        if re.match(
            r"^\d+(?:\.\d+)?(?:\s*[a-zA-Z]+)?$",
            line
        ):
            flush_paragraph()
            output.append(line)
            continue

        # Equations / symbol lines
        if (
            "=" in line
            or "%" in line
            or "@" in line
            or " & " in line
        ):
            flush_paragraph()
            output.append(line)
            continue

        # Degree / angle lines
        if "°" in line:
            flush_paragraph()
            output.append(line)
            continue

        # Normal paragraph text
        current_paragraph.append(line)

    flush_paragraph()

    cleaned_output = []
    previous_blank = False
    for line in output:
        # Never insert blank lines between consecutive list items
        if (
            cleaned_output
            and line.startswith(("•", "- ", "* "))
            and cleaned_output[-1] != ""
            and (
                cleaned_output[-1].startswith("•")
                or cleaned_output[-1].startswith("- ")
                or cleaned_output[-1].startswith("* ")
            )
        ):
            previous_blank = False
            cleaned_output.append(line)
            continue

        if line == "":
            if not previous_blank:
                cleaned_output.append("")

            previous_blank = True

        else:
            cleaned_output.append(line)
            previous_blank = False

    return "\n".join(cleaned_output).strip()


# ---------------------------------------------------------
# PDF UPLOAD
# ---------------------------------------------------------

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):

    # Read uploaded PDF
    pdf_bytes = await file.read()


    # Open PDF from memory
    document = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )


    extracted_text = ""


    # Extract text from every page
    for page in document:

        extracted_text += page.get_text()

        extracted_text += "\n"


    document.close()


    # Clean PDF visual line wrapping
    extracted_text = clean_pdf_text(
        extracted_text
    )


    return {
        "filename": file.filename,
        "text": extracted_text
    }


# ---------------------------------------------------------
# DOCX UPLOAD
# ---------------------------------------------------------

@app.post("/upload-docx")
async def upload_docx(file: UploadFile = File(...)):

    docx_bytes = await file.read()


    document = Document(
        io.BytesIO(docx_bytes)
    )


    extracted_text = "\n".join(
        paragraph.text
        for paragraph in document.paragraphs
    )


    return {
        "filename": file.filename,
        "text": extracted_text
    }


# ---------------------------------------------------------
# OPTIONAL TEXT PROCESSING
# ---------------------------------------------------------

@app.post("/process-text")
async def process_text(data: dict):

    text = data.get("text", "")


    if not text.strip():

        return {
            "error": "No text provided"
        }


    # The main prototype currently uses the
    # local deterministic processing in the frontend.
    #
    # This endpoint is kept so the frontend does not
    # break if the AI button is pressed.

    return {
        "text": text,
        "message": (
            "AI processing is currently disabled. "
            "The document was returned unchanged."
        )
    }