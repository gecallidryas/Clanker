import asyncio
import unittest

from utils.persona_queue import PersonaInvocationJob, PersonaQueueAbortedError, PersonaQueueManager


class PersonaQueueManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_job_aborts_remaining_jobs_and_clears_queue(self) -> None:
        queue = PersonaQueueManager()

        async def runner(job: PersonaInvocationJob) -> None:
            if job.mode_key == "mode_first":
                raise RuntimeError("boom")

        loop = asyncio.get_running_loop()
        first_future = loop.create_future()
        second_future = loop.create_future()

        await queue.enqueue(
            123,
            PersonaInvocationJob(mode_key="mode_first", completion_future=first_future),
        )
        await queue.enqueue(
            123,
            PersonaInvocationJob(mode_key="mode_second", completion_future=second_future),
        )

        task = queue.schedule_drain(123, runner)
        self.assertIsNotNone(task)

        with self.assertRaises(RuntimeError):
            await task

        with self.assertRaises(RuntimeError):
            await first_future
        with self.assertRaises(PersonaQueueAbortedError):
            await second_future
        self.assertIsNone(queue._queues.get(123))
        self.assertNotIn(123, queue._tasks)


if __name__ == "__main__":
    unittest.main()
