# BOQ AUTO Agent Instructions

This repository is a construction estimating platform for BOQs and tender workflows.

Main subsystems:
- BOQ pricing engine
- quotations/commercial layer
- rate-library ingestion
- review and learning workflow
- tender analysis and BOQ drafting

Rules for agents:
- Modify existing modules in place
- Do not create disconnected parallel pipelines
- Preserve CLI coherence
- Prefer review-first workflows
- Reuse config, logging, models, and workbook output patterns
- Keep outputs practical for QS and estimating teams