from datetime import datetime
from models import (
    RunArtifact, AttemptArtifact, FinalContent, 
    InputRequest, GeneratorOutput, ReviewerOutput
)
from agents import GeneratorAgent, ReviewerAgent, RefinerAgent, TaggerAgent
from database import save_run
import uuid

class GovernanceConfig:
    """Centralized governance parameters for the AI pipeline."""
    MAX_GEN_RETRIES = 2
    MAX_REFINE_ATTEMPTS = 2
    MIN_QUALITY_SCORE = 4  # Threshold for age_appropriateness, correctness, etc.
    DEFAULT_USER = "anonymous"

class Orchestrator:
    """
    The Orchestrator is the central governing body of the AI content pipeline.
    It manages the deterministic lifecycle: Generate -> Review -> (Refine) -> Tag.
    
    Attributes:
        generator (GeneratorAgent): Handles initial draft creation.
        reviewer (ReviewerAgent): Performs quantitative quality audits.
        refiner (RefinerAgent): Handles bounded refinement based on feedback.
        tagger (TaggerAgent): Classifies approved content for the catalog.
    """
    def __init__(self):
        self.generator = GeneratorAgent()
        self.reviewer = ReviewerAgent()
        self.refiner = RefinerAgent()
        self.tagger = TaggerAgent()
        
    async def run_pipeline(self, grade: int, topic: str, user_id: str = GovernanceConfig.DEFAULT_USER) -> RunArtifact:
        """
        Executes the full governed pipeline for a given grade and topic.
        
        Args:
            grade (int): Target educational grade level.
            topic (str): Subject matter to generate content for.
            user_id (str): Identifier for persistence and audit tracking.
            
        Returns:
            RunArtifact: A complete, immutable record of the entire generation lifecycle.
        """
        print(f"Starting deterministic pipeline for Grade {grade}, Topic: {topic}")
        # Initialize Run Artifact
        run = RunArtifact(
            user_id=user_id,
            input=InputRequest(grade=grade, topic=topic, user_id=user_id)
        )
        
        # --- PHASE 1: GENERATION (INITIAL DRAFT) ---
        print("PHASE 1: Generation...")
        current_content = None
        for gen_attempt_idx in range(1, GovernanceConfig.MAX_GEN_RETRIES + 1):
            print(f"  Attempt {gen_attempt_idx}: Calling Generator...")
            content, error = self.generator.generate(grade, topic)
            
            # Audit generation attempt
            attempt_log = AttemptArtifact(
                attempt=len(run.attempts) + 1,
                draft=content,
                validation_error=error
            )
            run.attempts.append(attempt_log)
            
            if content:
                print("  Success: Valid draft produced.")
                current_content = content
                break
            else:
                print(f"  Validation Error (Attempt {gen_attempt_idx}): {error}")
                if gen_attempt_idx == 2:
                    print("  Critical: Generation failed all retries.")
                    run.final = FinalContent(status="rejected", content=None)
        
        # If generation failed, wrap up
        if not current_content:
            run.timestamps.finished_at = datetime.utcnow()
            save_run(run)
            return run

        # --- PHASE 2: REVIEW & REFINEMENT LOOP ---
        print("PHASE 2: Review & Refinement...")
        refine_attempts = 0
        
        while refine_attempts <= GovernanceConfig.MAX_REFINE_ATTEMPTS:
            print(f"  Cycle {refine_attempts + 1}: Reviewing Content...")
            
            # Review the current draft
            review = self.reviewer.review(current_content)
            print(f"  Review Result: {'PASS' if review.is_passing else 'FAIL'} (Scores: {review.scores})")
            
            # Update the latest attempt artifact with the review
            run.attempts[-1].review = review
            
            if review.is_passing:
                # --- PHASE 3: CLASSIFICATION (TAGGING) ---
                print("PHASE 3: Tagging Approved Content...")
                tags = self.tagger.tag(current_content, topic)
                run.final = FinalContent(
                    status="approved",
                    content=current_content,
                    tags=tags
                )
                break
            else:
                # Failure -> Refine if bounded attempts remain
                if refine_attempts < GovernanceConfig.MAX_REFINE_ATTEMPTS:
                    print(f"  Action: Triggering Refinement (Attempts remaining: {GovernanceConfig.MAX_REFINE_ATTEMPTS - refine_attempts})...")
                    refined_content = self.refiner.refine(current_content, review.feedback)
                    
                    if refined_content:
                        # Record refinement in the CURRENT attempt artifact
                        run.attempts[-1].refined = refined_content
                        
                        current_content = refined_content
                        refine_attempts += 1
                        
                        # Prepare for the next review cycle with a NEW attempt artifact
                        run.attempts.append(AttemptArtifact(
                            attempt=len(run.attempts) + 1,
                            draft=current_content
                        ))
                    else:
                        print("  Critical: Refiner failed to produce content.")
                        run.final = FinalContent(status="rejected", content=current_content)
                        break
                else:
                    print(f"  Critical: Max refinements ({GovernanceConfig.MAX_REFINE_ATTEMPTS}) reached without approval.")
                    run.final = FinalContent(status="rejected", content=current_content)
                    break
        
        # --- FINALIZATION ---
        if not run.final:
             run.final = FinalContent(status="rejected", content=current_content)

        run.timestamps.finished_at = datetime.utcnow()
        save_run(run)
        print(f"Pipeline Finished. Final Status: {run.final.status}")
        return run
