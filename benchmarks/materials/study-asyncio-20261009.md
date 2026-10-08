# NEKO-LAB-20261009B Python asyncio 复习提纲（编程 / 异步编程）

## 1. 事件循环
asyncio 的核心是事件循环（event loop）：单线程调度大量协程任务，
协程在 await 点让出控制权，循环切换到其他就绪任务。

## 2. 协程与 await
- `async def foo(): ...` 定义协程函数；调用它返回协程对象，不执行。
- `await foo()` 才真正调度执行，并在等待期间允许其他任务运行。

## 3. 并发执行：asyncio.gather
`results = await asyncio.gather(task_a(), task_b(), task_c())`
三个 I/O 任务并发执行，总耗时≈最慢者，而不是三者之和。
`return_exceptions=True` 时，异常作为结果返回而不是立即抛出。

## 4. 常见误区：阻塞调用冻结整个循环
在协程里使用 `time.sleep(3)` 是常见错误：它是同步阻塞调用，
会冻结整个事件循环 3 秒，所有其他协程都动不了。
正确写法是 `await asyncio.sleep(3)`：非阻塞，让出控制权。

## 5. 检查清单
① 有没有把同步阻塞调用（time.sleep、requests、重 CPU 计算）混进协程？
② 并发任务是否用 gather/create_task 组织？
③ 异常处理策略是否明确（return_exceptions 与否）？
