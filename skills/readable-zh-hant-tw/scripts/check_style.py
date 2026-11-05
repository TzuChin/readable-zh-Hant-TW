#!/usr/bin/env python3
"""readable-zh-hant-tw 裡能用程式數的規則。

用法：python3 -I check_style.py FILE [--json]
      也可以 import 後呼叫 check(text) -> dict

分兩級：
  hard  幾乎不會誤判，只有 hard 會讓檢查失敗：簡體字、破折號、中文旁邊的半形標點（, : ; ? !）、中文和半形英數字之間沒空格、箭頭、「不是 X 而是 Y」（含並非、與其說…不如說）、
        中國用語、黑話、討好語、填充句、自己發明的口語（那一顆）、開頭兩句就在預告（以下是、下面是…）、
        「看不到…，下面是通用做法」這種前提接預告（出現在哪一句都算）、
        第一句就在講自己的限制（我沒有 X 的存取權、看不到你的程式碼）、最後一段在提議幫忙（需要的話我可以…、有問題歡迎再問）
  soft  只報告、不擋：空殼詞、AI 高頻詞、句子超過 40 字、一段超過 6 句、emoji、粗體過多、粗體標籤清單（連續三項時改算 hard）、
        沒有出處的歸因、空泛結尾與誇大、段落中間的宣告句、出貨、最後一段可能在提議幫忙（要不要我、我可以幫你、我再幫你）
        （拿真實 transcript 量過，句長一類會擋下七成回合，誤判太多，只給人工或 eval 參考）

不檢查：code fence、inline code、「」與“”裡的引文、> 開頭的引用、URL、路徑、markdown 表格列、標題。
計字：中文一字算一；一段連續的英數字（含路徑、指令）算一。
"""
import json
import os
import re
import sys

MAX_SENT = 40
MAX_PARA_SENT = 6
MAX_BOLD = 6

# 簡體字：只收繁簡不同、而且台灣的文章裡不會出現的字形
SIMP = set(
    "这个们为么没来对说时间会发还过现从问题应该实际开关门数据库设选择语结错误测试执运环变参处请输显隐"
    "启动删创编辑复读写备记录检确认获响连断网络页图视频软统调优质账权验码邮电话号历区县东头脑体术业专"
    "办农汉书长风马鸟鱼龙贝车让给样种点线两组织节单态状内当证译压缩载传协议异锁导则规标简带继续终见观"
    "觉决论学习爱机识够块层离闭换转递归尽虽仅将极众务护适积计带钟饭饮买卖经济产员门闻亚欧"
)

# 中國用語（繁體字形）
PRC_HARD = ["視頻", "軟件", "信息", "默認", "兼容", "屏幕", "文件夾", "質量", "渠道",
            "網絡", "內存", "硬盤", "打印", "鼠標", "服務器", "字符", "激活", "牛逼", "搞定了",
            "密鑰", "隊列", "緩存", "線程", "字符串", "數組", "端口", "存儲", "註銷", "中間件", "鏈接", "縮進",
            "嵌套", "分佈式", "用戶名", "死機", "縮略圖", "界面"]
PRC_SOFT = ["優化", "數據", "智能", "調用", "代碼",   # 「錯誤代碼」「事件代碼」在台灣是正常用法；「項目」在「子項目」裡是正常用法，不收
            "字節", "文檔",   # 會誤抓「文字節點」「明文檔案」
            "函數", "導出", "添加", "交互", "刷新", "源碼", "組件", "禁用", "重命名", "父進程", "文件名",
            "擴展", "聲明", "運行", "批量", "截取", "性能", "溢出", "持久性", "默認值"]
