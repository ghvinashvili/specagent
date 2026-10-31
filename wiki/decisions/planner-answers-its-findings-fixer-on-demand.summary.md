Decision (owner, 2026-10-30): the planner answers its own findings; the fixer is launched on demand.
After every part it writes, the planner answers the open ids of its own tasks found by open_ids.py --cause plan.
The watcher launches the plan fixer only when its open ids reach demand.queue (6) or the oldest is wait_minutes (45) old.
It stops the fixer when the queue is empty and never revives it; the manager never launches it at the start.
