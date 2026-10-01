from typing import Callable, Generic, TypeVar
from mysql.connector.cursor import MySQLCursorDict
import inspect


T = TypeVar("T")


class PaginationRequest(Generic[T]):

    def __init__(
        self,
        callback: Callable[..., T]
    ):
        self.callback = callback

    def runCallback(
        self,
        cursor: MySQLCursorDict,
        user_id: int = None,
        limit: int = None,
        offset: int = None,
        **filters
    ) -> T:
        """
        Runs the wrapped callback, passing only the arguments it
        declares.

        A callback must accept cursor, limit and offset. Any further
        parameters it declares, such as user_id or a filter, are
        forwarded when supplied.
        """

        parameters = inspect.signature(self.callback).parameters

        required = {
            "cursor",
            "limit",
            "offset"
        }

        if not required.issubset(parameters):
            raise TypeError(
                "Callback must accept cursor, limit and offset."
            )

        available = {
            "cursor": cursor,
            "user_id": user_id,
            "limit": limit,
            "offset": offset,
            **filters
        }

        arguments = {
            name: value
            for name, value in available.items()
            if name in parameters
        }

        return self.callback(**arguments)
