# GimKit CSV format

GimKit imports question sets from a CSV uploaded via
New Kit → Import from Spreadsheet → Upload File. The multiple choice
template has exactly five columns. Produce files matching it.

```
Question,Correct Answer,Incorrect Answer 1,Incorrect Answer 2,Incorrect Answer 3
```

## Row rules

- Row one is the header exactly as spelled above. If an upload fails,
  re-download GimKit's template from the kit editor and match its headers
  before suspecting the content.
- One question per row. Four options, no more and no fewer: one correct
  answer in column 2, three distractors in columns 3–5. The template
  expresses single-correct questions only; no multi-select.
- Answer cells are plain text. The template does not carry images, equations,
  or audio, so questions must work as text alone.
- Do not number question text (`1.`, `Q1`); GimKit numbers its own display.
- Encoding: UTF-8 without byte-order mark. Write Chinese question text as-is.

## Escaping

- Quote a field with double quotes when it contains a comma, double quote, or
  newline.
- Double any double quote inside a quoted field.
- Prefer rewording over escaping: questions whose options need embedded
  commas usually read better split differently.

```
"Which statement about ""thermal expansion"" is correct?",Solids expand when heated,…
```

## What the file is not

- No kit title, subject, or metadata rows: kit name and info are entered in
  the GimKit UI during kit creation.
- No Quizlet export, no flashcard question-and-answer template: this skill
  produces the four-option multiple choice template only.
