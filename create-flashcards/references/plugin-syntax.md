# Flashcards plugin v2 syntax

Read this reference before writing cards into notes. The forms below are for
authoring; identity metadata is added automatically by the plugin during
update.

## Choosing a card type

| Need | Suggested form |
| --- | --- |
| Short question and answer | Inline basic |
| Useful in both directions | Inline or fenced reversed |
| Recall of missing content in context | Cloze |
| Multi-section answer under one topic | Hashtag heading |
| Explicit, precise boundaries | Fenced card or card callout |
| A principle that should recur periodically | Reminder |
| A note deliberately expressing one concept | Atomic note |
| One claim worth asking in multiple ways | Atomic note, multiple `test:` entries |

## Inline cards

Basic:

```markdown
What is the capital of France?::Paris
```

Reversed:

```markdown
TCP:::Transmission Control Protocol
```

An inline card in a list item owns that item and its indented sub-block.
A sibling item at the same indentation level starts a separate card.

## Cloze cards

```markdown
The mitochondria is the ==powerhouse== of the cell.
The {1:heart} pumps blood through the {1:circulatory system}.
```

`==text==` uses automatic numbering. `{N:text}` uses explicit numbering.
Reuse the same `N` when multiple spans should be hidden together. Native
`{{cN::text}}` syntax is also supported.

Keep clozes inside a sentence or other context that points at the expected
answer. Never use clozes purely to delete arbitrary words from copied prose.

## Fenced cards

Basic or reversed:

````markdown
```flashcard
front: What does CSS stand for?
back: Cascading Style Sheets
type: reversed
```
````

`type` is optional and defaults to `basic`. Supported values are `basic`,
`reversed`, `cloze`, and `reminder`.

A cloze fence uses `front` as the Anki Text field and the optional `back` as
the Extra field. A reminder fence uses a single `content` field:

````markdown
```flashcard
type: reminder
content: Prefer reversible decisions when uncertainty is high.
```
````

## Hashtag cards

```markdown
## What is recursion? #card

A function that calls itself and has a base case.
```

Use `#card-reverse` or `#card/reverse` for reversed cards. The tag may sit on
its own line directly after the heading.

A heading card owns its full section. Lower-level headings stay inside the
answer. A heading at the same or higher level ends the answer.

A paragraph with `#card` uses the text in the same paragraph after the tag. If
nothing else is in the paragraph, the next top-level Markdown block is used.
Use a heading or an explicit container for longer answers.

## Reminder cards

```markdown
Keep the feedback loop short. #card-reminder
```

A reminder card has content but no answer. A reminder paragraph owns only that
paragraph. The v1 `#card-spaced` syntax is not supported.

## Card callouts

```markdown
> [!CARD] : What is recursion?
> A function that calls itself.
>
> It needs a base case.
```

A callout is an explicit container. Its title is the question and its body is
the answer.

## Atomic note cards

Use atomic syntax only when a note is deliberately written as a single card.
The answer is always the first paragraph of the body. Everything after the
first paragraph is ignored.

Write `test:` as a list of strings. A single bare scalar is also accepted and
normalized into a one-item list, but the list form is the convention: it keeps
the Obsidian properties panel consistent across notes.

```markdown
---
test:
  - Define recursion
---

A function that calls itself and has a base case.
```

Each entry produces one card. An entry is either a reserved keyword or a
question you write yourself:

| Entry | Question | Result |
| --- | --- | --- |
| `title` | The file name | Basic card |
| `reversed` | File name and first paragraph, both directions | One note, two cards |
| `cloze` | First paragraph with its `==spans==` hidden | Cloze card |
| Any other string | That string | Basic card |

Multiple entries can ask about one claim from different angles while sharing
one answer:

```markdown
---
test:
  - title
  - "Re-reading feels productive. What does it fail at?"
---
```

That note produces two cards sharing the same answer. Use multiple entries only
when the prompts target the *same* claim. If the prompts need different
answers, the note is not atomic: split it.

The following violations silently produce zero cards. Check before writing:

- Entries must be unique. Duplicate entries invalidate the whole `test:` key.
- A self-written question must not equal the file name or duplicate another
  entry's derived question. Both collide with the `title` card.
- `reversed` and `cloze` may each appear at most once.
- Nested maps or non-string entries are errors; never guess.

Two conditions are reported as warnings and leave the note untouched: a `test:`
key with no first paragraph, and a `cloze` entry whose first paragraph contains
no `==span==`.

A note without a `test:` key is not a card. For bridge notes, structure notes,
and any note whose value lies in its links, this is the correct default.

## Boundaries and precedence

An explicit card container owns its source span. Card-like text inside that
span is content, not another card.

Precedence, in order:

1. Atomic note cards, fenced cards, and card callouts.
2. Hashtag cards.
3. Inline list cards and their sub-blocks.
4. Inline reversed cards.
5. Inline basic cards.
6. Cloze cards.

Never place a second card inside a container. Close the first container before
starting the next card.

## Decks, tags, and context

To set a note's deck explicitly:

```yaml
---
cards-deck: Knowledge::Biology
tags:
  - biology
  - exam
---
```

Without `cards-deck`, folder-based decks are enabled by default. The final
fallback deck is `Default`. The default tag is `obsidian`. The parent heading
is the default context shown above the review question.

## Managed metadata

Do not write or edit these values:

- the `flashcards` frontmatter property;
- `^q-xxxx` anchors;
- legacy numeric anchors;
- Anki note IDs, source hashes, or sync hashes.

These are created and maintained by the plugin. Preserve existing values when
editing a note.

For the full set of edge cases, read `docs/wiki.md` in the repository.
