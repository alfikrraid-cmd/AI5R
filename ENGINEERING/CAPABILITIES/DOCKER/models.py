SUPPORTED_OPERATIONS = {
    "GET_VERSION",
    "LIST_CONTAINERS",
    "LIST_IMAGES",
}

OPERATION_MAP = {
    "GET_VERSION": ["docker", "--version"],
    "LIST_CONTAINERS": ["docker", "ps"],
    "LIST_IMAGES": ["docker", "images"],
}
