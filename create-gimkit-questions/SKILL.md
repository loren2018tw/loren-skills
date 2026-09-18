---
name: create-gimkit-questions
description: Generate GimKit-importable multiple choice questions as a ready-to-upload CSV from provided text. Auto-extracts key concepts from the source material, builds one-answer-many-questions scenario sets plus property questions, and engineers plausible, confusable distractors only. Use when a user asks to turn text, notes, or documents into GimKit questions or a question CSV. Do not use for other quiz platforms, text-input or flashcard formats, or generic summaries with no question output.
---

# Create GimKit Questions

Turn the user's source material into single-correct multiple choice questions
that import cleanly into GimKit (New Kit → Import from Spreadsheet → Upload
File). Keep the source content accurate, test understanding rather than word
matching, and never fill an answer slot with a throwaway option.

## Required context

Before extracting concepts or writing questions, read
[question design](references/question-design.md). Before writing the CSV
file, also read [CSV format](references/gimkit-csv-format.md).

Domain vocabulary lives in the repo CONTEXT.md under "GimKit 選擇題出題":
key concept, one-answer-many-questions, property question, mixed question
generation, distractor.

## Fidelity invariants

- Every correct answer must be fully supported by the source text. Skip
  material the text does not support; never pad the set to hit a count.
- Claims that are vague or hedged in the text must not silently become facts
  in a question.
- Distractors may draw on well-known confusable knowledge outside the text,
  but correct answers may not.
- Every question has exactly four options, one of them correct. GimKit's
  spreadsheet template supports no other shape.

## Workflow

1. Identify the scope: the whole source or the part the user selects. Accept
   pasted text or a file path. Question language follows the source text.
2. Extract the key concepts: durable ideas worth repeated retrieval. If the
   text is thin, produce fewer concepts; do not inflate.
3. For each key concept, write two scenario questions whose correct answer is
   the concept itself, from two different stem angles. If and only if the
   text supports a cause, mechanism, or property statement for the concept,
   add at most one property question whose correct answer is that statement.
4. Source every distractor through the three-tier hierarchy in
   `question-design.md`. Tier 3 transforms are always available: no question
   ever ends up with filler options.
5. Run the self-check in `question-design.md`. Fix or drop failing questions.
6. Write the CSV file and show every question in the conversation for review.
   If the user only asks to see a preview, show the questions without writing
   the file.

## Question count

Total = two scenario questions per key concept plus optional property
questions, bounded to 5–30. When the user requests a specific count,
distribute extra questions across concepts evenly, keeping each question
within the design rules; if the material runs out, say so rather than pad.

## Output location

Write the CSV next to the source file when the input is a file; otherwise
write it to the current working directory.

File naming: when the input is a file, use the original filename with a
`-gimkit` suffix, e.g. `ch3-notes.pdf` → `ch3-notes-gimkit.csv`. When the
input is pasted text with no filename, use a short slug of the topic, e.g.
`gimkit-heat-expansion.csv`.
