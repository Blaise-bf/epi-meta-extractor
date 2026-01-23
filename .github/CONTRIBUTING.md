# Contributing Guidelines

Thank you for your interest in contributing to this project.
This repository is designed as a **research-grade, semi-automated tool** to support epidemiological evidence extraction and synthesis.

All contributions should prioritize **transparency, traceability, and methodological rigor**.

---

## Guiding Principles

* **Human-in-the-loop over full automation**
  This tool assists epidemiologists; it does not replace expert judgment.

* **Schema-driven design**
  All extraction logic must be guided by explicit schemas.

* **Auditability and provenance**
  Extracted data must always be traceable to source text.

* **Reproducibility**
  Changes should be deterministic, documented, and testable.

---

## How to Contribute

### 1. Open or Select an Issue

All work should be linked to a GitHub issue.

* Use the provided **issue template**
* Clearly define acceptance criteria
* Assign the issue to yourself if appropriate

---

### 2. Branching Strategy

Create a feature branch from `main`:

```bash
git checkout -b feature/short-description
```

Examples:

* `feature/schema-definition`
* `feature/pdf-ingestion`
* `fix/extraction-confidence-bug`

---

### 3. Development Expectations

* Follow the project directory structure
* Keep commits small and meaningful
* Avoid introducing unnecessary dependencies
* Document assumptions and limitations explicitly

---

### 4. Pull Request Process

Before opening a pull request:

* Ensure the related issue acceptance criteria are met
* Run tests where applicable
* Update documentation if behavior changes

All pull requests must:

* Use the provided **Pull Request template**
* Reference the related issue(s)
* Clearly describe design decisions

---

## Issue and PR Style

This project follows a **user-story-driven workflow**:

**As a** [role]
**I need** [function]
**So that** [benefit]

Acceptance criteria should be written in **Gherkin-style** where applicable.

---

## Code of Conduct

This project follows standard open-source conduct guidelines:

* Be respectful
* Assume good faith
* Prioritize scientific integrity

---

## Disclaimer

This tool is intended to **support research workflows only**.
All outputs must be reviewed by qualified researchers before use in scientific or clinical decision-making.
