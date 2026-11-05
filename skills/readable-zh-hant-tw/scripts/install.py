#!/usr/bin/env python3
"""把 readable-zh-hant-tw 設成 Claude Code 的全域預設。這支 script 跟 skill 放在一起，從 skill 資料夾執行。

用法：
  python3 install.py --status       看目前有沒有全域套用
  python3 install.py                全域套用（可加 --dry-run 只看會改什麼、--no-hooks 不裝 hook、--print 只印出組好的規則）
  python3 install.py --uninstall    移除全域套用，outputStyle 還原成套用前的值
  python3 install.py --print-agents 印出給其他工具（AGENTS.md、GEMINI.md）的全域規則，內容跟 Claude Code 的全域套用一樣

全域套用會做這些事（每一項都可以用 --uninstall 還原）：
  1. ~/.claude/output-styles/readable-zh-hant-tw.md   對話回覆的規則（output style）
  2. ~/.claude/readable-zh-hant-tw/core.md            共用的寫法規則，~/.claude/CLAUDE.md 用 @ 匯入。
                                                 subagent 和寫文件時也讀得到
  3. ~/.claude/readable-zh-hant-tw/hooks/             PostToolUse hook 檢查寫進檔案的中文文件
  4. ~/.claude/settings.json                     outputStyle、hooks、skillOverrides（全域套用後，
                                                 這個 skill 不再讓模型自己叫出來，免得規則重複）
改動前的檔案備份在 ~/.claude/backups/readable-zh-hant-tw/<時間>/。
"""
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

NAME = "readable-zh-hant-tw"
SKILL_DIR = Path(__file__).resolve().parent.parent
HOME = Path.home()
# 測試時用 READABLE_ZH_HANT_TW_CLAUDE_DIR 指到別的目錄；也尊重 CLAUDE_CONFIG_DIR
CLAUDE = Path(os.path.expanduser(os.environ.get("READABLE_ZH_HANT_TW_CLAUDE_DIR") or os.environ.get("CLAUDE_CONFIG_DIR")
                                 or "~/.claude"))
BASE = CLAUDE / NAME
STYLE_DST = CLAUDE / "output-styles" / f"{NAME}.md"
CLAUDE_MD = CLAUDE / "CLAUDE.md"
SETTINGS = CLAUDE / "settings.json"
MANIFEST = BASE / "install.json"
BLOCK_START, BLOCK_END = f"<!-- {NAME} -->", f"<!-- /{NAME} -->"
CORE_REF = f"~/.claude/{NAME}/core.md" if CLAUDE == HOME / ".claude" else f"{CLAUDE}/{NAME}/core.md"
IMPORT_BLOCK = f"{BLOCK_START}\n@{CORE_REF}\n{BLOCK_END}\n"
HOOK_FILES = ("check_style.py", "doc_check_hook.py", "TWPhrases.txt", "TWPhrases.LICENSE")
OLD_NAME = "readable-zh-tw"   # 改名前的名稱，裝新版時連同它的全域套用一起移除
LEGACY = (CLAUDE / "hooks" / NAME, CLAUDE / "skills" / f"{NAME}-doc",   # 舊版裝過的位置
          CLAUDE / OLD_NAME, CLAUDE / "output-styles" / f"{OLD_NAME}.md", CLAUDE / "hooks" / OLD_NAME,
          CLAUDE / "skills" / OLD_NAME, CLAUDE / "skills" / f"{OLD_NAME}-doc")

DRY = "--dry-run" in sys.argv
BACKUP = CLAUDE / "backups" / NAME / time.strftime("%Y%m%d-%H%M%S")


def say(msg):
    print(("[dry-run] " if DRY else "") + msg)


def backup(p: Path):
    if not p.exists():
        return
    dest = BACKUP / (p.relative_to(HOME) if p.is_relative_to(HOME) else p.relative_to(p.anchor))
    if DRY:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if p.is_dir():
        shutil.copytree(p, dest, symlinks=True, dirs_exist_ok=True)
    else:
        shutil.copy2(p, dest)


