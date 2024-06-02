class RemoteResourceException(Exception):
    message: str

    def __init__(self, resource: str, details: str):
        self.message = f"Cannot fetch remote resource {resource}: {details}."

    def __str__(self):
        return self.message
