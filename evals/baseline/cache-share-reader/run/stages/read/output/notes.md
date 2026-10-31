# Notes on context/sample.txt

## Header
| Source | Kind | Size |
| --- | --- | --- |
| context/sample.txt | the only source | 9 lines |

## context/sample.txt
- The file is about the retry policy of the upload client. Quote: "Retry policy for the upload client." `context/sample.txt:1`
- A failed upload is retried at most three times. Quote: "A failed upload is retried at most three times." `context/sample.txt:2`
- The first retry waits two seconds. Quote: "The wait before the first retry is two seconds." `context/sample.txt:3`
- Every later wait doubles. Quote: "Each later wait is twice the previous one." `context/sample.txt:4`
- Status 400 is never retried. Quote: "A response with status 400 is never retried." `context/sample.txt:5`
- Status 503 is always retried. Quote: "A response with status 503 is always retried." `context/sample.txt:6`
- A file whose last retry fails is logged. Quote: "After the last retry fails, the file name is written to failed.log." `context/sample.txt:7`
- The policy dates from version 1.4. Quote: "The policy was introduced in version 1.4." `context/sample.txt:8`
- Large uploads are split first. Quote: "Uploads larger than 2 GB are split before any retry logic applies." `context/sample.txt:9`

## Contradictions
none

## Coverage
| Source | Coverage |
| --- | --- |
| context/sample.txt | read completely |