# OpenCC 的台灣詞彙表（TWPhrases.txt，Apache-2.0，授權在 TWPhrases.LICENSE）。上面兩份以外的詞：
# 三個字以上算 hard，兩個字算 soft（兩個字容易跟前後文湊錯，例如「明顯卡頓」裡的「顯卡」）。
# 2026-10 用 3,228 則台灣使用者自己寫的訊息量過：有人用過的詞放進 PRC_SKIP，不檢查。
PRC_SKIP = set("保存 像素 優先級 全局 分區 前綴 參數 在線 外鍵 字體 對話框 導入 引導程序 拋出 接口 文件 映射 查找 查看 "
               "權限 狀態欄 登錄 發佈 發送 算法 綁定 網卡 腳本 自行車 視圖 設備 設置 調度 連接 重裝 重載 鏡像 項目 類型 顯存 "
               "點擊 實時 免提 顯卡 任務欄 算子 命名空間 窗口".split())
PRC_TW = {}   # 中國用語 → 台灣用語，報告時附在後面
try:
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "TWPhrases.txt"), encoding="utf-8") as _f:
        for _line in _f:
            _k, _, _v = _line.rstrip("\n").partition("\t")
            if _v and not _line.startswith("#") and _k not in _v.split() and _k not in PRC_SKIP:
                PRC_TW[_k] = _v.split()[0]
except OSError:
    pass
PRC_TW["死機"] = "當機"   # OpenCC 給「宕機」，台灣一般說「當機」
_listed = set(PRC_HARD) | set(PRC_SOFT)
PRC_HARD += [k for k in PRC_TW if k not in _listed and len(k) >= 3]
PRC_SOFT += [k for k in PRC_TW if k not in _listed and len(k) == 2]

JARGON = ["賦能", "閉環", "抓手", "底層邏輯"]
FLATTER = ["好問題", "希望這對你有幫助", "希望這對您有幫助", "如有其他問題", "歡迎隨時", "很高興能"]
# 「你說得對」多半出現在被糾正後承認錯誤，不收
FILLER = ["值得注意的是", "這件事的本質是", "在當今快速發展的", "綜上所述", "總的來說"]

HOLLOW = ["進行", "相關", "層面", "基於", "針對", "透過", "其實", "基本上"]   # 「部分」誤判太多，不收
AI_WORDS = ["此外", "至關重要", "深入探討", "彰顯", "凸顯", "不可或缺", "無縫", "根本性", "結構性"]
ODD_SLANG = ["那一顆", "這一顆", "一顆 instance", "一顆 server", "一顆伺服器", "一顆機器"]
ODD_SOFT = ["出貨"]
# 晶晶體：有常用中文說法的英文詞夾在中文句子裡（只報告，不擋）
CHINGLISH = re.compile(r"[\u4e00-\u9fff]\s*(?:sync|case|confirm|check|follow|share|update|meeting|make sense|cover|handle|support|part|"
                       r"focus|schedule|plan)\s*(?:一下|[\u4e00-\u9fff])", re.I)
VAGUE = ["專家認為", "業界普遍", "一般來說", "眾所周知", "研究顯示"]          # 沒有出處的歸因
# 「我看不到你的程式碼，下面是通用做法」：前提接預告，出現在哪一句都算
NO_DATA_ANNOUNCE = re.compile(r"(?:看不到|沒看到|讀不到|沒有看到|找不到|沒找到|沒有找到|手上沒有|手邊沒有|工作目錄是空的)[^。\n]{0,40}?(?:下面|以下)(?:是|講|列出|整理|先)"
                              r"|(?:下面|以下)是通用")
