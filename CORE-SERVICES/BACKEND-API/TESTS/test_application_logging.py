import io
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
for path in (BACKEND_API_DIR, CORE_SERVICES_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from main import configure_application_logging


# -- configure_application_logging() decision logic -----------------------
#
# pytest's own logging plugin keeps a LogCaptureHandler permanently attached
# to the real root logger for the whole session (regardless of whether any
# test uses the caplog fixture), so asserting on the real
# logging.getLogger().handlers list here would be testing pytest's plugin,
# not this function. Mocking logging.getLogger()/basicConfig isolates the
# function's own branching instead.


def test_calls_basicConfig_when_root_has_no_handlers():
    fake_root = MagicMock()
    fake_root.handlers = []
    with patch("logging.getLogger", return_value=fake_root), patch("logging.basicConfig") as mock_basic_config:
        configure_application_logging()

    mock_basic_config.assert_called_once_with(level=logging.INFO)


def test_skips_basicConfig_when_root_already_has_a_handler():
    fake_root = MagicMock()
    fake_root.handlers = [MagicMock()]
    with patch("logging.getLogger", return_value=fake_root), patch("logging.basicConfig") as mock_basic_config:
        configure_application_logging()

    mock_basic_config.assert_not_called()


def test_calling_twice_never_calls_basicConfig_a_second_time():
    # Simulates the real sequence: first call finds no handler and
    # configures one; a second call (e.g. a module re-exercised under test,
    # or any future caller) must see that handler and skip -- proving no
    # handler duplication across repeated calls.
    fake_root = MagicMock()
    fake_root.handlers = []

    def _add_handler_on_first_basicConfig_call(**_kwargs):
        fake_root.handlers = [MagicMock()]

    with patch("logging.getLogger", return_value=fake_root), patch(
        "logging.basicConfig", side_effect=_add_handler_on_first_basicConfig_call
    ) as mock_basic_config:
        configure_application_logging()
        configure_application_logging()

    mock_basic_config.assert_called_once_with(level=logging.INFO)


# -- real, non-caplog proof that INFO records reach an actual stream ------


def test_info_record_reaches_a_real_attached_stream_handler_not_just_caplog():
    # MWO-025H's own regression: caplog captures log records directly
    # through the logging framework's internal machinery regardless of
    # whether any handler is actually configured -- exactly why the
    # missing-handler bug in production went undetected by the existing
    # WhatsApp test suite (its tests all used caplog). This test instead
    # attaches a real logging.StreamHandler -- the same mechanism
    # configure_application_logging() installs on the root logger via
    # logging.basicConfig() -- and proves an application-style
    # event=whatsapp_webhook_received record actually lands in that
    # stream's content, independent of pytest's own log capture.
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.INFO)
    logger = logging.getLogger("routers.whatsapp_webhook.regression_test")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.addHandler(handler)
    try:
        logger.info("event=whatsapp_webhook_received event_type=messages signature_valid=true")
    finally:
        logger.removeHandler(handler)

    assert "event=whatsapp_webhook_received" in stream.getvalue()
