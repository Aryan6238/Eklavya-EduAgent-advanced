const runBtn = document.getElementById('runBtn');
const topicInput = document.getElementById('topicInput');
const gradeInput = document.getElementById('gradeInput');
const visualizer = document.getElementById('visualizer');
const finalResult = document.getElementById('final-result');
const finalContentArea = document.getElementById('finalContentArea');
const tagArea = document.getElementById('tagArea');
const historyList = document.getElementById('historyList');

/**
 * Initiates the pipeline execution
 */
async function runPipeline() {
    const topic = topicInput.value.trim();
    const grade = gradeInput.value;

    if (!topic) {
        return;
    }

    // Reset UI to Loading State
    visualizer.innerHTML = `
        <div style="text-align: center; padding: 60px; animation: pulse 2s infinite">
            <i class="ph-bold ph-gear-six" style="font-size: 3rem; margin-bottom: 20px; display: block"></i>
            <p style="font-weight: 500; letter-spacing: 0.1em">ORCHESTRATING MULTI-AGENT LIFECYCLE...</p>
        </div>
    `;
    finalResult.classList.add('hidden');

    try {
        const response = await fetch('/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ grade: parseInt(grade), topic })
        });

        const artifact = await response.json();
        renderPipeline(artifact);
    } catch (error) {
        console.error(error);
        visualizer.innerHTML = `
            <div class='attempt-card' style="border-color: var(--error)">
                <span class="step-label" style="color: var(--error)">ERROR</span>
                <h3>Pipeline Interrupted</h3>
                <p style="color: var(--text-secondary)">${error.message || "A system-level error occurred. Please check server logs."}</p>
            </div>
        `;
    }
}

/**
 * Renders the pipeline audit trace with staggered animations
 */
