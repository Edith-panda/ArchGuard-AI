# Structured Engineering Answer UI — Test Matrix

## Prompt gating
- `Ask ArchGuard` is disabled while the prompt is blank.
- Files/images are optional context; they do not enable submission by themselves.
- Entering a prompt enables the action.

## DESIGN
Ask: `Design an e-commerce platform for 10M users`.
Expected: formatted executive assessment. Existing backend DESIGN text remains visible. Structured component cards require structured architecture in the response (planned backend enhancement).

## REVIEW
Attach architecture JSON/YAML and ask: `Review this architecture and tell me what should change first.`
Expected: component cards, detected connections, risk/recommendation cards, Well-Architected score when available, and Digital Twin graph.

## SIMULATE
With architecture context ask: `What happens if the database goes down?`
Expected: structured architecture context plus the scenario explanation. Scenario-specific structured presentation can be expanded when the backend returns richer scenario fields.

## Images
Use `Attach files / image` and select a supported PNG/JPG/WebP architecture diagram. The existing FileDropZone + ingestion pipeline handles supported image attachments; a natural-language prompt is still required.

## Stakeholder change
Ask: `Stakeholders expect 20x traffic. What should change?`
Expected: MODIFY routing and formatted explanation. Generating a new structured post-change Digital Twin is intentionally not claimed by this UI PR; that remains a backend evolution-engine task.
