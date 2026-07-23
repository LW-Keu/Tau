import importlib.util, json, os
from pathlib import Path
from tau_paths import TAUKEY_PATH

_taukey_path = _taukey_mtime = None
taukeys = {}
LEGACY_TAUKEY_PATH = Path(__file__).with_name("taukey.json")

def _load_taukeys():
    global _taukey_path
    p = str(TAUKEY_PATH)
    if TAUKEY_PATH.exists():
        spec = importlib.util.spec_from_file_location("taukey", p)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        _taukey_path = p
        return {k: v for k, v in vars(mod).items() if not k.startswith('_')}
    if LEGACY_TAUKEY_PATH.exists():
        _taukey_path = str(LEGACY_TAUKEY_PATH)
        with LEGACY_TAUKEY_PATH.open(encoding='utf-8') as f: return json.load(f)
    raise Exception(
        f'[ERROR] {p} not found. Run `tau configure`, or copy assets/template/taukey_template.py and fill in your key.'
    )

def reload_taukeys():
    global _taukey_mtime, taukeys
    mt = os.stat(_taukey_path).st_mtime_ns if _taukey_path else -1
    if mt == _taukey_mtime: return taukeys, False
    mk = _load_taukeys(); _taukey_mtime = os.stat(_taukey_path).st_mtime_ns
    print(f'[Info] Load taukeys from {_taukey_path}')
    taukeys = mk
    return mk, True
