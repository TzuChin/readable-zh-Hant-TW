# Proofreading

When the user says 「校稿」「幫我改這份文件」「把文件改好讀」「去 AI 味」 and provides a file or passage:

1. Read the whole thing first, and identify the parts that must not be changed: code blocks, commands, paths, URLs, version numbers, numbers and units, quoted original text, proper nouns.
2. Execute `python3 -I scripts/check_style.py <file>` with your shell tool; don't just read the script (the script path is relative to the skill folder). Everything under `[hard]` must be fixed; judge `[soft]` items in context. Run it again after editing; `[hard]` must be 0. Where scripts can't run, check each row of the "Avoid" table by hand instead.
3. Revise paragraph by paragraph according to "Writing style". Only change sentences that have a problem; if one sentence can be fixed, don't rewrite the whole paragraph. Move the conclusion to the top; make headings state the content (write 「部署前要關掉排程」, not 「注意事項」).
4. Don't change facts, numbers, conclusions, the order of steps, or warnings and limitations. Don't add experience, sources, numbers, or examples that weren't in the original. Where the original is uncertain, keep it uncertain after editing too. Missing information (such as no stated duration) stays as is in the sentence, flag it for the author to fill in when you report back.
5. Report how many places were changed and what kinds of issues they were, with 2 to 3 before/after examples. For anything deliberately left unchanged, state the reason in one sentence.
