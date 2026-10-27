#!/usr/bin/env python3
"""Claude Code PostToolUse hook：Claude 用 Write / Edit 寫中文文件後，檢查整份檔案。
用 Bash 寫檔時（`>`、`>>`、`tee` 寫到文件檔），也檢查被寫的那幾個檔案。

settings.json：
{"hooks":{"PostToolUse":[{"matcher":"Write|Edit|MultiEdit|Bash","hooks":[{"type":"command",
  "command":"python3 -I ~/.claude/readable-zh-hant-tw/hooks/doc_check_hook.py","timeout":10}]}]}}

只看副檔名是 .md、.mdx、.markdown、.txt，而且內容有中文的檔案。
只回報 check_style.py 的 hard 級問題（附行號），用 additionalContext 交給 Claude 修，不擋下工具。
環境變數 READABLE_ZH_HANT_TW_HOOK=off 可以整個關掉。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_style  # noqa: E402


EXTS = (".md", ".mdx", ".markdown", ".txt")
# Bash 指令裡寫進文件檔的目標：cat > a.md、echo ... >> a.md、tee [-a] a.md
BASH_TARGET = re.compile(r"(?:>>?|\btee\b(?:\s+-a)?)\s*[\"']?([^\s\"'<>|;&]+\.(?:md|mdx|markdown|txt))\b")
SKIP_DIRS = ("/node_modules/", "/.git/", "/vendor/", "/dist/", "/build/")


def main():
    if os.environ.get("READABLE_ZH_HANT_TW_HOOK", "").lower() in ("off", "0", "false"):
        return
    try:
        d = json.load(sys.stdin)
    except ValueError:
        return
    tool_input = d.get("tool_input") or {}
    if d.get("tool_name") == "Bash":
        cwd = d.get("cwd") or os.getcwd()
        paths = [os.path.join(cwd, os.path.expanduser(m)) for m in BASH_TARGET.findall(tool_input.get("command", ""))]
    else:
        paths = [tool_input.get("file_path") or ""]
    msgs = [m for m in (report_for(p) for p in dict.fromkeys(paths)) if m]
    if msgs:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "\n".join(msgs)}},
                         ensure_ascii=False))


def report_for(path):
    """有 hard 級問題就回傳要給 Claude 的說明，沒有就回傳空字串。"""
    if not path.lower().endswith(EXTS) or any(s in path for s in SKIP_DIRS):
        return ""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError):
        return ""
    report = check_style.check(text)
    if not report["has_cjk"] or not report["fail"]:
        return ""
    parts = []
    for label, v in report["hard"].items():
        if isinstance(v, dict):
            where = "；".join(f"「{w}」第 {'、'.join(map(str, lns[:5]))} 行" for w, lns in list(v.items())[:4])
        else:
            lines = [x[0] if isinstance(x, tuple) else x for x in v]
            where = f"第 {'、'.join(map(str, lines[:6]))} 行"
        parts.append(f"{label}：{where}")
    return (f"{os.path.basename(path)} 有不符合 readable-zh-hant-tw 寫法的地方：" + "。".join(parts)
            + "。請只修這些地方，內容與識別字不變。引用的原文、程式碼區塊不用改。")


if __name__ == "__main__":
    main()
