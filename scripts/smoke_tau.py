"""Smoke test: tau_agent symbols import from their defining modules."""
from tau_agent.handler import TauHandler
from tau_agent.tools.utils import smart_format, format_error, consume_file, get_global_memory
from tau_agent.tools.code_run import code_run, ask_user
from tau_agent.tools.file_io import file_read, file_patch
from tau_agent.tools.web import web_scan, web_execute_js, first_init_driver
from tau_agent.tools.utils import smart_format as sf2
print(f'[SMOKE-OK] handler={TauHandler.__module__} smart_format={smart_format is sf2} '
      f'code_run={code_run.__module__} file_io={file_read.__module__} web={web_scan.__module__}')
