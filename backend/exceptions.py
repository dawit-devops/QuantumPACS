class ApiException(Exception):
    def __init__(self, message='', status_code=400, error_code='API_ERROR'):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


class ConfigurationError(Exception):
    pass
