from __future__ import annotations

import logging
import uuid
from typing import Callable, Dict

import dash
from dash import (
    Output,
    html,
)
from dash._callback_context import _get_context_value, has_context
from dash._utils import stringify_id

from dash_extensions.utils import DashNode, as_list


@has_context
def set_props(component_id: str | dict, props: dict, append: bool = False) -> None:
    """
    In the current (upstream) implementation of Dash, the "set_props" function overrides the value on each call,
    effectively leaving only the last value in the updated_props dictionary. This implementation allows for *appending*.
    """
    ctx_value = _get_context_value()
    _id = stringify_id(component_id)
    if not append or _id not in ctx_value.updated_props:
        ctx_value.updated_props[_id] = props
        return
    updated_props = dict(ctx_value.updated_props[_id]) if _id in ctx_value.updated_props else {}
    for key in props:
        if key not in updated_props:
            updated_props[key] = props[key]
            continue
        updated = as_list(updated_props[key])
        updated.append(props[key])
        updated_props[key] = updated
    ctx_value.updated_props[_id] = updated_props


class DashLogHandler(logging.Handler):
    """
    DashLogHandler is a logging handler that writes log messages to a Dash component. It fits inside the existing
    logging framework of Python, while providing the ability to update Dash UI components.
    """

    def __init__(
        self, output: Output, log_writers: Dict[int, Callable], layout: DashNode | None = None, level=logging.DEBUG
    ):
        self.output = output
        self.log_writers = log_writers
        self.layout = layout
        # Per default set the level to DEBUG (i.e. log it all).
        logging.Handler.__init__(self=self, level=level)

    def emit(self, record):
        """
        The emit method calls set_props to update the (Dash) log output component when logs are written.
        """
        # If we are in a Dash callback context, we update the log output.
        try:
            if record.levelno in self.log_writers:
                msg = self.log_writers[record.levelno](record.getMessage())
                set_props(self.output.component_id, {self.output.component_property: msg}, append=True)
        # If we are not in a Dash callback context, we the log invocation.
        except dash.exceptions.MissingCallbackContextException:
            pass

    def embed(self) -> DashNode | None:
        """
        Return any components that should be embedded in the app layout.
        """
        if self.layout is None:
            return []
        return self.layout

    def setup_logger(self, logger_name: str = "dash_extensions", level: int = logging.DEBUG) -> logging.Logger:
        """
        Convenience method to set up a logger with this handler.
        """
        logger = logging.getLogger(logger_name)
        logger.addHandler(self)
        logger.setLevel(level)
        return logger


def get_default_log_writers() -> dict[int, Callable]:
    """
    Simplest possible log writers for INFO, WARNING, and ERROR messages.
    """
    return {
        logging.INFO: lambda x, **kwargs: html.Div(f"INFO: {x}", **kwargs),
        logging.WARNING: lambda x, **kwargs: html.Div(f"WARNING: {x}", **kwargs),
        logging.ERROR: lambda x, **kwargs: html.Div(f"ERROR: {x}", **kwargs),
    }


class DivLogHandler(DashLogHandler):
    """
    Simplest possible DashLogHandler. Just writes log messages to a Div component.
    """

    def __init__(self, log_div: DashNode | None = None) -> None:
        log_div = html.Div(id="log_id") if log_div is None else log_div
        super().__init__(output=Output(log_div, "children"), log_writers=get_default_log_writers(), layout=log_div)


def get_notification_log_writers() -> dict[int, Callable]:
    """
    Log writers that target the Notification component from dash_mantine_components.
    """
    import dash_mantine_components as dmc

    def _default_kwargs(color, title, message):
        return dict(
            color=color,
            title=title,
            message=message,
            id=str(uuid.uuid4()),
            action="show",
            autoClose=False,
        )

    def log_info(message, **kwargs):
        return dmc.Notification(**{**_default_kwargs("blue", "Info", message), **kwargs})

    def log_warning(message, **kwargs):
        return dmc.Notification(**{**_default_kwargs("yellow", "Warning", message), **kwargs})

    def log_error(message, **kwargs):
        return dmc.Notification(**{**_default_kwargs("red", "Error", message), **kwargs})

    return {
        logging.INFO: log_info,
        logging.WARNING: log_warning,
        logging.ERROR: log_error,
    }


class NotificationsLogHandler(DashLogHandler):
    """
    Dash log handler that displays the logs as notifications using dash_mantine_components.
    """

    def __init__(self, log_div: DashNode | None = None, notifications_provider: DashNode | None = None) -> None:
        log_div = html.Div(id="log_id") if log_div is None else log_div
        if notifications_provider is None:
            import dash_mantine_components as dmc

            notifications_provider = (
                dmc.NotificationsProvider() if dmc.__version__ < "0.14.0" else dmc.NotificationProvider()  # type: ignore
            )
        super().__init__(
            output=Output(log_div, "children"),
            log_writers=get_notification_log_writers(),
            layout=html.Div([notifications_provider, log_div]),  # type: ignore
        )