# 第一句就在講自己的限制（「我沒有 X 的存取權」「看不到你的程式碼」），答案被擠到後面：規則 1 要先給答案，限制放在後面
LIMIT_FIRST = re.compile(r"^(?:(?:我這邊|我|這邊)[^。！？\n]{0,14}?(?:沒有|無法|沒辦法|不能)[^。！？\n]{0,16}?(?:存取|權限|讀取|讀到|連到|連線|看到|跑指令|執行指令)"
                         r"|(?:我)?(?:看不到|讀不到|沒看到)(?:你的|你們的|這台|那台|你貼的)"
                         # 「目前工作目錄裡沒有週報頁面的程式碼」「找不到相關程式碼」「這邊沒看到你們 staging 的設定檔」（2026-10 v27、v28 評分回覆）
                         r"|(?:目前|這個|這邊|我這邊)?[^。！？\n]{0,8}?(?:工作目錄|環境|目錄|專案|資料夾)[^。！？\n]{0,10}?(?:沒有|找不到|沒找到|沒有找到|沒看到|沒有看到|看不到)"
                         r"|(?:目前|這邊|我這邊)?(?:找不到|沒找到|沒有找到|沒看到|沒有看到)[^。！？\n]{0,16}?(?:程式碼|專案|檔案|設定檔|repo)"
                         # 「我沒看到週報頁面的程式碼」「我沒有這台 server 的設定或監控資料」（v42；評分回覆量過：抓到 24、誤擋 0）
                         r"|(?:我|我這邊)(?:沒有|找不到|沒找到|沒有找到|沒看到|沒有看到|看不到)[^。！？\n]{0,16}?(?:程式碼|專案|檔案|設定|資料|repo|log))")
OPENING_ANNOUNCE = re.compile(r"(?:^|[。！？])\s*(以下是|以下為|以下整理|下面整理|下面是|下面列出|我來說明|我來解釋|接下來介紹|接下來說明)")
# 第一句就用「如下」預告：「摘要如下：」「做法分別如下」。只看第一句，而且「如下」前面在 20 字以內：
# 第一句先給答案、第二句才說「摘要如下」，或長句子句尾才接「如下」，評審都判通過（2026-10 用 873 則評分回覆量過）
FIRST_AS_FOLLOWS = re.compile(r"如下(?:[：:，,]|\s*$)")
ANNOUNCE = re.compile(r"(?:^|[。！？，：\n])\s*(以下是|以下為|以下整理|下面整理|下面是|下面列出|我來說明|我來解釋|接下來介紹|接下來說明)")
# 最後一段在提議幫忙。2026-10 用 1,349 則評分回覆對照評審判定量過：
# hard 這組抓到評審判失敗的 187 則裡的 12 則，誤擋 1 則；soft 這組多抓 39 則，但誤擋 50 則，
# 誤擋的多半是「把結果貼給我，我再幫你判斷」這種具體下一步，或「要不要我順手改掉？」這種請使用者決定的問題
OFFER_HARD = re.compile(r"需要的話[，,]?\s*我|如果(你)?(還)?(需要|想要?|有需要|有興趣)[^。\n]{0,40}(我(可以|再|能|來|就)|告訴我|跟我說)"
                        r"|有(任何)?(其他)?(問題|疑問)(再|歡迎|隨時)|歡迎(隨時|再)|隨時(告訴|跟)我|再深入嗎|進一步[^。\n]{0,20}嗎[？?]"
                        # 邀請再問：「想深入哪一塊…都可以再問」「直接問我」（1,620 則評分回覆裡抓到 3 則，誤擋 0 則）
                        r"|都可以(再)?問|可以再問|再問我|直接問我|隨時問我")
BOLD_LABEL_LIST = re.compile(r"(?:^[ \t]*(?:[-*+]|\d+[.)])[ \t]+\*\*[^*\n]+\*\*[^。\n]*。?[ \t]*\n){3}", re.M)
OFFER_SOFT = re.compile(r"要不要我|我可以(直接)?(再)?(幫你|替你|給你|協助)|我再(幫你|給你)")
HOLLOW_END = ["未來可期", "奠定了堅實基礎", "奠定基礎", "重要的一步", "邁出了", "越來越好", "不懈追求", "標誌著"]     # 電商、物流的 repo 裡是正常用語，只報告

