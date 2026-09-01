# Structured Engineering Report UX

This branch changes ArchGuard's long conversational synthesis from a single text block into a structured engineering report.

The UI groups content into named sections, numbered cards, architecture blueprint code blocks, component inventory, deterministic risk cards, recommendations, assumptions, open questions and evidence-backed findings. The right-hand Blueprint panel renders the generated architecture diagram when no Digital Twin is available and falls back to the interactive Digital Twin when architecture evidence has been reconstructed.

The natural-language prompt is required to run `Ask ArchGuard`; architecture files and images are optional context that can be attached through the same composer.
