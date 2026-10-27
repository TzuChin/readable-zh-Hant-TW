# When the user says 「看不懂」

When the user says 「蛤」「看不懂」「看無」「沒看懂」「什麼意思」「你是說」「wait what」, asks the same question again, or invokes /readable-zh-hant-tw again in a conversation where it's already in effect (including when it's applied globally), restate the previous passage:

1. The first sentence is the main point itself, for example 「使用者被登出，是因為 axios interceptor 收到 401 沒有重試」. Don't open with what went wrong last time. After that, say in one or two sentences what wasn't clear before (usually too long, too dense, or the key point buried).
2. Rewrite according to "Writing style". Keep every term, number, component, and approach mentioned in the original passage, even ones that seem unimportant, only change the phrasing and order. Don't add content that wasn't there originally. Restore any omitted subjects and conjunctions.
3. If the sticking point is terminology, put a comparison table after the first paragraph, at most five rows: term, what it means here, the corresponding name in code.

If the passage was about a task handed over from another session or a forwarded brief, open the restatement with a line starting 「需求：」 that says in one sentence what is being done now and why.

The third time this is triggered on the same topic, the restatements aren't working: make it much shorter. Use a numbered list, one point per line, and drop background and explanations. If the user asked several questions, answer them one by one, one line per question. Facts the user needs to act on still stay.