CODE_FENCE = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`\n]*`")
QUOTED = re.compile(r"「[^」\n]*」|“[^”\n]*”")
BLOCKQUOTE = re.compile(r"^[ \t]*>.*$", re.M)
# 只認 ASCII：Python 的 \w 也會比對中文字，路徑後面緊接的中文會被一起吃掉
PATH = re.compile(r"(?:~|\.{1,2})?/[A-Za-z0-9_.@~+-]+(?:/[A-Za-z0-9_.@~+-]+)+|(?<![A-Za-z0-9_.-])[A-Za-z0-9_.-]+\.(?:py|ts|tsx|js|jsx|md|json|ya?ml|toml|sh|go|rs|java|kt|swift|sql|html|css)(?::\d+)?(?![A-Za-z0-9_])")
URL = re.compile(r"https?://\S+")
HEADING_OR_TABLE = re.compile(r"^[ \t]*(#{1,6}\s.*|\|.*)$", re.M)
LIST_MARK = re.compile(r"^[ \t]*(?:[-*+]\s+|\d+[.)]\s+)", re.M)
BOLD = re.compile(r"\*\*[^*\n]+\*\*")
EMOJI = re.compile(r"[\U0001F300-\U0001FAFF☀-➿⭐✅❌]")
CJK = re.compile(r"[一-鿿]")
NO_SPACE = re.compile(r"[一-鿿][A-Za-z0-9#@&+=$]|[A-Za-z0-9#@&+=$%][一-鿿]")


def keep_lines(m):
    """刪掉內容但留下換行，行號才會跟原檔對得上。"""
    return "\n" * m.group(0).count("\n")


def strip_frontmatter(text):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return "\n" * text[:end + 4].count("\n") + text[end + 4:]
    return text


def clean(text):
    text = strip_frontmatter(text)
    text = CODE_FENCE.sub(keep_lines, text)
    text = INLINE_CODE.sub("X", text)       # 識別字算一個字
    text = URL.sub("X", text)
    text = PATH.sub("X", text)
    text = BLOCKQUOTE.sub("", text)
    text = QUOTED.sub("「」", text)
    text = HEADING_OR_TABLE.sub("", text)
    text = re.sub(r"<!--.*?-->", keep_lines, text, flags=re.S)
    return text


def lines_of(text, needle):
    return [text.count("\n", 0, m.start()) + 1 for m in re.finditer(re.escape(needle), text)]


def sentences(block):
    parts = re.split(r"(?<=[。！？；])", block)
    return [p.strip() for p in parts if p.strip()]


def sent_len(s):
    """中文一字算一、英文一個單字算一。"""
    cjk = len(CJK.findall(s))
    latin = len(re.findall(r"[A-Za-z0-9_][\w./:@~+-]*", s))
    return cjk + latin


