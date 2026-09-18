# Question design

Rules for extracting key concepts and key words, writing stems, and sourcing
distractors. Terms used here are defined in the repo CONTEXT.md: key
concept, key word, one-answer-many-questions, property question, word
question, mixed question generation, distractor.

## Key concepts

A key concept is an idea that rewards being recognized from multiple
situations. Signals: the text defines it, explains its cause or mechanism,
gives examples of it, contrasts it with something, or uses it to account for
other material. One-off proper nouns, dates, and decorative details are not
key concepts. Extract fewer concepts from thin text rather than inflating.

Key words are a separate pool with their own section below; extract both
pools independently and never substitute one for the other.

## Stem angles

Write every stem from one of these angles. Do not reuse an angle within one
concept's questions.

- Definition and property: what it is.
- Cause and mechanism: why it happens.
- Comparison and classification: what it is versus sibling categories.
- Numbers and units: magnitudes, thresholds, rates.
- Steps and sequence: orderings, before and after.
- Application and scenario: a concrete situation that reveals the concept.
- Exception and boundary: where it fails, edge conditions. Use only when the
  text actually supports an edge; narrative text often has none.

## Leakage ban

The correct answer's content must never appear in the stem. What that
constrains depends on the question type:

- Scenario questions: the answer is the concept word, so the stem must not
  contain the concept word, its synonyms, or wording that gives it away.
- Property questions: the answer is a statement, so its key wording must not
  appear in the stem.
- Word questions: the answer is a pronunciation or meaning, so the stem must
  not reveal it; the target word itself must appear in the stem, quoted from
  the text.

## Scenario questions

Two per key concept. The correct answer is always the concept word itself;
the stems are different situations that all point to that same concept. This
is the one-answer-many-questions pattern: the same concept is reached
repeatedly through varied contexts, which strengthens recognition.

- Vary the situation type across a concept's pair: one everyday scene plus
  one analytical framing beats two near-identical setups.
- Scenario stems may be synthesized. A synthesized stem wraps the concept in
  common-knowledge, everyday material. It must not assert specialized facts
  absent from the text, and must not contradict the text.
- Stems follow the leakage ban.
- Example (concept: 熱脹冷縮): stem "夏日午後，鐵軌接縫處互相擠壓而彎曲變形，
  這是哪一種現象？" — answer 熱脹冷縮; stem "金屬球加熱後卡在原本能穿過的
  金屬環中，可用哪個概念解釋？" — answer 熱脹冷縮. Same answer, different
  situations, neither stem contains the answer word.

## Property questions

At most one per key concept, and only when the text supports a cause,
mechanism, or property statement. The correct answer is that statement, not
the concept word. Stems follow the leakage ban.

- Example: stem "熱脹冷縮的微觀原因是什麼？" — correct answer "溫度升高使
  分子間距變大", not the concept word itself.

## Word questions

Key words form a separate pool from key concepts. A key word is a word worth
testing for pronunciation or meaning: difficult or rare words, words the
text's imagery leans on, polyphones (破音字) whose reading depends on
context, and domain terms. Not every noun qualifies; extract fewer from thin
text rather than inflating.

- One question per key word by default; add a second only when the word has
  another testable facet, such as usage, part of speech, or a confusing
  reading in context.
- The stem quotes the original sentence containing the word and names the
  target word, then asks for 音讀與意義 or 意義 alone.
  Example: 「撒了滿天的珍珠」的「撒」，音讀與意義？
- The correct answer combines reading and sense, e.g. "ㄙㄚˇ，散布、散放".
  Use the script the language standardly uses for readings: Zhuyin for
  Mandarin, pinyin or IPA elsewhere.
- Pronunciation and standard dictionary senses of words present in the text
  count as text-supported language facts, not outside content.

## Distractor hierarchy

Fill the three distractor slots in order. A distractor must be something a
learner who just read the text could plausibly pick.

1. **In-text confusables**: sibling concepts in the same category or word
   family as the correct answer. For 熱脹冷縮: 熱對流、熱傳導、熱輻射.
2. **Classic confusions**: well-known commonly confused knowledge or
   misconceptions for this topic, even when absent from the text. For
   熱脹冷縮: 熱熔化（heat melting solids）.
3. **Transforms of the correct answer**: swapped subject, reversed cause,
   changed scope, unit, or order. For concept words, word-shape transforms:
   reversed order (冷脹熱縮), near-spelling variants.

Word questions fill their slots on two battlefields, same tiers applied:

- Pronunciation battlefield: the word's other readings (破音字 variants),
  tone or reading variants, readings of visually similar characters.
- Meaning battlefield: other senses of the same character, confusable
  near-synonym words (倒、拋、丟 against 撒), common misreadings of the
  sense.

Never use filler: unrelated facts, joke options, obviously wrong picks. If
tiers 1–2 cannot fill all three slots, complete the set with tier 3.

Rotate distractor sets across the questions of the same concept, so the
repeated correct answer never appears alongside the same three options.

## Self-check

Before writing the CSV, verify every question. Fix or drop failures.

- Stem passes the leakage ban: the correct answer's content never appears in
  the stem.
- Exactly one option is defensibly correct, and the source text states or
  clearly entails it.
- Every distractor passes the plausibility test: a reader of the text could
  pick it.
- No two questions for one concept or key word reuse a stem angle or the
  same distractor set.
