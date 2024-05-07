class ConnectionError(Exception):
    """Exception raised for errors in the connection.

    Attributes:
        uuid -- uuid of the vehicle which caused the error
        message -- explanation of the error
    """

    def __init__(self, uuid, message="Failed to connect to vehicle"):
        self.uuid = uuid
        self.message = message + f" with UUID {uuid}"
        super().__init__(self.message)