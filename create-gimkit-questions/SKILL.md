---
name: create-gimkit-questions
description: Generate GimKit-importable multiple choice questions as a ready-to-upload CSV from provided text. Auto-extracts key concepts across the whole source (plus key words when the source is Chinese language material), builds one-answer-many-questions scenario sets and property questions covering every supported statement, and engineers plausible, confusable distractors only. Use when a user asks to turn text, notes, or documents into GimKit questions or a question CSV. Do not use for other quiz platforms, text-input or flashcard formats, or generic summaries with no question output.
---

# Create GimKit Questions

Turn the user's source material into single-correct multiple choice questions
that import cleanly into GimKit (New Kit → Import from Spreadsheet → Upload
File). Keep the source content accurate, test understanding rather than word
matching, never fill an answer slot with a throwaway option, and cover the
whole source: every statement the text supports is question material.

## Required context

Before extracting concepts or writing questions, read
[question design](references/question-design.md). Before writing the CSV
file, also read [CSV format](references/gimkit-csv-format.md).

Domain vocabulary lives in the repo CONTEXT.md under "GimKit 選擇題出題":
key concept, key word, one-answer-many-questions, property question, word
question, mixed question generation, distractor.

## Fidelity invariants

- Every correct answer must be fully supported by the source text. Skip
  material the text does not support; never pad the set to hit a count.
  Carve-out: word questions test linguistic facts about words the text
  contains — their standard pronunciation and dictionary senses count as
  supported.
- Claims that are vague or hedged in the text must not silently become facts
  in a question.
- Distractors may draw on well-known confusable knowledge outside the text,
  but correct answers may not.
- Every question has exactly four options, one of them correct. GimKit's
  spreadsheet template supports no other shape.

## Workflow

1. Identify the scope: the whole source or the part the user selects. Accept
   pasted text or a file path. Question language follows the source text.
2. Extract key concepts over the whole source, fact-dense passages included.
   Extract the key-word pool only when the source is Chinese language
   material (課文、散文、文言) or the user asks for word questions.
3. For each key concept, write scenario questions from distinct stem angles
   (at least two) and every property question the text supports for it.
   Distribute the total across concepts by richness: important, dense
   concepts carry more questions.
4. Source every distractor through the three-tier hierarchy in
   `question-design.md`. Tier 3 transforms are always available: no question
   ever ends up with filler options.
5. Run the self-check in `question-design.md`. Fix first; drop only what
   cannot be fixed. The check is a quality gate, never a way to shrink the
   set.
6. Write the CSV file and show every question in the conversation for review.
   If the user only asks to see a preview, show the questions without writing
   the file.

## Question count

No fixed cap. The only ceiling is what the source supports: a question fails
fidelity when unsupported, never for being too many. Per key concept keep at
least two scenario questions and add every supported property statement;
word questions follow their own section. When the user asks for a specific
count or "as many as possible", work up to that ceiling and spread the
questions across the whole source; if the material runs out, say so rather
than pad.

## Output location

Write the CSV next to the source file when the input is a file; otherwise
write it to the current working directory.

File naming: when the input is a file, use the original filename with a
`-gimkit` suffix, e.g. `ch3-notes.pdf` → `ch3-notes-gimkit.csv`. When the
input is pasted text with no filename, use a short slug of the topic, e.g.
`gimkit-heat-expansion.csv`.
