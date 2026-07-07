"""每日日报 SMTP 发送：定位当日 .docx，作为附件发送。失败即抛。"""

import os
import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from core.paths import SCHE_TASKS, TEMP
from memory.email_config import load_email_config
DONE = str(SCHE_TASKS / "done")
SENT = str(TEMP / "email_report.sent")
EMAIL_LOG = str(TEMP / "email_report.log")


def _today() -> str:
    return datetime.now().strftime('%Y-%m-%d')


def _today_docx(done_dir: str, today: str) -> str:
    hits = sorted(
        n for n in os.listdir(done_dir)
        if n.startswith(today) and n.endswith('.docx')
    )
    if not hits:
        raise FileNotFoundError(
            f"{done_dir} 中没有 {today} 开头的 .docx（请先生成日报）"
        )
    return os.path.join(done_dir, hits[0])


def _is_fallback_docx(path: str) -> bool:
    return '_fallback' in os.path.basename(path)


def _build(cfg: dict, docx_path: str, date: str, acc: dict = None) -> EmailMessage:
    """组装邮件。多账户模式:acc 覆盖 From;单账户模式:acc=None,从 cfg 推。"""
    msg = EmailMessage()
    subject = cfg['subject'].format(date=date)
    body = cfg['body'].format(date=date)
    if _is_fallback_docx(docx_path):
        subject = f'[兜底] {subject}'
        body = (
            '⚠️ 当日正常日报未生成，以下是兜底版本（最近一份日报）。\n\n'
            + body
        )
    src = acc if acc is not None else cfg
    sender_user = src['smtp_user']
    sender_name = src.get('sender_name') or cfg.get('sender_name', '')
    msg['Subject'] = subject
    msg['From'] = f"{sender_name} <{sender_user}>"
    msg['To'] = ', '.join(cfg['to_addrs'])
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(domain=sender_user.split('@', 1)[1])
    msg.set_content(body)
    with open(docx_path, 'rb') as f:
        data = f.read()
    msg.add_attachment(
        data,
        maintype='application',
        subtype='vnd.openxmlformats-officedocument.wordprocessingml.document',
        filename=os.path.basename(docx_path),
    )
    return msg


def _already_sent(today: str, sent_path: str) -> bool:
    if not os.path.exists(sent_path):
        return False
    try:
        with open(sent_path, encoding='utf-8') as f:
            line = f.readline().strip()
        return line.startswith(today)
    except OSError:
        return False


def _audit(today: str, status: str, docx_path: str = '', err: str = '', label: str = None) -> None:
    """写审计行（失败不抛——审计是辅助，发送主流程不受影响）。"""
    try:
        os.makedirs(os.path.dirname(EMAIL_LOG), exist_ok=True)
        with open(EMAIL_LOG, 'a', encoding='utf-8') as f:
            docx = os.path.basename(docx_path) if docx_path else '-'
            tag = f'[{label}] ' if label else ''
            f.write(
                f'{datetime.now().isoformat(timespec="seconds")} '
                f'{today} {status} {tag}{docx} {err}\n'
            )
    except OSError:
        pass


def _smtp_send(acc: dict, email_msg: EmailMessage, timeout: int) -> None:
    """用单账户配置执行 SMTP 投递。失败抛 smtplib.SMTPException 或 OSError。"""
    if acc.get('smtp_use_ssl', True):
        with smtplib.SMTP_SSL(
            acc['smtp_host'], acc['smtp_port'], timeout=timeout
        ) as s:
            s.login(acc['smtp_user'], acc['smtp_pass'])
            s.send_message(email_msg)
    else:
        with smtplib.SMTP(
            acc['smtp_host'], acc['smtp_port'], timeout=timeout
        ) as s:
            s.starttls()
            s.login(acc['smtp_user'], acc['smtp_pass'])
            s.send_message(email_msg)