def load_settings():
    if not SETTINGS.exists():
        return {}
    return json.loads(SETTINGS.read_text(encoding="utf-8"))


def save_settings(data):
    backup(SETTINGS)
    if not DRY:
        SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def strip_our_hooks(data):
    """拿掉 settings.json 裡所有指到這個 skill 的 hook，包括舊版路徑和改名前的名稱。"""
    hooks = data.get("hooks") or {}
    for event in list(hooks):
        kept = []
        for entry in hooks[event]:
            hs = [h for h in entry.get("hooks", []) if not any(n in h.get("command", "") for n in (NAME, OLD_NAME))]
            if hs:
                kept.append({**entry, "hooks": hs})
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]
    if "hooks" in data and not data["hooks"]:
        del data["hooks"]


def sections(path: Path):
    """把 markdown 依 `## ` 標題切開，回傳 (開頭, {標題: 整段})。"""
    text = path.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        text = text[text.index("\n---\n", 4) + 5:]
    parts = re.split(r"(?m)^(?=## )", text.strip() + "\n")
    return parts[0], {p.splitlines()[0][3:].strip(): p for p in parts[1:]}


def as_section(path: Path, **replace):
    """references 裡的檔案，第一行 `# ` 降成 `## `，當成一段接進去。"""
    text = "#" + path.read_text(encoding="utf-8").lstrip()
    for old, new in replace.items():
        text = text.replace(old, new)
    return text.rstrip() + "\n\n"


def build_rules():
    """從 SKILL.md 和 references 組出全域套用用的 output style 和 core.md，規則只維護 SKILL.md 一份。

    core.md（CLAUDE.md 匯入，subagent 和寫文件也讀得到）：開頭、Language、Scope、Writing style、校稿。
    output style（主對話）：讀者怎麼讀、Rules、看不懂時重講、When to relax、送出前檢查。
    assets/global-extras.md 只在全域套用時用到：全域不受 skill 的 5,000 token 上限，放回完整的讀者描述和檢查清單。
    """
    head, sec = sections(SKILL_DIR / "SKILL.md")
    head = "\n\n".join(p for p in head.split("\n\n") if not p.startswith("First action"))   # 只跟叫出 skill 有關
    refs = SKILL_DIR / "references"
    _, extras = sections(SKILL_DIR / "assets" / "global-extras.md")   # 只給全域套用，SKILL.md 放不下
    check = f"{BASE}/hooks/check_style.py" if CLAUDE != HOME / ".claude" else f"~/.claude/{NAME}/hooks/check_style.py"
    core = (f"<!-- {NAME} 全域套用時由 install.py 產生，改規則請改 skill 的 SKILL.md -->\n\n" + head.strip() + "\n\n"
            + sec["Language: always respond in Traditional Chinese"] + sec["Scope"] + sec["Writing style"]
            + as_section(refs / "proofread.md", **{"Execute `python3 -I scripts/check_style.py <file>` with your shell tool; don't just read the script (the script path is relative to the skill folder)": f"Run `python3 -I {check} <file>`"}))
    style = ("---\n"
             f"name: {NAME}\n"
             "description: 用台灣慣用的繁體中文回覆：先講結論、每次回覆都講進度、不寫 AI 套話。\n"
             "keep-coding-instructions: true\n"
             "---\n\n"
             "# Readable Taiwanese Chinese: conversation rules\n\n"
             "Language, scope, and writing style are in the readable-zh-hant-tw core that CLAUDE.md imports. "
             "Follow both; this file adds the rules for replies in conversation.\n\n"
             + extras["How the reader reads"] + sec["Rules"] + as_section(refs / "re-pitch.md") + sec["When to relax"]
             + extras["Checklist before sending"])
    return style.rstrip() + "\n", core.rstrip() + "\n"


