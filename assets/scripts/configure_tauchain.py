#!/usr/bin/env python3
"""configure_tauchain.py - 人类首次配置 Tau 邮件 SMTP（v2 支持多账户轮询）。

用法:
  首次配置（单账户）：
    python assets/scripts/configure_tauchain.py                # 交互模式（默认）
    python assets/scripts/configure_tauchain.py --interactive  # 同上
    python assets/scripts/configure_tauchain.py --non-interactive  # 读环境变量
    python assets/scripts/configure_tauchain.py --send-test    # 配置后立即发一封测试邮件

  多账户 fallback（v2）：
    python assets/scripts/configure_tauchain.py --migrate-to-v2          # 把 v1 顶层账户迁为 accounts[0]
    python assets/scripts/configure_tauchain.py --add-account            # 交互添加新账户
    python assets/scripts/configure_tauchain.py --add-account --label backup --host smtp.163.com --port 465 --user x@163.com --password AUTHCODE
    python assets/scripts/configure_tauchain.py --list-accounts          # 列出已有账户
    python assets/scripts/configure_tauchain.py --remove-account LABEL   # 删指定 label

写入与字段契约统一来自 memory.email_config（禁止自带 json.dump 绕开校验）。
"""
import argparse
import getpass
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from memory import email_config


DEFAULTS = {
    "sender_name": "Tau 日报",
    "subject": "Tau 日报 {date}",
    "body": "今日日报见附件。",
    "smtp_timeout": 30,
}


def _env(name: str, default: str = "") -> str:
    v = os.environ.get(name)
    return v if v is not None else default


def _prompt(label: str, default: str = "", secret: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    prompt = f"{label}{suffix}: "
    if secret:
        return getpass.getpass(prompt)
    return input(prompt).strip() or default


def _infer_or_ask(addr: str) -> dict:
    """SMTP 推断；命中则用命中值，未命中则手填。"""
    info = email_config.infer_provider(addr)
    if info is None:
        print(f"未识别 {addr!r} 的 SMTP 服务商，需手填：")
        host = _prompt("SMTP 服务器", "smtp.example.com")
        port_s = _prompt("端口（SSL 465 / STARTTLS 587）", "465")
        ssl_s = _prompt("SSL 还是 STARTTLS", "SSL").upper()
        return {
            "host": host,
            "port": int(port_s),
            "ssl": ssl_s == "SSL",
            "note": "手填",
        }
    print(f"推断：{info['host']}:{info['port']}（{'SSL' if info['ssl'] else 'STARTTLS'}）")
    if info.get("note"):
        print(f"注意：{info['note']}")
    return info


def _interactive() -> dict:
    print("=== Tau 邮件 SMTP 首次配置 ===\n")
    addr = _prompt("发件邮箱地址（如 you@qq.com）")
    if not addr or "@" not in addr:
        sys.exit("发件邮箱不能为空且必须含 @")

    info = _infer_or_ask(addr)

    sender = _prompt("发件人显示名", DEFAULTS["sender_name"])
    recipients_s = _prompt("收件人（逗号分隔）")
    if not recipients_s:
        sys.exit("收件人不能为空")

    auth = _prompt("SMTP 授权码", secret=True)
    if not auth:
        sys.exit("授权码不能为空")

    return {
        "smtp_host": info["host"],
        "smtp_port": info["port"],
        "smtp_use_ssl": info["ssl"],
        "smtp_user": addr,
        "smtp_pass": auth,
        "sender_name": sender,
        "to_addrs": [r.strip() for r in recipients_s.split(",") if r.strip()],
        "subject": DEFAULTS["subject"],
        "body": DEFAULTS["body"],
        "smtp_timeout": DEFAULTS["smtp_timeout"],
    }


def _non_interactive() -> dict:
    """从环境变量读全部字段；缺失则报错退出（不静默回填）。"""
    required_env = {
        "TAU_SMTP_HOST": "smtp_host",
        "TAU_SMTP_PORT": "smtp_port",
        "TAU_SMTP_USER": "smtp_user",
        "TAU_SMTP_PASS": "smtp_pass",
        "TAU_TO_ADDRS": "to_addrs",
    }
    missing = [k for k in required_env if not _env(k)]
    if missing:
        sys.exit(f"非交互模式需设置环境变量：{', '.join(missing)}")

    port = _env("TAU_SMTP_PORT")
    try:
        port_int = int(port)
    except ValueError:
        sys.exit(f"TAU_SMTP_PORT 必须是整数，得到 {port!r}")

    ssl = _env("TAU_SMTP_SSL", "true").lower() in ("1", "true", "yes", "ssl")
    return {
        "smtp_host": _env("TAU_SMTP_HOST"),
        "smtp_port": port_int,
        "smtp_use_ssl": ssl,
        "smtp_user": _env("TAU_SMTP_USER"),
        "smtp_pass": _env("TAU_SMTP_PASS"),
        "sender_name": _env("TAU_SENDER_NAME", DEFAULTS["sender_name"]),
        "to_addrs": [r.strip() for r in _env("TAU_TO_ADDRS").split(",") if r.strip()],
        "subject": _env("TAU_SUBJECT", DEFAULTS["subject"]),
        "body": _env("TAU_BODY", DEFAULTS["body"]),
        "smtp_timeout": int(_env("TAU_SMTP_TIMEOUT", str(DEFAULTS["smtp_timeout"]))),
    }


def _send_test() -> None:
    """调 memory.email_send.send_email() 发一封测试邮件（复用库 API）。"""
    sys.path.insert(0, str(REPO / "memory"))
    from email_send import send_email
    print("\n发送测试邮件...")
    try:
        result = send_email()  # 默认 today=今天,从 done_dir 找当日 docx
        print(f"✅ {result}")
    except RuntimeError as e:
        if "已发过" in str(e):
            print(f"⚠️  {e}（如需重测，删 $TAU_HOME/temp/email_report.sent）")
        else:
            print(f"❌ 发送失败：{e}")
            print("   常见：授权码错 / 端口被挡 / SSL/STARTTLS 选错")
            sys.exit(1)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)


