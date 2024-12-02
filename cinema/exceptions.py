class RemoteResourceException(Exception):
    message: str

    def __init__(self, resource: str, details: str):
        self.message = f"Cannot fetch remote resource {resource}: {details}."

    def __str__(self):
        return self.message


class GeckoDriverNotFound(Exception):
    message: str = (
        "Gecko driver not found, please download it from https://github.com/mozilla/geckodriver/releases "
        "and place it in the cinema code folder."
    )

    def __str__(self):
        return self.message
