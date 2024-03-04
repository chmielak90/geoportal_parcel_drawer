class PathNotFoundError(Exception):
    def __init__(self, path_error, message="Path not found"):
        self.path_error = path_error
        self.message = message
        super().__init__(f"{self.message}: '{self.path_error}'")


class WrongZoneError(Exception):
    def __init__(self, identifier, message="Wrong zone"):
        self.path_error = identifier
        self.message = message
        super().__init__(f"Identifier: ${identifier} are from different zone then others.")
