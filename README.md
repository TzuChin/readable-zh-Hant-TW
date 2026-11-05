# readable-zh-Hant-TW

**讓 AI 先講結論，用台灣慣用的繁體中文把話寫清楚。**

回覆、寫文件、校稿都適用。句子寫完整，不寫「好問題！」「以下是…」這類 AI 常見的套話，也不寫讀的人要猜意思的口語。程式碼、指令、錯誤訊息照原樣保留。

## 安裝

```bash
npx skills add TzuChin/readable-zh-Hant-TW
```

支援 Claude Code、Codex、Gemini CLI、Antigravity、Grok Build、Cursor 等能裝 Agent Skills 的工具。

## 核心原則

1. 第一句就給答案或結果。
2. 用台灣的用字和說法。程式碼、指令、錯誤訊息和技術名詞照原樣不翻；其他有中文說法的就寫中文，不寫「我們 sync 一下這個 case」。
3. 同一個東西從頭到尾用同一個名稱。例如前面叫「訂單服務」，後面不會改叫 `OrderService` 或「下單模組」。
4. 不寫 AI 常見的寫法，例如「好問題！」、破折號、「不是 X 而是 Y」、「以下是…」。
5. 自己能做完的事直接做完，不丟回給你。
6. 回覆要短：一般問題 5 句、150 字內，不複述問題，不補沒被問的背景。

完整規則見 [SKILL.md](skills/readable-zh-hant-tw/SKILL.md)。

## 使用

有三種用法：

1. 自己叫出來：在對話裡輸入 `/readable-zh-hant-tw`（Codex 是 `$readable-zh-hant-tw`），這個對話接下來的回覆都會照規則寫。
2. 讓 AI 自己叫出來：直接說「幫我校稿 README.md」「去 AI 味」「看不懂」，AI 會自己載入這個 skill。
3. 套用到所有對話：只有 Claude Code 有，見下一段。

在 Claude Code 第一次輸入 `/readable-zh-hant-tw` 時，它會問你要不要**套用到所有對話**。選了之後，每個新對話都會自動照規則寫，寫進檔案的中文文件和 subagent 也一樣，不必每次輸入。改設定之前，它會先列出要改的地方給你確認，也會先備份。

要取消套用到所有對話，輸入 `/readable-zh-hant-tw 移除全域套用`。

## 自動檢查的 hook

全域套用時會一起裝一個 hook，在 Claude Code 裡自動跑 Python 程式。它只檢查 Claude 寫出來的中文，不會連網路，也不會刪檔或改設定：

文件檢查：Claude 寫完或改完 `.md`、`.mdx`、`.markdown`、`.txt` 這類有中文的檔案，就檢查整份檔案。抓到同樣的問題會附上行號請 Claude 修，不會擋住 Claude 繼續做事。

要關掉這個 hook，在 `~/.claude/settings.json` 加上這段，再開新的對話：

```json
{ "env": { "READABLE_ZH_HANT_TW_HOOK": "off" } }
```

大陸用語的對照用 [OpenCC](https://github.com/BYVoid/OpenCC) 的台灣詞彙表 `TWPhrases.txt`。台灣工程師也常用的詞（例如「文件」「參數」「腳本」）不檢查。

規則本身照樣生效，只是不再自動檢查。要連規則一起拿掉，輸入 `/readable-zh-hant-tw 移除全域套用`。

## claude.ai 網頁版

把 `skills/readable-zh-hant-tw` 這個資料夾壓成 zip，在 Settings 的 Capabilities 上傳。網頁版沒有全域套用和 hook，只會套用規則本身。

## 其他工具的全域套用

Codex、Gemini CLI、Antigravity 這類工具沒有 output style 和 hook。要讓規則在每個對話都生效，先產生一份規則檔：

```bash
python3 skills/readable-zh-hant-tw/scripts/install.py --print-agents > AGENTS.md
```

把 `AGENTS.md` 放在專案根目錄，或把內容貼進工具的全域規則檔（例如 `~/.gemini/GEMINI.md`）。內容跟 Claude Code 的全域套用一樣，只拿掉 hook 這類 Claude Code 才有的部分。

## 限制

- 自動檢查的 hook 只在 Claude Code 有，而且需要 Python 3。其他工具只會套用規則本身。
- 沒有全域套用時，不會自動檢查回覆和文件，subagent 也不會照規則寫。要連這些一起管，就選全域套用。

## 致謝

這份規則整理、翻譯並改寫自下面幾個 skill，再補上台灣用詞和中文寫作的規則。依取用的多寡排序：

| 來源 | 作者與授權 | 取用的部分 |
|---|---|---|
| [i-have-adhd-zh-tw](https://github.com/panda850819/i-have-adhd-zh-tw) | Panda Zeng 維護，MIT（i-have-adhd 的繁體中文版） | 這份規則的中文骨架：規則的分法和標題（先給答案、步驟有邊界、錯誤要具體…）、一律用繁體中文、台灣用詞清單、刪掉翻譯腔和空殼詞的例句、哪幾種情況才交給使用者處理、黑話與填充句的清單、「不是 X 而是 Y」和破折號的禁用、例外情況（破壞性操作先確認、失敗三次就停、真的有歧義才問）、送出前檢查；README 的寫法也參考了這個專案 |
| [i-have-adhd](https://github.com/ayghri/i-have-adhd) | Ayoub Ghriss，MIT | 讀者模型的五個事實（記不住畫面以外的東西、開始最難、對時間長短沒有感覺…），以及中文版沒有的幾條對話規則：每次回覆都講進度、時間寫成具體長度、讓成果看得見、先做完手上的事、結尾給一個兩分鐘內做得到的下一步、清單最多 5 項 |
| [Humanizer-zh-TW](https://github.com/kevintsai1202/Humanizer-zh-TW) | 歸藏，MIT。繁體化自 [op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh)，原作 [blader/humanizer](https://github.com/blader/humanizer)（Siqi Chen，MIT），參考 [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) 與維基百科 [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) | 寫作規則「Avoid」表格裡大約一半的項目：湊成三個一組、句尾加「凸顯了…」、用「作為」代替「是」、不能比的「從 X 到 Y」、金句、沒有出處的說法、宣傳用語、emoji、粗體標題清單、討好和空泛的結尾；校稿時不加入原文沒有的事實 |
| [wait-what](https://github.com/mattpocock/skills) | Matt Pocock，MIT | `references/re-pitch.md`（使用者說「看不懂」時重講）：先補上他缺的前因後果，用簡單的句子，照 repo 的術語用詞 |
| [caveman](https://github.com/JuliusBrussee/caveman) | Julius Brussee，Apache-2.0 | 寫作規則「When shortening, keep」一節的出發點：縮短時識別字和錯誤訊息照原樣；遇到安全警告、改不回來的操作，就改回完整的句子 |
| [OpenCC](https://github.com/BYVoid/OpenCC) | BYVoid，Apache-2.0（授權全文在 `scripts/TWPhrases.LICENSE`） | `scripts/TWPhrases.txt`：大陸用語對台灣用語的詞彙表，原檔照收，檢查程式用它抓大陸用語 |
| [ponytail](https://github.com/DietrichGebert/ponytail) | DietrichGebert，MIT | 規則 6（Say what's usable now）的一句：刻意沒做的事要寫出來，跳過了什麼、什麼時候要補 |

## 授權

MIT。來源 skill 的作者與授權見上表。
