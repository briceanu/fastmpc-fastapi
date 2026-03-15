import logging

logger = logging.getLogger(name='mcp_logger')

COLORS = {
    "INFO": "\033[92m",    # Green
    "WARNING": "\033[93m",  # Yellow
    "ERROR": "\033[91m",   # Red
    "DEBUG": "\033[94m",   # Blue
    "RESET": "\033[0m"     # Reset color
}


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        color = COLORS.get(record.levelname, COLORS["RESET"])
        message = super().format(record)
        return f"{color}{message}{COLORS['RESET']}"


logger.setLevel(level='INFO')

formatter = ColoredFormatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
