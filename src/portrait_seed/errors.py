class PipelineError(Exception):
    """A safe error code, not an upstream exception body or camera content."""


class CloudError(PipelineError):
    def __init__(self, code, retryable=False):
        super().__init__(code)
        self.retryable = retryable

