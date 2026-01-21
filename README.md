# Semi-Automated Evidence Extraction and Synthesis for Epidemiological Research

## Overview

This project implements a **semi-automated, schema-driven application** designed to assist epidemiologists in extracting structured data from scientific articles for systematic reviews and meta-analyses.

The tool focuses on **transparency, traceability, and human validation**, addressing key limitations of fully automated AI-based extraction systems in evidence-based research.

---

## Motivation

Systematic reviews and meta-analyses require manual extraction of study characteristics, effect estimates, and methodological details from multiple PDF articles. This process is:

* Time-consuming
* Prone to inconsistencies
* Difficult to audit and reproduce

While recent advances in natural language processing (NLP) enable automated text extraction, many existing tools lack:

* Explicit linkage between extracted values and source text
* Confidence assessment
* Opportunities for human review and correction

This project aims to bridge that gap by combining modern NLP techniques with **epidemiology-aware system design**.

---

## Key Features

* **PDF ingestion and scientific text parsing**
* **Schema-driven data extraction** for meta-analysis
* **Human-in-the-loop validation interface**
* **Source-linked extracted values** with confidence indicators
* **Meta-analysis–ready data export** (CSV / Excel / JSON)
* **Structured article summaries**
* **Exploratory cross-article thematic synthesis**

---

## Core Design Principles

* **Semi-automation over full automation**
  Human oversight is central to the workflow.

* **Schema-first extraction**
  Users define *what* to extract before extraction begins.

* **Full traceability**
  Every extracted value is linked to its source text and document section.

* **Reproducibility and transparency**
  Outputs are auditable and suitable for scientific use.

---

## System Workflow

1. **Upload PDFs**
   Scientific articles in PDF format are ingested.

2. **Document Parsing**
   Text is extracted and structured by section (Abstract, Methods, Results, Tables).

3. **Schema-Driven Extraction**
   A user-defined schema guides the extraction of specific variables (e.g. sample size, effect size, confidence intervals).

4. **Human Validation**
   Users review, edit, and confirm extracted values with highlighted source text.

5. **Data Export**
   Clean datasets are exported for downstream meta-analysis.

6. **Summarization & Synthesis** *(optional)*
   Structured summaries and cross-article comparisons are generated.

---

## Example Extraction Schema

```json
{
  "study_design": "string",
  "sample_size": "integer",
  "population": "string",
  "effect_measure": "OR | RR | HR",
  "effect_value": "float",
  "ci_lower": "float",
  "ci_upper": "float"
}
```

Each extracted field includes:

* Extracted value
* Source quotation
* Section reference
* Confidence score

---

## Technical Stack

* **Backend:** Python, FastAPI
* **NLP / ML:** Large Language Models, embeddings for similarity analysis
* **Data Storage:** SQLite or PostgreSQL
* **Frontend:** Streamlit (interactive review interface)
* **Deployment:** Docker

---

## Evaluation Strategy

The system is evaluated based on:

* Accuracy compared to manual data extraction
* Completeness of extracted schemas
* Transparency and traceability of outputs
* Usability and time savings for users

---

## Use Cases

* Systematic reviews
* Meta-analyses
* Rapid evidence synthesis
* Methodological comparison across studies

---

## Limitations

* The tool does **not** replace expert judgment.
* Extraction quality depends on PDF quality and reporting clarity.
* Cross-article synthesis is exploratory and not inferential.

---

## Future Work

* PRISMA-compliant workflows
* Citation manager integration
* Fine-tuned extraction models for specific study designs
* Collaboration features for team-based reviews

---

## Project Status

This project is under active development and is intended as a **research-focused portfolio project** at the intersection of epidemiology, statistics, and machine learning.

---

## Disclaimer

This tool is designed to **assist** researchers and does not replace methodological expertise or critical appraisal. All extracted outputs should be reviewed before use in scientific work.