def build_agents_rules():
    """給 Claude Code 以外的工具（AGENTS.md、GEMINI.md 這類一直生效的規則檔）用的全域規則。
    內容跟 build_rules() 一樣，拿掉只有 Claude Code 才有的部分：output style 的 frontmatter 和開頭說明、
    hook 的那句，校稿時跑檢查程式的路徑改回 skill 資料夾裡的相對路徑。"""
    style, core = build_rules()
    style = style[style.index("\n---\n", 4) + 5:].lstrip()
    style = re.sub(r"^# Readable Taiwanese Chinese: conversation rules\n\n[^\n]*\n\n", "## Conversation rules\n\n", style)
    style = re.sub(r"\n*If a hook reports 「風格檢查沒過」[^\n]*", "", style)
    core = re.sub(r"^<!--.*?-->\n\n", "", core, flags=re.S)
    core = re.sub(r"Run `python3 -I [^`]*check_style\.py <file>`",
                  "If this skill's `scripts/check_style.py` is available, run `python3 -I <skill folder>/scripts/check_style.py <file>`", core)
    return core.rstrip() + "\n\n" + style.rstrip() + "\n"


def status():
    data = load_settings()
    style_on = data.get("outputStyle") == NAME and STYLE_DST.exists()
    md_on = CLAUDE_MD.exists() and BLOCK_START in CLAUDE_MD.read_text(encoding="utf-8")
    hooks = json.dumps(data.get("hooks", {}))
    print(json.dumps({
        "installed": style_on and md_on,
        "output_style": style_on,
        "claude_md_import": md_on,
        "doc_hook": "doc_check_hook.py" in hooks,
    }, ensure_ascii=False))


def remove_legacy(data):
    """移除改名前（readable-zh-tw）的全域套用：CLAUDE.md 匯入段、skillOverrides、舊資料夾和檔案。
    settings.json 的舊 hook 由 strip_our_hooks 拿掉，outputStyle 由呼叫的人處理。"""
    (data.get("skillOverrides") or {}).pop(OLD_NAME, None)
    if "skillOverrides" in data and not data["skillOverrides"]:
        del data["skillOverrides"]
    text = CLAUDE_MD.read_text(encoding="utf-8") if CLAUDE_MD.exists() else ""
    start, end = f"<!-- {OLD_NAME} -->", f"<!-- /{OLD_NAME} -->"
    if start in text and end in text:
        say(f"從 {CLAUDE_MD} 移除改名前的匯入段")
        backup(CLAUDE_MD)
        i, j = text.index(start), text.index(end) + len(end)
        rest = (text[:i].rstrip() + "\n" + text[j:].lstrip("\n")).strip()
        if not DRY:
            CLAUDE_MD.write_text(rest + "\n", encoding="utf-8") if rest else CLAUDE_MD.unlink()
    for old in LEGACY:
        if old.exists() or old.is_symlink():
            say(f"移除舊版 {old}")
            backup(old)
            if not DRY:
                old.unlink() if old.is_symlink() or old.is_file() else shutil.rmtree(old)


def old_previous_style():
    """改名前那次安裝記下的「套用前的 outputStyle」。"""
    m = CLAUDE / OLD_NAME / "install.json"
    return json.loads(m.read_text(encoding="utf-8")).get("previous_output_style") if m.exists() else None


