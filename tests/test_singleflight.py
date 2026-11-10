import asyncio

import pytest

# from devtools import debug
from singleflight import SingleFlight


@pytest.mark.asyncio
async def test_same_key_shares_one_task() -> None:
    group = SingleFlight()
    calls = 0

    async def operation() -> str:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return "result"

    # Здесь запустим два параллельных вызова
    group1 = group.do("user:123", operation)
    group2 = group.do("user:123", operation)
    all_result = await asyncio.gather(group1, group2)

    # Здесь проверим результаты и количество запусков
    assert calls == 1
    assert all_result == ["result", "result"]


@pytest.mark.asyncio
async def test_cancelling_one_waiter_does_not_cancel_task() -> None:
    group = SingleFlight()
    started = asyncio.Event()
    finish = asyncio.Event()
    calls = 0

    async def operation() -> str:
        nonlocal calls
        calls += 1
        started.set()
        await finish.wait()
        return "result"

    # Запускаем первого ожидающего
    task1 = asyncio.create_task(group.do("user:123", operation))

    # Ждём, пока operation действительно начнётся
    await started.wait()

    # Запускаем второго ожидающего
    task2 = asyncio.create_task(group.do("user:123", operation))

    # Даём event loop возможность запустить task2
    await asyncio.sleep(0)

    # Отменяем только первого ожидающего
    task1.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task1

    # Разрешаем общей operation завершиться
    finish.set()

    # Второй ожидающий должен получить результат
    result = await task2

    assert result == "result"
    assert calls == 1


@pytest.mark.asyncio
async def test_exception_after_all_waiters_cancelled() -> None:
    group = SingleFlight()
    started = asyncio.Event()
    finish = asyncio.Event()
    finished = asyncio.Event()
    calls = 0

    async def operation() -> str:
        nonlocal calls
        calls += 1
        started.set()

        try:
            await finish.wait()
            raise RuntimeError("operation failed")
        finally:
            finished.set()

    # Здесь запускаем двух ожидающих
    task1 = asyncio.create_task(group.do("user:123", operation))
    task2 = asyncio.create_task(group.do("user:123", operation))

    # Ждём начала операции и присоединения второго
    await started.wait()
    await asyncio.sleep(0)

    # Отменяем обоих ожидающих
    task1.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task1

    task2.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task2

    # Разрешаем общей операции завершиться
    finish.set()
    await finished.wait()
    await asyncio.sleep(0)

    # Проверяем очистку
    assert calls == 1
    assert group._flights == {}


@pytest.mark.asyncio
async def test_exception_is_shared_between_waiters() -> None:
    group = SingleFlight()
    started = asyncio.Event()
    finish = asyncio.Event()
    calls = 0

    async def operation() -> str:
        nonlocal calls
        calls += 1
        started.set()
        await finish.wait()
        raise RuntimeError("operation failed")

    # Запустить двух ожидающих
    task1 = asyncio.create_task(group.do("user:123", operation))
    task2 = asyncio.create_task(group.do("user:123", operation))

    # Дождаться присоединения обоих
    await started.wait()
    await asyncio.sleep(0)

    # Разрешаем общей операции завершиться
    finish.set()

    # Получаем результаты обеих задач
    results = await asyncio.gather(
        task1,
        task2,
        return_exceptions=True,
    )

    # Проверяем исключения
    assert all(isinstance(result, RuntimeError) for result in results)

    assert all(str(result) == "operation failed" for result in results)

    # Проверяем calls и очистку
    assert calls == 1

    await asyncio.sleep(0)
    assert group._flights == {}


@pytest.mark.asyncio
async def test_different_keys_run_independently() -> None:
    group = SingleFlight()
    calls = 0

    async def operation() -> str:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return "result"

    # Здесь запустим два параллельных вызова
    group1 = group.do("user:123", operation)
    group2 = group.do("user:456", operation)
    all_result = await asyncio.gather(group1, group2)

    # Здесь проверим результаты и количество запусков
    assert calls == 2
    assert all_result == ["result", "result"]


@pytest.mark.asyncio
async def test_slow_key_does_not_block_another_key() -> None:
    group = SingleFlight()

    first_started = asyncio.Event()
    second_started = asyncio.Event()
    finish_first = asyncio.Event()

    async def slow_operation() -> str:
        first_started.set()
        await finish_first.wait()
        return "first"

    async def fast_operation() -> str:
        second_started.set()
        return "second"

    # Запускаем первую операцию
    # Ждём её начала
    task1 = asyncio.create_task(group.do("user:123", slow_operation))
    await first_started.wait()

    # Запускаем вторую операцию
    task2 = asyncio.create_task(group.do("user:456", fast_operation))

    # Проверяем, что вторая началась,
    # хотя первая ещё не завершилась
    await asyncio.wait_for(
        second_started.wait(),
        timeout=1,
    )

    # Завершаем первую операцию
    finish_first.set()
    # Проверяем оба результата
    results = await asyncio.gather(task1, task2)

    assert results == ["first", "second"]


@pytest.mark.asyncio
async def test_rejoining_client_with_same_key_receives_original_result_without_restart() -> (
    None
):
    group = SingleFlight()
    calls = 0

    started = asyncio.Event()
    finish = asyncio.Event()

    async def operation() -> str:
        nonlocal calls
        calls += 1
        started.set()
        await finish.wait()
        return "result"

    async def wait_for_waiters(count: int) -> None:
        while group._flights["user:123"].waiters != count:
            await asyncio.sleep(0)

    task1 = asyncio.create_task(group.do("user:123", operation))
    await started.wait()

    task2 = asyncio.create_task(group.do("user:123", operation))
    await wait_for_waiters(2)

    task1.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task1
    task2.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task2

    task3 = asyncio.create_task(group.do("user:123", operation))
    await asyncio.sleep(0)

    finish.set()
    result = await task3

    assert result == "result"
    assert calls == 1