def _cmd_send_test_only() -> None:
    """独立连通性自检：发测试邮件（无 docx 附件、不写 .sent、不影响正常日报）"""
    sys.path.insert(0, str(REPO / "memory"))
    try:
        from email_send import send_test_email
    except ImportError as e:
        print(f"❌ 无法导入 send_test_email：{e}")
        print("   请确认 memory/email_send.py 已更新到最新版本")
        sys.exit(1)
    print("\n📡 发送测试邮件（连通性自检）...")
    try:
        result = send_test_email()
        print(f"✅ {result}")
    except ValueError as e:
        print(f"❌ 配置缺失/不合法：{e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"❌ 全部账户发送失败：{e}")
        print("   常见：授权码错 / 端口被挡 / SSL/STARTTLS 选错 / 网络封")
        sys.exit(1)


def _cmd_migrate_to_v2() -> None:
    """把 v1 顶层单账户迁为 v2 accounts[0]"""
    from memory import email_config as ec
    try:
        cfg = ec.load_email_config()
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ 加载配置失败：{e}")
        sys.exit(1)
    if cfg.get("accounts"):
        print("⚠️  已经是 v2（含 accounts 字段），无需迁移")
        return
    acc = {
        "label": "primary",
        "smtp_host": cfg["smtp_host"],
        "smtp_port": cfg["smtp_port"],
        "smtp_user": cfg["smtp_user"],
        "smtp_pass": cfg["smtp_pass"],
        "smtp_use_ssl": cfg.get("smtp_use_ssl", True),
    }
    cfg["accounts"] = [acc]
    cfg.setdefault("meta", {})["version"] = 2
    # 清掉顶层 smtp_user/pass 避免歧义（accounts[0] 已是真值）
    for k in ("smtp_user", "smtp_pass", "smtp_host", "smtp_port", "smtp_use_ssl"):
        cfg.pop(k, None)
    errs = ec.validate(cfg)
    if errs:
        print(f"❌ 迁移后校验失败：{errs}")
        sys.exit(1)
    ec.save_email_config(cfg)
    print("✅ 已迁移到 v2（accounts[0] = primary）。可用 --list-accounts 校验")


def _cmd_list_accounts() -> None:
    """列出当前所有 SMTP 账户"""
    from memory import email_config as ec
    try:
        cfg = ec.load_email_config()
    except FileNotFoundError:
        print("❌ 配置文件不存在，请先 --interactive 初始化")
        sys.exit(1)
    accounts = cfg.get("accounts") or [cfg]
    print(f"\n共 {len(accounts)} 个 SMTP 账户：")
    for i, a in enumerate(accounts):
        label = a.get("label", "(default)")
        ssl = a.get("smtp_use_ssl", True)
        print(f"  [{i}] {label:20s} {a['smtp_user']:30s} {a['smtp_host']}:{a.get('smtp_port', 465)} SSL={ssl}")


def _cmd_add_account(args) -> None:
    """追加一个新 SMTP 账户。优先用 CLI 参数,缺则走交互。"""
    from memory import email_config as ec
    try:
        cfg = ec.load_email_config()
    except FileNotFoundError:
        print("❌ 配置文件不存在，请先 --interactive 初始化")
        sys.exit(1)
    # 若还是 v1,提示先迁移
    if not cfg.get("accounts") and cfg.get("meta", {}).get("version") != 2:
        print("ℹ️  检测到 v1 配置，将同时迁移到 v2 并把现账户置为 accounts[0]")
        cfg = {
            "meta": {"version": 2, "purpose": cfg.get("meta", {}).get("purpose", "Tau 日报 SMTP")},
            "to_addrs": cfg.get("to_addrs", []),
            "accounts": [{
                "label": "primary",
                "smtp_host": cfg["smtp_host"],
                "smtp_port": cfg["smtp_port"],
                "smtp_user": cfg["smtp_user"],
                "smtp_pass": cfg["smtp_pass"],
                "smtp_use_ssl": cfg.get("smtp_use_ssl", True),
            }],
        }
    # 非交互路径
    if all([args.label, args.host, args.port, args.user, args.password]):
        new_acc = {
            "label": args.label,
            "smtp_host": args.host,
            "smtp_port": args.port,
            "smtp_user": args.user,
            "smtp_pass": args.password,
            "smtp_use_ssl": args.ssl if args.ssl is not None else True,
        }
    else:
        # 交互
        print("\n追加新 SMTP 账户（Ctrl+C 取消）：")
        label = input("  label (e.g. backup-163): ").strip()
        if not label:
            print("❌ label 必填")
            sys.exit(1)
        host = input("  smtp_host: ").strip()
        port_s = input("  smtp_port [465]: ").strip() or "465"
        try:
            port = int(port_s)
        except ValueError:
            print("❌ port 必须是整数")
            sys.exit(1)
        user = input("  smtp_user: ").strip()
        pw = input("  smtp_pass (授权码): ").strip()
        ssl_s = input("  使用 SSL? [Y/n]: ").strip().lower()
        use_ssl = ssl_s not in ("n", "no", "false", "0")
        new_acc = {
            "label": label, "smtp_host": host, "smtp_port": port,
            "smtp_user": user, "smtp_pass": pw, "smtp_use_ssl": use_ssl,
        }
    # 查重
    if any(a.get("label") == new_acc["label"] for a in cfg["accounts"]):
        print(f"❌ label 已存在: {new_acc['label']}")
        sys.exit(1)
    cfg["accounts"].append(new_acc)
    errs = ec.validate(cfg)
    if errs:
        print(f"❌ 校验失败：{errs}")
        sys.exit(1)
    ec.save_email_config(cfg)
    print(f"✅ 已追加账户 [{new_acc['label']}]，现共 {len(cfg['accounts'])} 个")


def _cmd_remove_account(label: str) -> None:
    """按 label 删除账户"""
    from memory import email_config as ec
    try:
        cfg = ec.load_email_config()
    except FileNotFoundError:
        print("❌ 配置文件不存在")
        sys.exit(1)
    accounts = cfg.get("accounts")
    if not accounts:
        print("⚠️  当前不是 v2 多账户模式，无账户可删")
        return
    new_list = [a for a in accounts if a.get("label") != label]
    if len(new_list) == len(accounts):
        print(f"❌ 未找到 label={label!r}")
        sys.exit(1)
    if len(new_list) == 0:
        print("❌ 不能删完，至少保留 1 个账户")
        sys.exit(1)
    cfg["accounts"] = new_list
    errs = ec.validate(cfg)
    if errs:
        print(f"❌ 删除后校验失败：{errs}")
        sys.exit(1)
    ec.save_email_config(cfg)
    print(f"✅ 已删除 [{label}]，剩余 {len(new_list)} 个账户")


def _cmd_list_recipients() -> None:
    """打印顶层 to_addrs。"""
    from memory import email_config as ec
    try:
        cfg = ec.load_email_config()
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ 加载配置失败：{e}")
        sys.exit(1)
    to = cfg.get("to_addrs") or []
    if not to:
        print("（暂无收件人）")
        return
    print(f"\n共 {len(to)} 个收件人：")
    for i, a in enumerate(to):
        print(f"  [{i}] {a}")


def _cmd_add_recipient(addr: str) -> None:
    """追加收件人；自动 v1→v2 升级(若顶层 smtp 还在)。"""
    from memory import email_config as ec
    try:
        cfg = ec.load_email_config()
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ 加载配置失败：{e}")
        sys.exit(1)
    addr = addr.strip()
    if not addr or "@" not in addr:
        print("❌ 邮箱格式无效")
        sys.exit(1)
    # 兜底：若 v1 schema（无 accounts）但有顶层凭据,自动迁移
    if not cfg.get("accounts") and cfg.get("smtp_user") and not cfg.get("meta", {}).get("version") == 2:
        print("ℹ️  检测到 v1 配置，先自动迁移到 v2 accounts 模式")
        _cmd_migrate_to_v2()
        cfg = ec.load_email_config()
    to = cfg.get("to_addrs", [])
    if addr in to:
        print(f"⚠️  收件人已存在：{addr}")
        return
    to.append(addr)
    cfg["to_addrs"] = to
    errs = ec.validate(cfg)
    if errs:
        print(f"❌ 校验失败：{errs}")
        sys.exit(1)
    ec.save_email_config(cfg)
    print(f"✅ 已追加收件人 [{addr}]，现共 {len(to)} 个")


def _cmd_remove_recipient(addr: str) -> None:
    from memory import email_config as ec
    try:
        cfg = ec.load_email_config()
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ 加载配置失败：{e}")
        sys.exit(1)
    to = cfg.get("to_addrs", [])
    if addr not in to:
        print(f"❌ 未找到收件人：{addr}")
        sys.exit(1)
    to.remove(addr)
    cfg["to_addrs"] = to
    errs = ec.validate(cfg)
    if errs:
        print(f"❌ 校验失败：{errs}")
        sys.exit(1)
    ec.save_email_config(cfg)
    print(f"✅ 已删除收件人 [{addr}]，剩余 {len(to)} 个")


def _cmd_set_recipients(addr_list: str) -> None:
    """逗号分隔整组替换。空串=清空(校验会拦,需 at least 1)。"""
    from memory import email_config as ec
    try:
        cfg = ec.load_email_config()
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ 加载配置失败：{e}")
        sys.exit(1)
    new_list = [a.strip() for a in addr_list.split(",") if a.strip()]
    for a in new_list:
        if "@" not in a:
            print(f"❌ 邮箱格式无效：{a}")
            sys.exit(1)
    cfg["to_addrs"] = new_list
    errs = ec.validate(cfg)
    if errs:
        print(f"❌ 校验失败：{errs}")
        sys.exit(1)
    ec.save_email_config(cfg)
    print(f"✅ 已替换 to_addrs,共 {len(new_list)} 个收件人")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--interactive", action="store_true", help="交互模式（默认）")
    g.add_argument("--non-interactive", action="store_true", help="非交互模式（读环境变量）")
    ap.add_argument("--send-test", action="store_true", help="配置后立即发一封测试邮件")
    # 多账户（v2）
    ap.add_argument("--migrate-to-v2", action="store_true", help="把 v1 顶层账户迁为 accounts[0]")
    ap.add_argument("--add-account", action="store_true", help="追加新 SMTP 账户（v2）")
    ap.add_argument("--list-accounts", action="store_true", help="列出所有 SMTP 账户")
    ap.add_argument("--remove-account", metavar="LABEL", help="按 label 删除账户（v2）")
    # 收件人管理（v2 顶层 to_addrs 共享）
    ap.add_argument("--add-recipient", metavar="ADDR", help="追加收件人邮箱（v2 顶层 to_addrs）")
    ap.add_argument("--remove-recipient", metavar="ADDR", help="按邮箱删除收件人（v2 顶层 to_addrs）")
    ap.add_argument("--list-recipients", action="store_true", help="列出当前 to_addrs")
    ap.add_argument("--set-recipients", metavar="ADDR1,ADDR2,...", help="替换整组收件人（逗号分隔）")
    ap.add_argument("--send-test-only", action="store_true", help="独立连通性自检：发一封测试邮件（无 docx 附件、不写 .sent）")
    # add-account 非交互参数
    ap.add_argument("--label", help="账户 label")
    ap.add_argument("--host", help="SMTP host")
    ap.add_argument("--port", type=int, help="SMTP port")
    ap.add_argument("--user", help="SMTP user")
    ap.add_argument("--password", help="SMTP password / 授权码")
    ap.add_argument("--ssl", dest="ssl", action="store_true", default=None, help="SMTP_SSL")
    ap.add_argument("--no-ssl", dest="ssl", action="store_false", help="STARTTLS")
    args = ap.parse_args()

    # v2 多账户子命令
    if args.send_test_only:
        _cmd_send_test_only()
        return
    if args.send_test and not (args.migrate_to_v2 or args.add_account or args.remove_account):
        _send_test()
        return
    if args.migrate_to_v2:
        _cmd_migrate_to_v2()
        if args.send_test:
            _send_test()
        return
    if args.list_accounts:
        _cmd_list_accounts()
        return
    if args.remove_account:
        _cmd_remove_account(args.remove_account)
        if args.send_test:
            _send_test()
        return
    if args.add_account:
        _cmd_add_account(args)
        if args.send_test:
            _send_test()
        return
    if args.list_recipients:
        _cmd_list_recipients()
        return
    if args.add_recipient:
        _cmd_add_recipient(args.add_recipient)
        return
    if args.remove_recipient:
        _cmd_remove_recipient(args.remove_recipient)
        return
    if args.set_recipients:
        _cmd_set_recipients(args.set_recipients)
        return

    if args.non_interactive:
        cfg = _non_interactive()
    else:
        cfg = _interactive()

    print(f"\n写入配置到 {email_config.CONFIG_FILE} ...")
    email_config.save_email_config(cfg)
    print("✅ 已保存（含 chmod 0o600，旧文件已备份）")

    if args.send_test:
        _send_test()


if __name__ == "__main__":
    main()