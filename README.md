# Eklavya: Governed Multi-Agent AI Content Pipeline 🛡️🎓

Eklavya is a production-grade, auditable AI content generation platform. It transforms the standard LLM "chat" interface into a rigorous, governed manufacturing process for educational materials.

## 🚀 Repository Details
**Repository**: [Aryan6238/Eklavya-EduAgent-advanced](https://github.com/Aryan6238/Eklavya-EduAgent-advanced)

## 🏗️ Architecture: The Governed Pipeline
The system moves beyond simple prompts by implementing a deterministic `Generate -> Review -> Refine -> Tag` lifecycle managed by four specialized agents:

1.  **Generator Agent**: Produces initial drafts (Grade 1-12) using strict Pydantic schemas.
2.  **Reviewer Agent**: Performs quantitative quality audits (1-5 grading) on age-appropriateness, accuracy, and coverage.
3.  **Refiner Agent**: Applies targeted corrections based on Reviewer feedback to avoid content drift.
4.  **Tagger Agent**: Classifies approved content with pedagogical metadata (Bloom's Taxonomy, Difficulty).

## 🛠️ Tech Stack
- **Backend**: FastAPI (Async Python)
- **Governance**: Pydantic v2 (Strict Schema Validation)
- **Intelligence**: Google Gemini 2.0 / Ollama (Local Llama 3.2)
- **Persistence**: SQLite (Immutable RunArtifact Audit Trails)
- **Frontend**: Vanilla JS + CSS (Nocturne Dark Design System)

## ⚙️ Local Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   Create a `.env` file from the provided `.env.example`:
   ```env
   GOOGLE_API_KEY=your_key_here
   LLM_PROVIDER=gemini # or 'ollama'
   OLLAMA_MODEL=llama3.2:latest
   ```

3. **Run the Dashboard**:
   ```bash
   uvicorn main:app --reload
   ```
   Visit: `http://localhost:8000`

## 🧪 Verification & Testing
The project includes a mandatory governance test suite. Run it to verify the safety gates:
```bash
pytest test_orchestrator.py
```
This suite verifies:
- ✅ Schema validation recovery.
- ✅ Successful content refinement loops.
- ✅ Rejection of low-quality content after max retries.

## 🛡️ Governance & Auditability
Every run generates a **RunArtifact** — a full forensic record containing every draft attempt, every score, and every piece of feedback. This ensures the system is not a "black box" and results are 100% reproducible and auditable.

---
*Developed for AI Assessment Part 2: Governed, Auditable Pipeline Compliance.*