def install():
    style, core = build_rules()
    data = load_settings()
    prev_style = data.get("outputStyle")
    if prev_style == OLD_NAME:
        prev_style = old_previous_style()
    if MANIFEST.exists():
        prev_style = json.loads(MANIFEST.read_text(encoding="utf-8")).get("previous_output_style", prev_style)

    say(f"寫入 {STYLE_DST}")
    backup(STYLE_DST)
    if not DRY:
        STYLE_DST.parent.mkdir(parents=True, exist_ok=True)
        STYLE_DST.write_text(style, encoding="utf-8")

    say(f"寫入 {BASE}/core.md 與 hooks/")
    if not DRY:
        (BASE / "hooks").mkdir(parents=True, exist_ok=True)
        (BASE / "core.md").write_text(core, encoding="utf-8")
        for f in HOOK_FILES:
            shutil.copy2(SKILL_DIR / "scripts" / f, BASE / "hooks" / f)

    text = CLAUDE_MD.read_text(encoding="utf-8") if CLAUDE_MD.exists() else ""
    if BLOCK_START not in text:
        say(f"在 {CLAUDE_MD} 加上匯入 core.md 的一段")
        backup(CLAUDE_MD)
        if not DRY:
            CLAUDE_MD.write_text((text.rstrip() + "\n\n" if text.strip() else "") + IMPORT_BLOCK, encoding="utf-8")

    data["outputStyle"] = NAME
    strip_our_hooks(data)
    if "--no-hooks" not in sys.argv:
        hooks = data.setdefault("hooks", {})
        hooks.setdefault("PostToolUse", []).append({"matcher": "Write|Edit|MultiEdit|Bash", "hooks": [{
            "type": "command", "command": f"python3 -I {BASE}/hooks/doc_check_hook.py", "timeout": 10}]})
    data.setdefault("skillOverrides", {})[NAME] = "user-invocable-only"
    say(f"更新 {SETTINGS}：outputStyle、hooks、skillOverrides")
    save_settings(data)

    remove_legacy(data)
    save_settings(data)

    if not DRY:
        MANIFEST.write_text(json.dumps({"previous_output_style": prev_style, "installed_at": time.strftime("%F %T")},
                                       ensure_ascii=False, indent=2), encoding="utf-8")
    say(f"完成。備份在 {BACKUP}。開一個新的 Claude Code session 才會套用新的 output style。")


def uninstall():
    data = load_settings()
    prev = None
    if MANIFEST.exists():
        prev = json.loads(MANIFEST.read_text(encoding="utf-8")).get("previous_output_style")
    if data.get("outputStyle") == OLD_NAME:
        prev = prev or old_previous_style()
        data["outputStyle"] = NAME
    if data.get("outputStyle") == NAME:
        if prev and prev not in (NAME, OLD_NAME):
            data["outputStyle"] = prev
        else:
            data.pop("outputStyle", None)
    strip_our_hooks(data)
    overrides = data.get("skillOverrides") or {}
    overrides.pop(NAME, None)
    if "skillOverrides" in data and not overrides:
        del data["skillOverrides"]
    remove_legacy(data)
    say(f"更新 {SETTINGS}：還原 outputStyle、移除 hooks")
    save_settings(data)

    if CLAUDE_MD.exists():
        text = CLAUDE_MD.read_text(encoding="utf-8")
        if BLOCK_START in text:
            say(f"從 {CLAUDE_MD} 移除匯入段")
            backup(CLAUDE_MD)
            start, end = text.index(BLOCK_START), text.index(BLOCK_END) + len(BLOCK_END)
            rest = (text[:start].rstrip() + "\n" + text[end:].lstrip("\n")).strip()
            if not DRY:
                if rest:
                    CLAUDE_MD.write_text(rest + "\n", encoding="utf-8")
                else:
                    CLAUDE_MD.unlink()   # 只剩我們加的那段，表示原本沒有這個檔案
    for p in (STYLE_DST, BASE):
        if p.exists():
            say(f"移除 {p}")
            backup(p)
            if not DRY:
                shutil.rmtree(p) if p.is_dir() else p.unlink()
    say(f"完成。備份在 {BACKUP}。")


if __name__ == "__main__":
    if "--print-agents" in sys.argv:
        print(build_agents_rules(), end="")
    elif "--print" in sys.argv:
        style, core = build_rules()
        print(style + "\n=====\n\n" + core)
    elif "--status" in sys.argv:
        status()
    elif "--uninstall" in sys.argv:
        uninstall()
    else:
        install()
