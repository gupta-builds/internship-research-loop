---
created: 2026-09-06
type: reference
tags: [internship-research-loop, resume, format-rules, example]
---

# Resume reference — rules and example, one file

Unlike the cover-letter side, this did not need fresh research — the Jarvis vault's `Resume Alteration Standard` §8 already carries real, cited (a)-tier rules, sourced 2026-08-29 from Greenhouse's and Ashby's own published documentation, plus Google's own resume-guidance video. This file cites that section directly and adds only what's specific to `.docx` generation, which the Standard itself doesn't cover.

## The rules, cited to `Resume Alteration Standard` §8

- **Layout**: single-column, no tables/text boxes/columns/sidebars/graphics — Greenhouse's own documented parse-failure list, not a style preference.
- **Section headings**: familiar labels only — Experience, Education, Skills (Summary/Objective optional).
- **Contact info**: in the document body, first page, never a header/footer.
- **Dates**: one consistent format throughout — no specific syntax is required anywhere in the sourced docs.
- **Fonts**: Arial, Calibri, Times New Roman, Garamond, or Helvetica, 10-12pt, one font throughout.
- **File**: PDF preferred, DOCX acceptable, under 2.5MB (Greenhouse's stricter ceiling) — trivial for a text-only file.
- **Length**: one page by default; two pages only where the target company's own guidance explicitly allows it for technical roles (Google's own video does). This generator warns, never blocks, past a one-page soft ceiling — the two-page call is the human's, per application.
- **Keywords**: no verified universal density rule exists — this generator does not check keyword density; that's `.cursor/skills/resume-alteration`'s content concern, not a format concern here.

## What's specific to `.docx` generation

- Section headings bold, one point size larger than body — matches `Main Resume.md`'s own real structure (`## Experience`, `### Role — Company, Dates`).
- Real Word bullet-list style (`List Bullet`) for every bullet, never a typed hyphen — this is what makes it parse as a list to both a human skimmer and most ATS parsers.
- Skills as one line per category (`*Category:* item, item, item`), single column, never a table.

## Example — fabricated, format only, never a content source

Same "Jordan Lee" persona as the cover-letter example, for consistency. Mirrors `Main Resume.md`'s own real section order exactly.

---

**Jordan Lee**
612-555-0143 · jordan.lee@example.edu · linkedin.com/in/jordanlee-example · github.com/jlee-example

**Education**
Pursuing a Bachelor of Science in Computer Science — Example State University. Expected Spring 2028.

**Skills**
*Programming:* Python, Rust, TypeScript, JavaScript
*AI & Data:* LLM APIs, RAG, embeddings, data pipelines
*Full Stack:* Next.js, React, REST APIs, backend logic

**Experience**

*Software Engineering Intern — Acme Robotics, June–August 2026*
- Built a real-time perception dashboard using Rust and a WebSocket event stream.
- Reduced pipeline stall detection time from minutes to seconds by adding structured observability tooling.

*Web Development Intern — Example Corp, June–August 2025*
- Built and deployed a production web application with Next.js, React, and a Strapi backend.

**Projects**
- **Second Brain Note Visualizer:** Added a computer-vision layer to an Obsidian vault to visualize idea connections.

**Certifications**
- **Generative AI** — Example Learning Platform, issued 2026.

---

Demonstrates: bold larger-size name → contact line → bold section headings (Education, Skills, Experience, Projects, Certifications, in that order; Objective optional between Education and Skills) → bold same-size sub-entry headers (role/company/dates, project names) → real bulleted lists under each entry → one-line-per-category Skills, single column throughout.
