from unittest.mock import patch

import pytest

from config import default_config, load_config


class TestDefaultConfig:
    def test_has_required_keys(self):
        required = [
            'secret', 'superadmin_pass', 'db_host', 'db_port',
            'db_database', 'db_user', 'db_password', 'es_host',
        ]
        for key in required:
            assert key in default_config, f'Missing key: {key}'

    def test_default_secret_is_default(self):
        assert default_config['secret'] == 'quantumpacs-default-secret-32-bytes-long!!'

    def test_db_defaults_are_reasonable(self):
        assert default_config['db_host'] == '127.0.0.1'
        assert default_config['db_port'] == '5432'
        assert default_config['db_database'] == 'quantumpacs'
        assert default_config['db_user'] == 'quantumpacs'

    def test_es_host_default(self):
        assert default_config['es_host'] == 'localhost'

    def test_secret_falls_back_to_dev_default(self):
        cfg = load_config(overrides={'secret': 'default', 'db_password': 'pa55w0rd'})
        assert cfg['secret'] == 'quantumpacs-dev-secret-replace-in-production-32b'

    def test_env_overrides_default(self, monkeypatch):
        monkeypatch.setenv('DB_HOST', '10.0.0.1')
        monkeypatch.setenv('DB_PORT', '9999')
        monkeypatch.setenv('SECRET', 'env-secret')
        cfg = load_config()
        assert cfg['db_host'] == '10.0.0.1'
        assert cfg['db_port'] == '9999'
        assert cfg['secret'] == 'env-secret'

    def test_overrides_param_takes_precedence(self):
        cfg = load_config(overrides={'db_host': 'override-host', 'secret': 'override-secret'})
        assert cfg['db_host'] == 'override-host'
        assert cfg['secret'] == 'override-secret'

    def test_is_docker_set_by_env(self, monkeypatch):
        monkeypatch.setenv('QUANTUMPACS_DOCKER', '1')
        import importlib
        import config as cfg_module
        importlib.reload(cfg_module)
        assert cfg_module.is_docker is True

    def test_is_docker_false_by_default(self, monkeypatch):
        monkeypatch.delenv('QUANTUMPACS_DOCKER', raising=False)
        import importlib
        import config as cfg_module
        importlib.reload(cfg_module)
        assert cfg_module.is_docker is False

    def test_env_keys_are_upper_case(self, monkeypatch):
        monkeypatch.setenv('SUPERADMIN_PASS', 's3cret!')
        cfg = load_config()
        assert cfg['superadmin_pass'] == 's3cret!'

    def test_local_yaml_overrides_defaults(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv('DB_HOST', '')
        monkeypatch.setenv('SECRET', '')
        yaml_content = 'db_host: 192.168.1.1\nsecret: yaml-secret\n'
        (tmp_path / 'config.local.yaml').write_text(yaml_content)
        cfg = load_config()
        assert cfg['db_host'] == '192.168.1.1'
        assert cfg['secret'] == 'yaml-secret'
        (tmp_path / 'config.local.yaml').unlink()

    def test_missing_local_yaml_does_not_fail(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cfg = load_config()
        assert 'db_host' in cfg