def check(raw):
    text = clean(raw)
    with_headings = INLINE_CODE.sub("X", CODE_FENCE.sub(keep_lines, strip_frontmatter(raw)))
    hard, soft = {}, {}

    def hits(words, pool):
        for w in words:
            for ln in lines_of(text, w):
                pool.setdefault(w, []).append(ln)

    # 中國用語：長的詞先比對，比對到的位置蓋掉，「字符串」就不會再算一次「字符」
    prc_text, prc = text, {}
    for w in sorted(set(PRC_HARD) | set(PRC_SOFT), key=len, reverse=True):
        if w in prc_text:
            prc[w] = lines_of(prc_text, w)
            prc_text = prc_text.replace(w, "\u3000" * len(w))

    def prc_hits(words, pool):
        for w in words:
            if w in prc:
                pool[f"{w}（改{PRC_TW[w]}）" if w in PRC_TW else w] = prc[w]

    # hard
    simp = [(text.count("\n", 0, i) + 1, ch) for i, ch in enumerate(text) if ch in SIMP]
    if simp:
        hard["簡體字"] = simp[:8]
    dash = lines_of(text, "—")
    if dash:
        hard["破折號"] = dash[:8]
    # 中文字緊接半形 , : ; ? !，或半形標點後面緊接中文字。標題也算，程式碼、引用、表格不算
    heads = re.sub(r"(?m)^(?!#).*$", "", with_headings)
    halfwidth = sorted({pool.count("\n", 0, m.start()) + 1
                        for pool in (text, heads)
                        for m in re.finditer(r"(?<=[\u4e00-\u9fff])[,:;?!]|[,:;?!](?=[\u4e00-\u9fff])", pool)})
    if halfwidth:
        hard["半形標點"] = halfwidth[:8]
    # 中文和半形英數字、符號緊貼（「2天」「IG貼文」「`npm`安裝」）：要空一格。行內程式碼、路徑、網址在 clean() 裡換成 X，一樣算。
    # 全形標點旁邊不用空。2026-10 量過評分回覆：1.5% 的回覆有這種寫法，抽看都是真的沒空格
    nospace = [text.count("\n", 0, m.start()) + 1 for m in NO_SPACE.finditer(text)]
    if nospace:
        hard["中文和半形字之間沒空格"] = nospace[:8]
    # 選單路徑（Settings → CI/CD）與數字變化（165 → 5 秒、④→⑤）可以用：箭頭兩邊都不是中文字才放過
    arrows = [text.count("\n", 0, m.start()) + 1
              for m in re.finditer(r"(\S?)\s*→\s*(\S?)", text)
              if CJK.match(m.group(1) or "") or CJK.match(m.group(2) or "")]
    if arrows:
        hard["箭頭"] = arrows[:8]
    nx = [text.count("\n", 0, m.start()) + 1
          for m in re.finditer(r"(?:不(?:是|僅|僅僅|只|只是|單是)|並非|並不是)[^。\n]{1,30}?而是|與其說[^。\n]{1,30}?不如說", text)]
    if nx:
        hard["不是X而是Y"] = nx[:8]
    yonghu = [text.count("\n", 0, m.start()) + 1 for m in re.finditer(r"用戶(?![端名])", text)]
    if yonghu:
        hard.setdefault("中國用語", {})["用戶"] = yonghu
    # 開頭兩句就在預告「以下是…」「下面是…」：規則 1 的反例，回覆與文件都不該這樣開頭
    head = " ".join(sentences(LIST_MARK.sub("", text).strip().replace("\n", " "))[:2])
    if OPENING_ANNOUNCE.search(head) or "工作目錄是空的" in head:
        hard["開頭預告"] = [1]
    first = (sentences(LIST_MARK.sub("", text).strip().replace("\n", " ")) or [""])[0]
    fa = FIRST_AS_FOLLOWS.search(first.strip())
    if fa and sent_len(first.strip()[:fa.start()]) <= 20:   # 長句子裡先給了答案、句尾才接「如下」的不算
        hard["開頭預告"] = [1]
    if LIMIT_FIRST.search(first.strip()):
        hard["開頭先講限制"] = [1]
    nda = [text.count("\n", 0, m.start()) + 1 for m in NO_DATA_ANNOUNCE.finditer(text)]
    if nda:
        hard["前提接預告"] = nda[:8]
    pool = hard.get("中國用語", {})
    prc_hits(PRC_HARD, pool)
    if pool:
        hard["中國用語"] = pool
    for label, words in [("黑話", JARGON), ("討好語", FLATTER), ("填充句", FILLER),
                         ("自己發明的口語", ODD_SLANG)]:
        pool = hard.get(label, {})
        hits(words, pool)
        if pool:
            hard[label] = pool

    paras = [x for x in re.split(r"\n\s*\n", text.strip()) if x.strip()]
    last = paras[-1] if paras else ""
    last_line = text.strip().count("\n") - last.strip().count("\n") + 1
    if OFFER_HARD.search(last):
        hard["結尾提議幫忙（刪掉提議的那句）"] = [last_line]

    # soft
    if last and "結尾提議幫忙（刪掉提議的那句）" not in hard and OFFER_SOFT.search(last):
        soft["結尾可能在提議幫忙"] = [last_line]
    pool = {}
    prc_hits(PRC_SOFT, pool)
    if pool:
        soft["中國用語（可議）"] = pool
    for label, words in [("空殼詞", HOLLOW), ("AI 高頻詞", AI_WORDS), ("口語（看情境）", ODD_SOFT), 
                         ("沒有出處的歸因", VAGUE), ("空泛結尾與誇大", HOLLOW_END)]:
        pool = {}
        hits(words, pool)
        if pool:
            soft[label] = pool
    chinglish = [text.count("\n", 0, m.start()) + 1 for m in CHINGLISH.finditer(text)]
    if chinglish:
        soft["晶晶體"] = chinglish[:8]
    announce = [text.count("\n", 0, m.start(1)) + 1 for m in ANNOUNCE.finditer(text)]
    if announce:
        soft["宣告句"] = announce[:8]
    emoji = [with_headings.count("\n", 0, m.start()) + 1 for m in EMOJI.finditer(with_headings)]
    if emoji:
        soft["emoji"] = emoji[:8]
    # 獨立一行的粗體是分段用的小標，不算
    bold = len(BOLD.findall(re.sub(r"(?m)^[ \t]*\*\*[^*\n]+\*\*[ \t]*$", "", text)))
    if bold > MAX_BOLD:
        soft["粗體過多"] = [bold]
    # 每項只有一句、開頭是粗體標籤的清單；項目有好幾句時，粗體標籤可以幫忙分界
    label_list = [text.count("\n", 0, m.start()) + 1
                  for m in re.finditer(r"^[ \t]*(?:[-*+]|\d+[.)])\s+\*\*[^*\n]{1,12}\*\*[^。\n]*。?[ \t]*$", text, re.M)]
    if len(label_list) >= 3:
        soft["粗體標籤清單"] = label_list[:8]
    # 連續三項「**標籤**＋一句」：跟評分題目的 no-bold-label-list 同一條規則，hard
    m = BOLD_LABEL_LIST.search(with_headings + "\n")
    if m:
        hard["粗體標籤清單"] = [with_headings.count("\n", 0, m.start()) + 1]
        soft.pop("粗體標籤清單", None)

    long_sents, long_paras = [], []
    body = LIST_MARK.sub("", text)
    for i, line in enumerate(body.split("\n"), 1):
        ss = sentences(line)
        if len(ss) > MAX_PARA_SENT:
            long_paras.append((i, len(ss)))
        for s in ss:
            n = sent_len(s)
            if n > MAX_SENT:
                long_sents.append((i, n, s[:24]))
    if long_sents:
        soft["句子超過40字"] = long_sents[:8]
    if long_paras:
        soft["一段超過6句"] = long_paras[:8]

    def count(pool):
        total = 0
        for v in pool.values():
            if isinstance(v, dict):
                total += sum(len(x) for x in v.values())
            else:
                total += len(v) if isinstance(v, list) else 1
        return total

    hard_n, soft_n = count(hard), count(soft)
    return {
        "hard": hard, "soft": soft,
        "hard_count": hard_n, "soft_count": soft_n,
        "fail": hard_n > 0,
        "has_cjk": bool(CJK.search(text)),
    }


def summary_line(report):
    parts = []
    for label, v in report["hard"].items():
        parts.append(f"{label} {len(v) if isinstance(v, list) else sum(len(x) for x in v.values())} 處"
                     + (f"（{'、'.join(list(v)[:4])}）" if isinstance(v, dict) else ""))
    for label, v in report["soft"].items():
        parts.append(f"{label} {len(v) if isinstance(v, list) else sum(len(x) for x in v.values())} 處"
                     + (f"（{'、'.join(list(v)[:4])}）" if isinstance(v, dict) else ""))
    return "；".join(parts)


def main():
    path = sys.argv[1]
    raw = open(path, encoding="utf-8").read()
    report = check(raw)
    if "--json" in sys.argv:
        print(json.dumps(report, ensure_ascii=False))
        return
    for tier in ("hard", "soft"):
        for label, v in report[tier].items():
            print(f"[{tier}] {label}: {v}")
    print(f"hard={report['hard_count']} soft={report['soft_count']} fail={report['fail']}")
    print(json.dumps({"file": path, "hard": report["hard_count"], "soft": report["soft_count"], "fail": report["fail"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
