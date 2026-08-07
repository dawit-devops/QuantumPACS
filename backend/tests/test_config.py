

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

    def test_has_dicom_config_keys(self):
        assert default_config['dicom_ae_title'] == 'QUANTUMPACS'
        assert default_config['dicom_cstore_port'] == '11112'

    def test_dead_dicom_ports_removed(self):
        # ME-07: the c-move listener was never started and remains removed;
        # dicom_mwl_port is live again (ME-03) as an optional dedicated MWL
        # listener (empty default = MWL on the C-STORE port).
        assert 'dicom_mwl_port' in default_config
        assert default_config['dicom_mwl_port'] == ''
        assert 'dicom_cmove_port' not in default_config

    def test_secret_falls_back_to_dev_default(self):
        cfg = load_config(overrides={'secret': 'default', 'db_password': 'pa55w0rd'})
        assert cfg['secret'] == 'quantumpacs-default-secret-32-bytes-long!!'

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
        from config import is_docker
        assert is_docker() is True

    def test_is_docker_false_by_default(self, monkeypatch):
        monkeypatch.delenv('QUANTUMPACS_DOCKER', raising=False)
        from config import is_docker
        assert is_docker() is False

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
