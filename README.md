# SingleFlight

**SingleFlight** is a lightweight asynchronous Python utility that prevents duplicate concurrent operations.

When multiple callers request the same operation using the same key, only one operation is executed. All callers share the result of that operation.

## Features

- Deduplicates concurrent operations by key.
- Shares results between multiple callers.
- Propagates exceptions to all waiting callers.
- Protects shared operations from individual caller cancellation.
- Supports independent operations for different keys.
- Automatically cleans up completed operations.
- Built with Python's standard `asyncio` library.

## Requirements

- Python 3.13+

## Installation

The package is distributed as `ea-singleflight` and imported as `singleflight`.

Once published on PyPI, install it with:

```bash
pip install ea-singleflight
```

Until then, you can install it directly from GitHub:

```bash
pip install git+https://github.com/EmilAyupov/ea-singleflight.git
```

## Quick Start

```python
import asyncio

from singleflight import SingleFlight


async def fetch_user(user_id: int) -> dict:
    print(f"Fetching user {user_id}...")

    await asyncio.sleep(1)

    return {
        "id": user_id,
        "name": "Alice",
    }


async def main() -> None:
    group = SingleFlight()

    results = await asyncio.gather(
        group.do("user:123", lambda: fetch_user(123)),
        group.do("user:123", lambda: fetch_user(123)),
        group.do("user:123", lambda: fetch_user(123)),
    )

    print(results)


if __name__ == "__main__":
    asyncio.run(main())
```

Although three callers request the same operation, `fetch_user()` is executed only once.

All three callers receive the same result.

## How It Works

SingleFlight maintains a collection of in-flight operations indexed by string keys.

When `do()` is called:

1. If no operation exists for the given key, a new asynchronous task is created.
2. If an operation already exists, the caller joins the existing task.
3. All callers await the same task.
4. Once the operation completes and all waiting callers finish, the corresponding entry is removed.

Operations with different keys run independently.

## Cancellation Behavior

SingleFlight uses `asyncio.shield()` to protect shared tasks from cancellation initiated by individual callers.

If one caller is cancelled:

- That caller receives `asyncio.CancelledError`.
- The shared operation continues running.
- Other callers can still receive its result.

If all callers are cancelled, the shared operation continues running and can be joined by a new caller using the same key.

## Exception Handling

If the shared operation raises an exception, all waiting callers receive that exception.

Once the operation has completed and its callers have finished, the corresponding entry is removed.

A subsequent call using the same key starts a new operation.

## API

### `SingleFlight()`

Creates a new SingleFlight instance.

```python
group = SingleFlight()
```

### `await group.do(key, fn)`

Executes or joins an asynchronous operation associated with the given key.

**Parameters:**

| Parameter | Type       | Description                                  |
| --------- | ---------- | -------------------------------------------- |
| `key`     | `str`      | Identifier of the operation                  |
| `fn`      | `Callable` | Zero-argument function returning a coroutine |

**Returns:**

The result of the shared asynchronous operation.

**Raises:**

- `TypeError` if `fn` does not return a coroutine.
- Any exception raised by the shared operation.
- `asyncio.CancelledError` if the individual caller is cancelled or the shared task is cancelled.

## Limitations

- Keys must be strings.
- Only asynchronous functions returning coroutines are supported.
- Callers using the same key must expect compatible results.
- The first caller's function is used; subsequent functions for the same key are not executed.
- A SingleFlight instance is intended for use within a single asyncio event loop.
- The implementation is not thread-safe.

## Development

Clone the repository:

```bash
git clone https://github.com/EmilAyupov/ea-singleflight.git
cd ea-singleflight
```

Install dependencies:

```bash
uv sync --all-groups
```

Run checks:

```bash
./scripts/check.sh
```

The project uses:

- [Python](https://www.python.org/)
- [asyncio](https://docs.python.org/3/library/asyncio.html)
- [pytest](https://pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Ruff](https://docs.astral.sh/ruff/)
- [Pyrefly](https://pyrefly.org/)
- [uv](https://docs.astral.sh/uv/)

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