function renderPipeline(artifact) {
    visualizer.innerHTML = '';

    // Defensive check: ensure attempts array exists
    if (!artifact || !artifact.attempts || !Array.isArray(artifact.attempts)) {
        visualizer.innerHTML = `
            <div class='attempt-card' style="border-color: var(--error)">
                <span class="step-label" style="color: var(--error)">ERROR</span>
                <h3>Invalid Pipeline Response</h3>
                <p style="color: var(--text-secondary)">The server returned malformed data. Please check server logs.</p>
            </div>
        `;
        return;
    }

    artifact.attempts.forEach((attempt, index) => {
        const card = document.createElement('div');
        card.className = 'attempt-card';
        card.style.animationDelay = `${index * 0.3}s`; // Stagger effect

        const isPass = attempt.review ? attempt.review.pass : false;
        const statusClass = attempt.review ? (isPass ? 'success' : 'error') : '';
        const statusText = attempt.review ? (isPass ? 'PASS' : 'FAIL') : 'PROCESSING';

        card.innerHTML = `
            <span class="step-label">CYCLE ${attempt.attempt} • ${new Date(attempt.timestamp).toLocaleTimeString()}</span>
            <div class="card-header">
                <h3>Draft Generation & Audit</h3>
                <div class="score-pills">
                    <span class="pill ${statusClass}">${statusText}</span>
                </div>
            </div>
            
            ${attempt.review ? `
            <div style="display: flex; gap: 8px; margin-bottom: 20px;">
                <span class="pill">Age: ${attempt.review.scores.age_appropriateness}/5</span>
                <span class="pill">Fact: ${attempt.review.scores.correctness}/5</span>
                <span class="pill">Clear: ${attempt.review.scores.clarity}/5</span>
                <span class="pill">Cover: ${attempt.review.scores.coverage}/5</span>
            </div>
            ` : '<div style="margin-bottom: 20px; color: var(--accent-cyan); font-size: 0.8rem">Pending Review...</div>'}

            <div class="content-display">
                <p style="line-height: 1.6; color: var(--text-secondary)">
                    ${attempt.draft.explanation.text}
                </p>
            </div>

            ${attempt.review && !isPass ? `
                <div class="feedback-area">
                    <div style="font-weight: 700; margin-bottom: 8px; color: var(--accent-pink)">
                        <i class="ph ph-warning-circle"></i> QA FEEDBACK
                    </div>
                    <ul style="margin: 0; padding-left: 20px;">
                        ${attempt.review.feedback.map(f => `<li><b>${f.field}:</b> ${f.issue}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
        `;

        visualizer.appendChild(card);
    });

    if (artifact.final.status === 'approved') {
        renderFinalArtifact(artifact);
    } else if (artifact.final.status === 'rejected') {
        renderRejection(artifact);
    }

    loadHistory();
}

/**
 * Renders the success state
 */
function renderFinalArtifact(artifact) {
    const { content, tags } = artifact.final;

    document.getElementById('artifactTopic').innerText = artifact.input.topic;
    document.getElementById('artifactMeta').innerText = `Educational Standard: Grade ${content.explanation.grade} • ID: ${artifact.run_id.slice(0, 8)}`;

    finalContentArea.innerHTML = `
        <div style="margin-bottom: 32px">
            <h4 style="color: var(--primary); margin-bottom: 12px">CURATED EXPLANATION</h4>
            <p style="font-size: 1.1rem; line-height: 1.7">${content.explanation.text}</p>
        </div>
        
        <div style="margin-bottom: 32px; padding: 20px; background: rgba(var(--primary-rgb), 0.05); border-left: 4px solid var(--primary); border-radius: 4px;">
            <h4 style="color: var(--primary); margin-bottom: 8px"><i class="ph ph-chalkboard-teacher"></i> TEACHER NOTES</h4>
            <p style="font-weight: 500; margin-bottom: 12px"><b>Objective:</b> ${content.teacher_notes.learning_objective}</p>
            <div style="font-size: 0.9rem; color: var(--text-secondary)">
                <p style="margin-bottom: 4px; font-weight: 600">Common Misconceptions:</p>
                <ul style="margin: 0; padding-left: 20px;">
                    ${content.teacher_notes.common_misconceptions.map(m => `<li>${m}</li>`).join('')}
                </ul>
            </div>
        </div>

        <hr style="border: none; border-top: 1px solid var(--border-light); margin: 32px 0">
        <div>
            <h4 style="color: var(--primary); margin-bottom: 12px">ASSESSMENT ITEMS</h4>
            ${content.mcqs.map((m, i) => `
                <div style="margin-bottom: 24px">
                    <p style="font-weight: 600; margin-bottom: 8px">${i + 1}. ${m.question}</p>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                        ${m.options.map(o => `<div style="padding: 10px; background: rgba(255,255,255,0.03); border-radius: 8px; font-size: 0.9rem">${o}</div>`).join('')}
                    </div>
                </div>
            `).join('')}
        </div>
    `;

    tagArea.innerHTML = `
        <div style="display: flex; gap: 12px; flex-wrap: wrap">
            <span class="pill" style="border-color: var(--primary)">Difficulty: ${tags.difficulty}</span>
            <span class="pill" style="border-color: var(--primary)">Taxonomy: ${tags.blooms_level}</span>
            <span class="pill" style="border-color: var(--primary)">Domain: ${tags.subject}</span>
        </div>
    `;

    finalResult.classList.remove('hidden');
    // Smooth scroll to results
    finalResult.scrollIntoView({ behavior: 'smooth' });
}

/**
 * Renders the rejection state
 */
function renderRejection(artifact) {
    document.getElementById('artifactTopic').innerText = artifact.input.topic;
    document.getElementById('artifactMeta').innerText = `Governance Audit • ID: ${artifact.run_id.slice(0, 8)}`;

    finalContentArea.innerHTML = `
        <div style="text-align: center; padding: 40px;">
            <i class="ph ph-x-circle" style="font-size: 4rem; color: var(--error); margin-bottom: 24px; display: block"></i>
            <h3 style="color: var(--error)">GOVERNANCE REJECTION</h3>
            <p style="color: var(--text-secondary)">This content failed to meet the required quality standards (Scores < 4) after maximum refinements.</p>
            <p style="font-size: 0.8rem; margin-top: 10px; color: var(--text-dim)">The AI was unable to produce authentic pedagogical material for this topic within the safety bounds.</p>
        </div>
    `;
    tagArea.innerHTML = '';
    finalResult.classList.remove('hidden');
}

/**
 * Loads history from backend
 */
async function loadHistory() {
    try {
        const response = await fetch('/history');
        const history = await response.json();

        historyList.innerHTML = history.map(h => `
            <div class="history-item">
                <span class="topic">${h.input.topic}</span>
                <div class="meta">
                    <span>G${h.input.grade}</span>
                    <span style="color: ${h.final.status === 'approved' ? 'var(--success)' : 'var(--error)'}">
                        ${h.final.status === 'approved' ? 'PASS' : 'REJECTED'}
                    </span>
                </div>
            </div>
        `).join('');
    } catch (e) {
        console.error(e);
    }
}

// Event Listeners
runBtn.addEventListener('click', runPipeline);
loadHistory();
