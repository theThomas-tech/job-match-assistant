"""Test helpers: a fake AI model, a fake embedder and a tiny PDF builder."""

import hashlib
import math
import re

from app.embeddings import EMBEDDING_DIM
from app.llm import LLMResult


class FakeEmbedder:
    """Bag-of-words vectors: texts sharing more words are more similar. Fast and deterministic."""

    model_name = "fake-embedder"

    def __init__(self):
        self.texts: list[str] = []

    def embed(self, texts):
        self.texts.extend(texts)
        return [self._vector(text) for text in texts]

    def embed_query(self, text):
        return self._vector(text)

    @staticmethod
    def _vector(text):
        vector = [0.0] * EMBEDDING_DIM
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % EMBEDDING_DIM] += 1.0
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norm for x in vector]


class FakeProvider:
    """Stands in for a real model. Give it the replies to return, in order.

    A reply can be a string (the model's JSON answer) or an exception to raise.
    """

    name = "fake"
    model = "fake-model"

    def __init__(self, *replies):
        self.replies = list(replies)
        self.prompts: list[str] = []

    def complete_json(self, system, user, schema):
        self.prompts.append(user)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return LLMResult(text=reply, model=self.model, input_tokens=100, output_tokens=50, latency_ms=10)

    def cost_usd(self, result):
        return 0.001


def make_pdf(lines: list[str]) -> bytes:
    """Build a minimal one-page PDF containing these lines of text (no parentheses allowed)."""
    content = "BT /F1 11 Tf 50 750 Td 14 TL " + " ".join(f"({line}) Tj T*" for line in lines) + " ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{number} 0 obj\n{obj}\nendobj\n".encode()
    xref_at = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode()
    pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    return pdf


RESUME_LINES = [
    "Ama Mensah - Software Engineer - Accra, Ghana",
    "Skills: Python, FastAPI, PostgreSQL, Node.js, Docker, Go",
    "Experience: Backend Intern at Hubtel, 2024-06 to 2024-09",
    "Built payment reconciliation APIs in FastAPI used by 3 internal teams",
    "Education: BSc Computer Science, University of Ghana, 2025",
    "Projects: Job matcher - ranks job postings against a resume using embeddings",
]

PROFILE = {
    "headline": "Backend-focused software engineer",
    "location": "Accra, Ghana",
    "total_years_experience": 0.25,
    "skills": ["Python", "FastAPI", "PostgreSQL", "NodeJS", "Docker", "Go"],
    "experience": [
        {
            "title": "Backend Intern",
            "organization": "Hubtel",
            "start": "2024-06",
            "end": "2024-09",
            "highlights": ["Built payment reconciliation APIs in FastAPI"],
        }
    ],
    "projects": [
        {"name": "Job matcher", "summary": "Ranks job postings against a resume.", "technologies": []}
    ],
    "education": [
        {"qualification": "BSc Computer Science", "institution": "University of Ghana", "end_year": "2025"}
    ],
    "certifications": [],
}
