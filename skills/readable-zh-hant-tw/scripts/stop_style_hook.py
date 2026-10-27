#!/usr/bin/env python3
"""Claude Code Stop hook：機械檢查最後一則回覆，沒過就要 Claude 只重寫那一則。

settings.json：
{"hooks":{"Stop":[{"hooks":[{"type":"command",
  "command":"python3 -I ~/.claude/readable-zh-hant-tw/hooks/stop_style_hook.py","timeout":10}]}]}}

只在生效的 output style 是 readable-zh-hant-tw 時檢查（依序看 cwd/.claude/settings.local.json、
cwd/.claude/settings.json、~/.claude/settings.json 的 outputStyle）。
環境變數：
  READABLE_ZH_HANT_TW_HOOK=off        整個關掉
  READABLE_ZH_HANT_TW_HOOK_MODE=block | context
      block（預設）：印 {"decision":"block","reason":...}，畫面會顯示 hook 訊息
      context：印 hookSpecificOutput.additionalContext，一樣會續寫，但不顯示 hook 錯誤通知
stop_hook_active 為 true 時一律放行，所以一回合最多重寫一次，重寫的那一則不再檢查。
只看 check_style.py 的 hard 級規則（簡體字、破折號、箭頭等幾乎不會誤判的），
另外擋整則用英文寫的回覆（使用者最後一則訊息要求英文時放行）。
注意：被擋下的原回覆已經顯示在畫面上，修正版會接在後面，不會取代它。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_style  # noqa: E402

STYLE = "readable-zh-hant-tw"
MIN_CHARS = 30


def claude_dir():
    """測試時用 READABLE_ZH_HANT_TW_CLAUDE_DIR 指到別的目錄；也尊重 CLAUDE_CONFIG_DIR。"""
    d = os.environ.get("READABLE_ZH_HANT_TW_CLAUDE_DIR") or os.environ.get("CLAUDE_CONFIG_DIR")
    return os.path.expanduser(d) if d else os.path.expanduser("~/.claude")



def effective_output_style(cwd):
    candidates = [
        os.path.join(cwd or "", ".claude", "settings.local.json"),
        os.path.join(cwd or "", ".claude", "settings.json"),
        os.path.join(claude_dir(), "settings.json"),
    ]
    for p in candidates:
        try:
            with open(p, encoding="utf-8") as fh:
                v = json.load(fh).get("outputStyle")
            if v:
                return v
        except (OSError, ValueError):
            continue
    return None


def mostly_english(text):
    """拿掉程式碼與識別字後，英文單字比中文字多：整則回覆沒用中文寫。"""
    t = check_style.clean(text)
    words = len(re.findall(r"[A-Za-z]{2,}", t))
    if words < 15 or len(check_style.CJK.findall(t)) >= words:
        return False
    # 原文也要中文很少：整份包在 ```markdown 裡又有巢狀程式碼區塊時，clean() 會切錯位置
    raw = re.sub(r"「[^」]*」", "", text)
    return len(check_style.CJK.findall(raw)) < len(re.findall(r"[A-Za-z]{2,}", raw)) * 0.3


def user_wants_english(transcript_path):
    """使用者最後一則訊息要求用英文時放行。讀不到 transcript 就當作沒要求。"""
    try:
        with open(transcript_path, encoding="utf-8") as fh:
            lines = fh.readlines()[-200:]
    except (OSError, TypeError):
        return False
    for line in reversed(lines):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") != "user":
            continue
        content = (e.get("message") or {}).get("content")
        if isinstance(content, list):
            content = " ".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
        if content:
            return bool(re.search(r"英文|English", content, re.I))
    return False


def block(reason):
    mode = os.environ.get("READABLE_ZH_HANT_TW_HOOK_MODE", "block").lower()
    if mode == "context":
        out = {"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": reason}}
    else:
        out = {"decision": "block", "reason": reason}
    print(json.dumps(out, ensure_ascii=False))


def main():
    if os.environ.get("READABLE_ZH_HANT_TW_HOOK", "").lower() in ("off", "0", "false"):
        return
    try:
        d = json.load(sys.stdin)
    except ValueError:
        return
    if d.get("stop_hook_active"):
        return
    if effective_output_style(d.get("cwd")) != STYLE:
        return
    # 不退回去讀 transcript：文件說它可能還沒寫到這一回合，會拿舊訊息誤擋
    text = d.get("last_assistant_message") or ""
    if len(text.strip()) < MIN_CHARS:
        return
    if mostly_english(text) and not user_wants_english(d.get("transcript_path")):
        block("風格檢查沒過：回覆沒有用繁體中文。程式碼、指令、識別字照原樣，其他整則改用台灣繁體中文重寫，"
              "事實與結論不變，不加新內容，不重做已經做完的工作。")
        return
    report = check_style.check(text)
    if not report["has_cjk"] or not report["fail"]:
        return
    report["soft"] = {}
    detail = check_style.summary_line(report)
    block(f"風格檢查沒過：{detail}。只重寫剛才那一則回覆：修掉被點名的地方，"
          f"事實與結論不變，不加新內容，不重做已經做完的工作。")


if __name__ == "__main__":
    main()
