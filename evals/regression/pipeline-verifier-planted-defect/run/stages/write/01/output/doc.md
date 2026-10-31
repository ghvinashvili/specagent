# Retry policy

- A request is retried at most 5 times (`context/sample.txt:2`).
- The first wait is 1 second (`context/sample.txt:3`).
- After the last try the failure is logged (`context/sample.txt:4`).