def send_email(done_dir: str = DONE, today: str = None, sent_path: str = SENT) -> str:
    """发日报邮件。幂等：当天发过抛 RuntimeError。

    支持多账户轮询（v2 schema）：cfg.accounts 非空时逐个尝试，
    任意一个成功即返回，全部失败抛 RuntimeError。

    Raises:
        ValueError: 配置缺失/不合法（来自 email_config.load_email_config）。
        FileNotFoundError: 当日 .docx 不在 done_dir。
        RuntimeError: 当天已发过 或 所有 SMTP 账户均失败。
    """
    from typing import Optional
    from memory.email_config import iter_accounts
    today = today or _today()

    cfg = load_email_config()  # 缺配置/不合法抛 ValueError

    if _already_sent(today, sent_path):
        raise RuntimeError(f'当天已发过日报 ({today})，跳过')

    docx_path = _today_docx(done_dir, today)
    to_addrs = cfg['to_addrs']
    timeout = cfg.get('smtp_timeout', 30)

    last_err: Optional[str] = None
    tried = 0
    winner_label: Optional[str] = None
    for label, acc in iter_accounts(cfg):
        tried += 1
        email_msg = _build(cfg, docx_path, today, acc=acc)
        try:
            _smtp_send(acc, email_msg, timeout)
        except (smtplib.SMTPException, OSError) as exc:
            last_err = str(exc)
            _audit(today, 'FAIL', docx_path, last_err, label=label)
            continue
        winner_label = label
        break

    if winner_label is None and last_err is not None:
        raise RuntimeError(
            f'全部 {tried} 个 SMTP 账户失败: {last_err}'
        )

    os.makedirs(os.path.dirname(sent_path), exist_ok=True)
    tmp = sent_path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        tag = f'[{winner_label}] ' if winner_label else ''
        f.write(f'{today} {tag}{os.path.basename(docx_path)}\n')
    os.replace(tmp, sent_path)
    _audit(today, 'OK', docx_path, '', label=winner_label)
    suffix = f'（账户: {winner_label}）' if winner_label else ''
    return (
        f'已发送 {os.path.basename(docx_path)} → '
        f'{", ".join(to_addrs)}{suffix}'
    )


def send_test_email(cfg: dict = None, today: str = None) -> str:
    """配置连通性自检：发一封极简测试邮件（无 docx 附件、不写 .sent）。

    - 遍历 cfg.accounts，首个成功即返回
    - 全部失败抛 RuntimeError
    - 不修改任何 sent_path，写 audit 行（label=账户）
    """
    from memory.email_config import iter_accounts
    from email.message import EmailMessage
    from email.utils import formatdate, make_msgid
    today = today or _today()
    cfg = cfg or load_email_config()
    to_addrs = cfg['to_addrs']
    timeout = cfg.get('smtp_timeout', 30)

    last_err: Optional[str] = None
    tried = 0
    winner_label: Optional[str] = None
    for label, acc in iter_accounts(cfg):
        tried += 1
        msg = EmailMessage()
        msg['Subject'] = f'[Tau-Test] SMTP 连通性自检 {today}'
        msg['From'] = f"{acc.get('sender_name') or cfg.get('sender_name', 'Tau')} <{acc['smtp_user']}>"
        msg['To'] = ', '.join(to_addrs)
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid(domain=acc['smtp_user'].split('@', 1)[1])
        msg.set_content(
            f'这是一封来自 Tau 配置脚本的测试邮件。\n\n'
            f'发件账户: {label} ({acc["smtp_user"]})\n'
            f'SMTP: {acc["smtp_host"]}:{acc.get("smtp_port", 465)} SSL={acc.get("smtp_use_ssl", True)}\n'
            f'收件人: {", ".join(to_addrs)}\n'
            f'发送时间: {today}\n'
        )
        try:
            _smtp_send(acc, msg, timeout)
        except (smtplib.SMTPException, OSError) as exc:
            last_err = str(exc)
            _audit(today, 'TEST-FAIL', '', last_err, label=label)
            continue
        winner_label = label
        _audit(today, 'TEST-OK', '', '', label=label)
        break

    if winner_label is None and last_err is not None:
        raise RuntimeError(f'全部 {tried} 个 SMTP 账户失败: {last_err}')
    suffix = f'（账户: {winner_label}）' if winner_label else ''
    return f'已发测试邮件 → {", ".join(to_addrs)}{suffix}'


if __name__ == '__main__':
    try:
        print(send_email())
    except Exception as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        sys.exit(1)