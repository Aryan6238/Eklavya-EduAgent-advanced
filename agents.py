import google.generativeai as genai
import json
import os
import ollama
from typing import List, Optional, Dict, Literal, Tuple, Protocol
from models import (
    GeneratorOutput, ReviewerOutput, TaggerOutput, 
    MCQ, TeacherNotes, Explanation
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

class LLMProvider(Protocol):
    def generate(self, prompt: str) -> str:
        ...

class GeminiProvider:
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        genai.configure(api_key=GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(model_name)

    def generate(self, prompt: str) -> str:
        response = self.model.generate_content(prompt)
        return response.text

class OllamaProvider:
    def __init__(self, model_name: str = "llama3.2"):
        self.model_name = model_name

    def generate(self, prompt: str) -> str:
        try:
            # Use Client for explicit host control
            client = ollama.Client(host='http://127.0.0.1:11434')
            response = client.generate(model=self.model_name, prompt=prompt)
            return response['response']
        except Exception as e:
            print(f"❌ OLLAMA PROVIDER INTERNAL ERROR: {str(e)}")
            raise e

class BaseAgent:
    def __init__(self, model_name: Optional[str] = None):
        self.use_mock = (LLM_PROVIDER == "mock")
        self.provider: Optional[LLMProvider] = None

        if not self.use_mock:
            if LLM_PROVIDER == "ollama":
                self.provider = OllamaProvider(OLLAMA_MODEL)
            elif LLM_PROVIDER == "gemini":
                if GOOGLE_API_KEY:
                    self.provider = GeminiProvider(model_name or "gemini-2.0-flash")
                else:
                    print("⚠️ GOOGLE_API_KEY missing. Falling back to MOCK.")
                    self.use_mock = True

    def _parse_json(self, text: str) -> Dict:
        try:
            # Clean common markdown wrappers first
            text = text.replace("```json", "").replace("```", "").strip()
            
            # Find the largest JSON-like block {}
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                candidate = text[start:end+1]
                
                # --- ROBUST REPAIR ATTEMPT ---
                import re
                # Fix missing commas between properties
                candidate = re.sub(r'([}\]" \t\n])(\s*"[a-zA-Z0-9_]+")\s*:', r'\1,\2:', candidate)
                candidate = candidate.replace(",,", ",")
                
                try:
                    return json.loads(candidate, strict=False)
                except json.JSONDecodeError as e:
                    # If it's a truncation issue (missing trailing }), try to fix it
                    if "Expecting value" in str(e) or "Unterminated string" in str(e):
                         # Try adding a closing brace if it looks truncated
                         try: return json.loads(candidate + "}", strict=False)
                         except: pass
                    pass
            
            return json.loads(text, strict=False)
        except Exception as e:
            # Last ditch: try to find any JSON-like object at all
            return {}

class GeneratorAgent(BaseAgent):
    """
    The GeneratorAgent is responsible for the initial creation of educational content.
    It specializes in pedagogical alignment and grade-appropriate language.
    """
    def generate(self, grade: int, topic: str) -> Tuple[Optional[GeneratorOutput], Optional[str]]:
        if self.use_mock or not self.provider:
            return self._mock_generate(grade, topic), None

        persona = "expert primary school teacher" if grade < 8 else "expert high school professor"
        complexity = "simple and foundational" if grade < 8 else "advanced and theoretical"
        
        prompt = f"""
        Act as an {persona}. Produce a Grade {grade} lesson on "{topic}".
        
        STRICT COMPLIANCE:
        - YOUR ENTIRE RESPONSE MUST BE A SINGLE JSON OBJECT.
        - DO NOT include conversational text, headers, or markdown outside the JSON.
        - START your response with "{{".
        
        STRICT PEDAGOGICAL REQUIREMENTS:
        1. CONTENT: The explanation must reflect Grade {grade} maturity. It should be {complexity}.
        2. MCQ QUANTITY: Produce EXACTLY 4 high-quality MCQs.
        3. MCQ FORMAT: The "question" field must contain ONLY the question text. 
           DO NOT include options like "A) ... B) ..." inside the question field.
        4. MCQ OPTIONS: The "options" array must contain the 4 distinct choices as strings. 
           DO NOT use placeholders like ["A", "B", "C", "D"]. Use meaningful content.
        5. NO QUESTIONS IN TEXT: The "explanation" should be pure lesson content. Do not embed 'Q1', 'Q2' etc. in the text.
        6. NO JUNK SYMBOLS: Use standard math notation. No "‒31/" or weird dashes.

        OUTPUT STRUCTURE:
        {{
            "explanation": {{ "text": "...", "grade": {grade} }},
            "mcqs": [
                {{ "question": "Question text only?", "options": ["Choice 1", "Choice 2", "Choice 3", "Choice 4"], "correct_index": 0 }}
            ],
            "teacher_notes": {{ "learning_objective": "...", "common_misconceptions": ["..."] }}
        }}
        """
        
        last_error = "Unknown"
        # STRICT REQUIREMENT: Retry once if validation fails
        for attempt in range(2):
            try:
                with open("agent_debug.log", "a") as f:
                    f.write(f"\n[GEN] Topic: {topic}, Grade: {grade}, Attempt: {attempt+1}\n")
                
                response_text = self.provider.generate(prompt)
                
                with open("agent_debug.log", "a") as f:
                    f.write(f"Raw response: {response_text[:300]}...\n")
                
                data = self._parse_json(response_text)
                if not data:
                    raise ValueError("Empty or unparsable JSON")
                    
                validated = GeneratorOutput.model_validate(data)
                return validated, None
            except Exception as e:
                last_error = str(e)
                with open("agent_debug.log", "a") as f:
                    f.write(f"Attempt {attempt+1} Failed: {last_error}\n")
                continue # Retry
        
        # All retries failed
        return self._mock_generate(grade, topic), f"Validation failed after 2 retries: {last_error}"

    def _mock_generate(self, grade: int, topic: str) -> GeneratorOutput:
        # High-quality demonstration slates for 'Mock Mode'
        text = f"This lesson covers the fundamentals of {topic} tailored specifically for Grade {grade} level. We explore the core concepts, historical context, and practical applications in a way that is easy to understand and engaging for young learners."
        
        return GeneratorOutput(
            explanation=Explanation(text=text, grade=grade),
            mcqs=[
                MCQ(question=f"Which of the following is a key component of {topic}?", options=["Option A", "Option B", "Option C", "Option D"], correct_index=1),
                MCQ(question=f"Why is {topic} important for us to study?", options=["It's a requirement", "It helps us understand the world", "For better grades", "None of the above"], correct_index=1),
                MCQ(question=f"What is a common application of {topic} in real life?", options=["Cooking", "Transportation", "Entertainment", "Infrastructure"], correct_index=0),
                MCQ(question=f"True or False: Understanding {topic} is helpful for problem solving.", options=["True", "False", "Partially True", "Not relevant"], correct_index=0)
            ],
            teacher_notes=TeacherNotes(
                learning_objective=f"Identify the key concepts of {topic}.", 
                common_misconceptions=[f"Thinking {topic} is only theoretical", f"Confusing {topic} with unrelated concepts"]
            )
        )

class ReviewerAgent(BaseAgent):
    """
    The ReviewerAgent acts as the primary Quality Assurance gate.
    It performs a quantitative audit and determines if content meets production standards.
    """
    def review(self, content: GeneratorOutput) -> ReviewerOutput:
        """
        Audits a content artifact against educational quality standards.
        
        Args:
            content (GeneratorOutput): The draft to evaluate.
            
        Returns:
            ReviewerOutput: A scorecard containing scores (1-5), feedback, and pass/fail decision.
        """
        if self.use_mock or not self.provider:
            return self._mock_review(content)
            
        prompt = f"""
        Act as a strict Quality Assurance auditor evaluating content for Grade {content.explanation.grade}.
        
        STRICT COMPLIANCE:
        - YOUR ENTIRE RESPONSE MUST BE A SINGLE JSON OBJECT.
        - START your response with "{{".
        
        CRITICAL FAILURE CONDITIONS (Score 1 if found):
        1. FORMAT ERROR: If MCQ options (A, B, C...) are embedded inside the "question" text field.
        2. PLACEHOLDERS: If the "options" array contains junk like ["A", "B", "C", "D"] instead of actual choices.
        3. AGE INAPPROPRIATE: If the content is too juvenile (e.g., pizza slices for Grade 11). Grade 11 requires mature, advanced academic language.
        4. HALLUCINATIONS: If you see weird symbols or "‒31/".
        
        SCORING LOGIC:
        - Correctness: Math/factual accuracy.
        - Age Appropriateness: Does it match Grade {content.explanation.grade} rigor?
        - Coverage: Does the explanation prepare the student for all 4 MCQs?
        
        is_passing is true ONLY if ALL scores are 4 or 5.
        
        CONTENT TO AUDIT:
        {content.model_dump_json()}
        
        OUTPUT SCHEMA:
        {{
            "scores": {{ "age_appropriateness": 1-5, "correctness": 1-5, "clarity": 1-5, "coverage": 1-5 }},
            "is_passing": bool,
            "feedback": [ {{ "field": "string", "issue": "string" }} ]
        }}
        """
        
        for attempt in range(2):
            try:
                response_text = self.provider.generate(prompt)
                data = self._parse_json(response_text)
                if not data:
                    raise ValueError("Empty or unparsable JSON")
                return ReviewerOutput.model_validate(data)
            except Exception as e:
                with open("agent_debug.log", "a") as f:
                    f.write(f"Reviewer Attempt {attempt+1} Failed: {str(e)}\n")
                continue
                
        return self._mock_review(content)

    def _mock_review(self, content: GeneratorOutput) -> ReviewerOutput:
        # If the content looks like mock content (contains "Option A"), we should actually FAIL it
        # so the pipeline knows it's not real validated content.
        is_mock = "Option A" in str(content.mcqs) or "Photosynthesis is the amazing process" in content.explanation.text
        
        return ReviewerOutput(
            scores={"age_appropriateness": 5, "correctness": 5, "clarity": 5, "coverage": 5},
            is_passing=not is_mock,
            feedback=[{"field": "mcqs", "issue": "System Fallback: Mock content detected"}] if is_mock else []
        )

class RefinerAgent(BaseAgent):
    """
    The RefinerAgent specializes in targeted modifications.
    It takes specific QA feedback and applies corrective actions to the draft.
    """
    def refine(self, content: GeneratorOutput, feedback: List[Dict]) -> Optional[GeneratorOutput]:
        """
        Improves a draft by addressing specific Reviewer issues.
        
        Args:
            content (GeneratorOutput): The original draft.
            feedback (List[Dict]): Points of failure from the Reviewer.
            
        Returns:
            Optional[GeneratorOutput]: The improved content, or None if refinement failed.
        """
        if self.use_mock or not self.provider:
            return content # Mock just returns same content
            
        prompt = f"""
        Act as a professional Content Refiner. Respond ONLY with a valid JSON object.
        
        STRICT COMPLIANCE:
        - YOUR ENTIRE RESPONSE MUST BE A SINGLE JSON OBJECT.
        - START your response with "{{".
        - DO NOT include conversational text or headers.
        
        REFINEMENT RULES:
        - Address the provided Reviewer feedback.
        - Modify ONLY fields referenced in feedback where possible.
        - Ensure language is mature and academic for Grade {content.explanation.grade}.
        - MCQ "question" must be text ONLY. options must be 4 distinct strings.

        ORIGINAL CONTENT:
        {content.model_dump_json()}
        
        FEEDBACK:
        {json.dumps([f.model_dump() if hasattr(f, "model_dump") else f for f in feedback], indent=2)}
        
        OUTPUT SCHEMA:
        {{
            "explanation": {{ "text": "...", "grade": {content.explanation.grade} }},
            "mcqs": [
                {{ "question": "...", "options": ["...", "...", "...", "..."], "correct_index": int }}
            ],
            "teacher_notes": {{ "learning_objective": "...", "common_misconceptions": ["..."] }}
        }}
        """
        
        try:
            with open("agent_debug.log", "a") as f:
                f.write(f"\n[REFINE] Starting refinement for Grade {content.explanation.grade}\n")
                
            for attempt in range(2):
                try:
                    response_text = self.provider.generate(prompt)
                    data = self._parse_json(response_text)
                    if not data:
                        raise ValueError("Empty or unparsable JSON")
                    return GeneratorOutput.model_validate(data)
                except Exception as e:
                    with open("agent_debug.log", "a") as f:
                        f.write(f"Refinement attempt {attempt+1} fail: {str(e)}\n")
                    continue
                    
            return content # REFINEMENT FAILED: Return original version so it stays rejected but authentic
        except Exception as e:
            with open("agent_debug.log", "a") as f:
                f.write(f"CRITICAL REFINER ERROR: {str(e)}\n")
            return content 

class TaggerAgent(BaseAgent):
    """
    The TaggerAgent performs classification for the content catalog.
    It runs ONLY on approved content to ensure taxonomy integrity.
    """
    def tag(self, content: GeneratorOutput, topic: str) -> TaggerOutput:
        """
        Classifies approved content across pedagogical dimensions.
        
        Args:
            content (GeneratorOutput): Validated educational content.
            topic (str): The targeted topic.
            
        Returns:
            TaggerOutput: Metadata for content organization.
        """
        if self.use_mock or not self.provider:
            return self._mock_tag(content, topic)
            
        prompt = f"""
        Act as an Educational Taxonomist. Classify approved content.
        
        STRICT JSON FORMATTING RULES:
        1. Use ONLY double quotes for keys and string values.
        2. Escape all newlines as "\\n".
        3. No trailing commas.

        APPROVED CONTENT:
        {content.model_dump_json()}
        
        OUTPUT SCHEMA (JSON ONLY):
        {{
            "subject": "string",
            "topic": "{topic}",
            "grade": {content.explanation.grade},
            "difficulty": "Easy" | "Medium" | "Hard",
            "content_type": ["string"],
            "blooms_level": "string"
        }}
        """
        
        for attempt in range(2):
            try:
                response_text = self.provider.generate(prompt)
                data = self._parse_json(response_text)
                if not data:
                    raise ValueError("Empty or unparsable JSON")
                return TaggerOutput.model_validate(data)
            except Exception as e:
                with open("agent_debug.log", "a") as f:
                    f.write(f"Tagger Attempt {attempt+1} Failed: {str(e)}\n")
                continue
                
        return self._mock_tag(content, topic)

    def _mock_tag(self, content: GeneratorOutput, topic: str) -> TaggerOutput:
        return TaggerOutput(
            subject="Science" if "photo" in topic.lower() else "General Education", 
            topic=topic, 
            grade=content.explanation.grade, 
            difficulty="Medium", 
            content_type=["Explanation", "Assessment"], 
            blooms_level="Understanding"
        )
