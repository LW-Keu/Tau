from setup.configure_taukey import generate_taukey


def test_generated_config_keeps_explicit_types():
    config = {
        "type": "native_oai",
        "name": "primary",
        "apikey": "key",
        "apibase": "https://example.test",
        "model": "model",
    }

    generated = generate_taukey([config], [])

    assert "mixin_config = {\n    'type': 'mixin'," in generated
    assert "native_oai_config = {\n    'type': 'native_oai'," in generated
