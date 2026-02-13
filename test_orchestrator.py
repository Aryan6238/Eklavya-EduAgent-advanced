import asyncio
import json
import pytest
from unittest.mock import MagicMock, patch
from orchestrator import Orchestrator
from models import GeneratorOutput, ReviewerOutput, Explanation, TeacherNotes, RunArtifact, TaggerOutput

# --- Mock Response Helpers ---

def create_valid_tagger_output(grade=5, topic="Test"):
    return TaggerOutput(
        subject="Science",
        topic=topic,
        grade=grade,
        difficulty="Medium",
        content_type=["Explanation"],
        blooms_level="Understanding"
    )

def create_valid_generator_output(grade=5, topic="Test"):
    return GeneratorOutput(
        explanation=Explanation(text="Test content", grade=grade),
        mcqs=[],
        teacher_notes=TeacherNotes(learning_objective="Obj", common_misconceptions=[])
    )

def create_reviewer_output(is_passing=True, scores=None):
    if scores is None:
        scores = {"age_appropriateness": 5, "correctness": 5, "clarity": 5, "coverage": 5}
    # Pass as 'is_passing' directly should work for keyword args, but the error said 'pass' field required.
    # Ah, I see: models.py has `is_passing: bool = Field(..., alias="pass")`.
    # When constructing a model with kwargs, Pydantic uses the field name. 
    # But if input_type=dict in error, maybe I should use model_validate?
    return ReviewerOutput(
        scores=scores,
        **{"pass": is_passing}, # Use alias to be safe with dict-like init
        feedback=[] if is_passing else [{"field": "explanation.text", "issue": "Too complex"}]
    )

# --- Test Cases ---

@pytest.mark.asyncio
async def test_schema_validation_failure_and_recovery():
    """Test 1: Schema validation fails once, then succeeds on retry."""
    orchestrator = Orchestrator()
    orchestrator.generator.use_mock = False
    
    mock_response_invalid = MagicMock()
    mock_response_invalid.text = "INVALID JSON"
    
    valid_data = create_valid_generator_output().model_dump()
    mock_response_valid = MagicMock()
    mock_response_valid.text = json.dumps(valid_data)
    
    with patch.object(orchestrator.generator.model, 'generate_content') as mock_gen:
        # First call fails validation, second succeeds
        mock_gen.side_effect = [mock_response_invalid, mock_response_valid]
        
        # Also mock reviewer to pass immediately
        with patch.object(orchestrator.reviewer, 'review', return_value=create_reviewer_output(True)):
            with patch.object(orchestrator.tagger, 'tag', return_value=create_valid_tagger_output()):
                result = await orchestrator.run_pipeline(5, "Test Topic")
                
                assert len(result.attempts) == 2 # 1 failed gen + 1 success gen
                assert result.attempts[0].validation_error is not None
                assert result.attempts[1].draft is not None
                assert result.final.status == "approved"

@pytest.mark.asyncio
async def test_fail_then_pass_after_refinement():
    """Test 2: Content fails review once, then passes after one refinement."""
    orchestrator = Orchestrator()
    orchestrator.generator.use_mock = False
    orchestrator.refiner.use_mock = False
    
    # Mock initial generation
    valid_content = create_valid_generator_output()
    with patch.object(orchestrator.generator, 'generate', return_value=(valid_content, None)):
        # Mock reviewer: first Fail, then Pass
        with patch.object(orchestrator.reviewer, 'review') as mock_review:
            mock_review.side_effect = [
                create_reviewer_output(False), # First review fails
                create_reviewer_output(True)   # Second review (after refinement) passes
            ]
            
            # Mock refiner
            refined_content = create_valid_generator_output()
            with patch.object(orchestrator.refiner, 'refine', return_value=refined_content):
                with patch.object(orchestrator.tagger, 'tag', return_value=create_valid_tagger_output()):
                    result = await orchestrator.run_pipeline(5, "Test Topic")
                    
                    assert result.final.status == "approved"
                    # Attempts: 1 (Gen) -> 1 (Refine) = 2 attempts in artifact
                    assert len(result.attempts) == 2
                    assert result.attempts[0].review.is_passing == False
                    assert result.attempts[1].review.is_passing == True

@pytest.mark.asyncio
async def test_fail_after_max_refinements():
    """Test 3: Content fails review even after maximum (2) refinements."""
    orchestrator = Orchestrator()
    orchestrator.generator.use_mock = False
    orchestrator.refiner.use_mock = False
    
    with patch.object(orchestrator.generator, 'generate', return_value=(create_valid_generator_output(), None)):
        # Always return a failing review
        with patch.object(orchestrator.reviewer, 'review', return_value=create_reviewer_output(False)):
            with patch.object(orchestrator.refiner, 'refine', return_value=create_valid_generator_output()):
                result = await orchestrator.run_pipeline(5, "Test Topic")
                
                assert result.final.status == "rejected"
                # Initial + 2 Refinements = 3 total attempts
                assert len(result.attempts) == 3
                for attempt in result.attempts:
                    assert attempt.review.is_passing == False

if __name__ == "__main__":
    # If run directly without pytest
    asyncio.run(test_schema_validation_failure_and_recovery())
    asyncio.run(test_fail_then_pass_after_refinement())
    asyncio.run(test_fail_after_max_refinements())
    print("\n[ALL TESTS PASSED MANUALLY]")
