"""Tests for memory/email_send.send_email() — 5 条分支:

  v2 发信 / 幂等跳过 / 未配置 / docx 缺失 / SKIP 不写审计。

TAU_HOME 隔离到临时目录; SMTP 全程 mock, 无真实外发。
Migrated from scripts/smoke_email_send.py.
"""
import importlib
import os
import shutil
import tempfile
import unittest
from datetime import date
from unittest import mock


class TestEmailSend(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="email_send_test_")
        os.environ["TAU_HOME"] = self.tmp
        # reload 顺序: paths(锚 TAU_HOME) → email_config → email_send
        # 模块级常量 (DONE/SENT/EMAIL_LOG/CONFIG_FILE) 只在 import 时求值一次。
        import tau_coding.paths
        importlib.reload(tau_coding.paths)
        import memory.email_config
        importlib.reload(memory.email_config)
        import memory.email_send
        importlib.reload(memory.email_send)
        self.email_send = memory.email_send
        # 建一份假"今日"日报 docx (DONE = SCHE_TASKS/done)
        today = date.today().isoformat()
        docx_dir = os.path.join(self.tmp, "sche_tasks", "done")
        os.makedirs(docx_dir, exist_ok=True)
        with open(os.path.join(docx_dir, f"{today}_daily_report_test.docx"), "wb") as f:
            f.write(b"fake docx content for test")

    def tearDown(self):
        # 清 env + reload 回默认, 避免常量残留污染后续套件
        os.environ.pop("TAU_HOME", None)
        import tau_coding.paths
        import memory.email_config
        import memory.email_send
        importlib.reload(tau_coding.paths)
        importlib.reload(memory.email_config)
        importlib.reload(memory.email_send)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_valid_cfg(self):
        from memory.email_config import save_email_config
        save_email_config({
            "smtp_host": "smtp.qq.com",
            "smtp_port": 465,
            "smtp_user": "u@qq.com",
            "smtp_pass": "tok",
            "to_addrs": ["a@x.com"],
        })

    def test_v2_path_sends(self):
        """完整 cfg + 无今日 sent 标记 → SMTP_SSL 发信, 写 sent 标记 + audit OK。"""
        self._write_valid_cfg()
        es = self.email_send
        self.assertFalse(os.path.exists(es.SENT))
        with mock.patch.object(es.smtplib, "SMTP_SSL") as m_ssl, \
                mock.patch.object(es.smtplib, "SMTP") as m_plain:
            m_ssl.return_value.__enter__.return_value = mock.MagicMock()
            m_plain.return_value.__enter__.return_value = mock.MagicMock()
            result = es.send_email()
            self.assertIn("已发送", result)
            self.assertTrue(m_ssl.called)                     # port 465 → SSL 路径
        self.assertTrue(os.path.exists(es.SENT))
        with open(es.SENT, encoding="utf-8") as f:
            self.assertIn("daily_", f.read())
        self.assertTrue(os.path.exists(es.EMAIL_LOG))
        with open(es.EMAIL_LOG, encoding="utf-8") as f:
            self.assertIn("OK", f.read())

    def test_idempotent_skip(self):
        """今天已发过 → RuntimeError, 不调 SMTP。"""
        self._write_valid_cfg()
        es = self.email_send
        today = date.today().isoformat()
        os.makedirs(os.path.dirname(es.SENT), exist_ok=True)
        with open(es.SENT, "w", encoding="utf-8") as f:
            f.write(f"{today} {today}_daily_report_test.docx\n")
        with mock.patch.object(es.smtplib, "SMTP_SSL") as m_ssl:
            with self.assertRaises(RuntimeError) as ctx:
                es.send_email()
            self.assertIn("已发过", str(ctx.exception))
            self.assertFalse(m_ssl.called)

    def test_unconfigured_raises_value_error(self):
        """未配置 .tau/tauchain.json → ValueError。"""
        es = self.email_send
        from memory.email_config import CONFIG_FILE
        self.assertFalse(os.path.exists(CONFIG_FILE))
        with self.assertRaises(ValueError) as ctx:
            es.send_email()
        self.assertTrue(
            "配置文件不存在" in str(ctx.exception)
            or "请先跑" in str(ctx.exception),
            str(ctx.exception),
        )

    def test_docx_missing_raises_file_not_found(self):
        """当日 docx 不在 done_dir → FileNotFoundError。"""
        self._write_valid_cfg()
        es = self.email_send
        empty_done = os.path.join(self.tmp, "empty_done")
        with self.assertRaises(FileNotFoundError) as ctx:
            es.send_email(done_dir=empty_done)
        msg = str(ctx.exception)
        self.assertTrue("没有" in msg or "sche_tasks" in msg or "empty_done" in msg, msg)

    def test_skip_does_not_write_audit(self):
        """幂等 SKIP 不写 audit log (避免 scheduler 重跑污染日志)。"""
        self._write_valid_cfg()
        es = self.email_send
        today = date.today().isoformat()
        os.makedirs(os.path.dirname(es.SENT), exist_ok=True)
        with open(es.SENT, "w", encoding="utf-8") as f:
            f.write(f"{today} {today}_daily_report_test.docx\n")
        with self.assertRaises(RuntimeError):
            es.send_email()
        self.assertFalse(os.path.exists(es.EMAIL_LOG))


if __name__ == "__main__":
    unittest.main()
