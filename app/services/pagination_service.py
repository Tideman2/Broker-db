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
        user_id: int,
        limit: int,
        offset: int
    ) -> T:

        args_length = len(
            inspect.signature(self.callback).parameters
        )

        if args_length == 3:
            return self.callback(
                cursor,
                limit,
                offset
            )

        if args_length == 4:
            return self.callback(
                cursor,
                user_id,
                limit,
                offset
            )

        raise TypeError(
            "Callback must accept either 3 or 4 arguments."
        )
