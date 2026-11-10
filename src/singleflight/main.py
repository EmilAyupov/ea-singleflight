import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any, TypeVar, cast

T = TypeVar("T")


@dataclass
class Flight[T]:
    task: asyncio.Task[T]
    waiters: int = 0


class SingleFlight:
    def __init__(self) -> None:
        self._flights: dict[str, Flight[Any]] = {}
        self._lock = asyncio.Lock()

    async def do(
        self,
        key: str,
        fn: Callable[[], Coroutine[Any, Any, T]],
    ) -> T:
        async with self._lock:
            flight = self._flights.get(key)

            if flight is None:
                task = asyncio.create_task(fn())
                flight = Flight(task=task)
                self._flights[key] = flight

                task.add_done_callback(lambda _: self._on_task_done(key, flight))

            flight.waiters += 1

        try:
            result = await asyncio.shield(flight.task)
            return cast(T, result)
        finally:
            flight.waiters -= 1
            self._cleanup(key, flight)

    def _cleanup(self, key: str, flight: Flight[Any]) -> None:
        if (
            self._flights.get(key) is flight
            and flight.task.done()
            and flight.waiters == 0
        ):
            del self._flights[key]

    def _on_task_done(self, key: str, flight: Flight["Any"]) -> None:
        if not flight.task.cancelled():
            flight.task.exception()

        self._cleanup(key, flight)
