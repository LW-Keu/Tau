"""Tau 邮件配置读写库：.tau/tauchain.json + 字段契约 + 邮箱域名 → SMTP 推断。"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.paths import TAU, ASSETS
CONFIG_DIR: str = str(TAU)
CONFIG_FILE: str = str(TAU / "tauchain.json")

REQUIRED: tuple = (
    "smtp_host",
    "smtp_port",
    "smtp_user",
    "smtp_pass",
    "to_addrs",
)

DEFAULTS: Dict[str, Any] = {
    "smtp_use_ssl": True,
    "smtp_timeout": 30,
    "sender_name": "",
    "subject": "Tau 日报 {date}",
    "body": "今日日报见附件。",
}


def has_email_config() -> bool:
    """True 表示 .tau/tauchain.json 存在。"""
    return os.path.exists(CONFIG_FILE)


def validate(cfg: Dict[str, Any]) -> List[str]:
    """校验 cfg 字段，返回错误列表（空列表 = 通过）。纯函数，不读文件、不连网络。

    Schema (v2):
      - 顶层单账户字段（向后兼容 v1）
      - 或 accounts: list[dict] 多账户轮询（v2 新增）；非空时忽略顶层 smtp_*
    """
    if not isinstance(cfg, dict):
        return ["cfg 必须是 dict"]
    errs: List[str] = []

    accounts = cfg.get("accounts")
    has_accounts = isinstance(accounts, list) and len(accounts) > 0

    if has_accounts:
        # 多账户模式：只校验 accounts，顶层 smtp_* 可缺
        if not all(isinstance(a, dict) for a in accounts):
            errs.append("accounts 每项必须是 dict")
        else:
            for i, a in enumerate(accounts):
                for k in ("smtp_host", "smtp_port", "smtp_user", "smtp_pass"):
                    if k not in a:
                        errs.append(f"accounts[{i}] 缺少字段: {k}")
                if "smtp_port" in a:
                    p = a["smtp_port"]
                    if not isinstance(p, int) or isinstance(p, bool) or not (1 <= p <= 65535):
                        errs.append(f"accounts[{i}].smtp_port 必须是 1-65535 整数")
                if "label" in a and not isinstance(a["label"], str):
                    errs.append(f"accounts[{i}].label 必须是字符串")
        # 顶层 to_addrs 仍必填（收件人统一）
        if "to_addrs" not in cfg:
            errs.append("缺少字段: to_addrs")
    else:
        # 单账户模式（v1 行为）
        for k in REQUIRED:
            if k not in cfg:
                errs.append(f"缺少字段: {k}")

    if "to_addrs" in cfg:
        ta = cfg["to_addrs"]
        if not isinstance(ta, list) or not ta or not all(
            isinstance(r, str) and r for r in ta
        ):
            errs.append("to_addrs 必须是非空字符串列表")
    return errs


def iter_accounts(cfg: Dict[str, Any]):
    """Yield (label, acc_cfg) 元组，按优先级排列。

    - accounts 非空 → 逐项 yield，每项已是完整单账户 dict
    - accounts 缺失/空 → yield (None, cfg) 单条（v1 兼容）
    """
    accounts = cfg.get("accounts")
    if isinstance(accounts, list) and accounts:
        for a in accounts:
            label = a.get("label") if isinstance(a, dict) else None
            yield (label, a)
    else:
        yield (None, cfg)


def _ensure_meta(cfg: Dict[str, Any]) -> Dict[str, Any]:
    cfg = dict(cfg)
    meta = cfg.get("meta")
    if not isinstance(meta, dict):
        meta = {}
    meta["version"] = 1
    cfg["meta"] = meta
    return cfg


def save_email_config(cfg: Dict[str, Any]) -> None:
    """原子写 cfg 到 .tau/tauchain.json，chmod 0o600。备份旧文件（仅在存在时）。

    输入 dict 不被修改。

    Raises:
        ValueError: 字段不全或写盘失败。
    """
    errs = validate(cfg)
    if errs:
        raise ValueError("配置不合法: " + "; ".join(errs))

    cfg = _ensure_meta(cfg)

    os.makedirs(CONFIG_DIR, exist_ok=True)

    # 备份旧文件（一次；备份失败不阻塞主流程）
    if os.path.exists(CONFIG_FILE):
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        base, _ext = os.path.splitext(CONFIG_FILE)
        bak = f"{base}.json.bak.{ts}"
        try:
            os.replace(CONFIG_FILE, bak)
        except OSError:
            pass

    tmp = CONFIG_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, CONFIG_FILE)
    except OSError as exc:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise ValueError(f"无法写入 {CONFIG_FILE}: {exc}") from exc

    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass  # Windows 权限降级


def load_email_config() -> Dict[str, Any]:
    """读 .tau/tauchain.json，校验 + 补默认。

    Raises:
        ValueError: 文件缺失 / JSON 错 / 字段不全 / _meta.version 非 1。
    """
    if not os.path.exists(CONFIG_FILE):
        raise ValueError(
            f"配置文件不存在: {CONFIG_FILE}，请先跑邮件配置 SOP"
        )

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{CONFIG_FILE} JSON 格式错误: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"无法读取 {CONFIG_FILE}: {exc}") from exc

    errs = validate(cfg)
    if errs:
        raise ValueError("配置文件不合法: " + "; ".join(errs))

    meta = cfg.get("meta")
    if not isinstance(meta, dict):
        raise ValueError("meta 必须是 object")
    ver = meta.get("version")
    if ver not in (1, 2):
        raise ValueError(
            f"meta.version 必须是 1 或 2，当前为 {ver!r}"
        )

    for k, v in DEFAULTS.items():
        cfg.setdefault(k, v)
    # 单账户模式才设 sender_name 默认值；accounts 模式每项已自带 smtp_user
    if not cfg.get("accounts") and not cfg["sender_name"]:
        cfg["sender_name"] = cfg["smtp_user"]
    return cfg


# --- SMTP 提供商推断（纯函数，无网络） ---

_PROVIDERS_TABLE: Path = ASSETS / "email_providers.json"


def infer_provider(
    addr: str, table_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """从邮箱地址推断 SMTP 元数据。返回 {host, port, ssl, note} 或 None。

    表文件丢失或地址不含 @ 返回 None，让配置入口降级到手填。
    供邮件配置 SOP 在用户输入邮箱后免手填 host/port/SSL。
    """
    if not addr or "@" not in addr:
        return None
    domain = addr.split("@", 1)[1].lower().strip()
    try:
        with open(table_path or _PROVIDERS_TABLE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    for p in data.get("providers", []):
        if p.get("domain") == domain:
            return {
                "host": p["host"],
                "port": p["port"],
                "ssl": p["ssl"],
                "note": p.get("note", ""),
            }
    return None