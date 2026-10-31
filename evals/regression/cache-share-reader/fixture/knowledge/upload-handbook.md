# Upload client handbook

This handbook is the project's standing knowledge for anyone who reads material about the upload client. It defines the words the project uses and the conventions of its notes. It does not restate the retry policy: the policy has its own source.

## Vocabulary

### As the storage team uses the words

- **upload**: one attempt to send one file to the storage service, from the first byte to the final status. The storage team writes this word in lower case and does not abbreviate it.
- **part**: a slice of a file that is sent as its own request when the file is larger than the split limit. The storage team writes this word in lower case and does not abbreviate it.
- **retry**: a new attempt for the same upload or the same part after a failed one. The storage team writes this word in lower case and does not abbreviate it.
- **wait**: the pause between a failed attempt and the retry that follows it. The storage team writes this word in lower case and does not abbreviate it.
- **final failure**: the state of an upload whose last permitted retry has failed. The storage team writes this word in lower case and does not abbreviate it.
- **client**: the program that sends files; the policy in this project is written for it and not for the service. The storage team writes this word in lower case and does not abbreviate it.
- **status**: the three-digit code the service returns for a request. The storage team writes this word in lower case and does not abbreviate it.
- **permanent status**: a status that will be the same on every later attempt. The storage team writes this word in lower case and does not abbreviate it.
- **transient status**: a status that can change on a later attempt without any change on the client's side. The storage team writes this word in lower case and does not abbreviate it.
- **log entry**: one line written to a log file by the client. The storage team writes this word in lower case and does not abbreviate it.
- **version**: the release number of the client in the form major.minor. The storage team writes this word in lower case and does not abbreviate it.
- **split limit**: the file size above which a file is sent in parts. The storage team writes this word in lower case and does not abbreviate it.

### As the desktop team uses the words

- **upload**: one attempt to send one file to the storage service, from the first byte to the final status. The desktop team writes this word in lower case and does not abbreviate it.
- **part**: a slice of a file that is sent as its own request when the file is larger than the split limit. The desktop team writes this word in lower case and does not abbreviate it.
- **retry**: a new attempt for the same upload or the same part after a failed one. The desktop team writes this word in lower case and does not abbreviate it.
- **wait**: the pause between a failed attempt and the retry that follows it. The desktop team writes this word in lower case and does not abbreviate it.
- **final failure**: the state of an upload whose last permitted retry has failed. The desktop team writes this word in lower case and does not abbreviate it.
- **client**: the program that sends files; the policy in this project is written for it and not for the service. The desktop team writes this word in lower case and does not abbreviate it.
- **status**: the three-digit code the service returns for a request. The desktop team writes this word in lower case and does not abbreviate it.
- **permanent status**: a status that will be the same on every later attempt. The desktop team writes this word in lower case and does not abbreviate it.
- **transient status**: a status that can change on a later attempt without any change on the client's side. The desktop team writes this word in lower case and does not abbreviate it.
- **log entry**: one line written to a log file by the client. The desktop team writes this word in lower case and does not abbreviate it.
- **version**: the release number of the client in the form major.minor. The desktop team writes this word in lower case and does not abbreviate it.
- **split limit**: the file size above which a file is sent in parts. The desktop team writes this word in lower case and does not abbreviate it.

### As the mobile team uses the words

- **upload**: one attempt to send one file to the storage service, from the first byte to the final status. The mobile team writes this word in lower case and does not abbreviate it.
- **part**: a slice of a file that is sent as its own request when the file is larger than the split limit. The mobile team writes this word in lower case and does not abbreviate it.
- **retry**: a new attempt for the same upload or the same part after a failed one. The mobile team writes this word in lower case and does not abbreviate it.
- **wait**: the pause between a failed attempt and the retry that follows it. The mobile team writes this word in lower case and does not abbreviate it.
- **final failure**: the state of an upload whose last permitted retry has failed. The mobile team writes this word in lower case and does not abbreviate it.
- **client**: the program that sends files; the policy in this project is written for it and not for the service. The mobile team writes this word in lower case and does not abbreviate it.
- **status**: the three-digit code the service returns for a request. The mobile team writes this word in lower case and does not abbreviate it.
- **permanent status**: a status that will be the same on every later attempt. The mobile team writes this word in lower case and does not abbreviate it.
- **transient status**: a status that can change on a later attempt without any change on the client's side. The mobile team writes this word in lower case and does not abbreviate it.
- **log entry**: one line written to a log file by the client. The mobile team writes this word in lower case and does not abbreviate it.
- **version**: the release number of the client in the form major.minor. The mobile team writes this word in lower case and does not abbreviate it.
- **split limit**: the file size above which a file is sent in parts. The mobile team writes this word in lower case and does not abbreviate it.

### As the support team uses the words

- **upload**: one attempt to send one file to the storage service, from the first byte to the final status. The support team writes this word in lower case and does not abbreviate it.
- **part**: a slice of a file that is sent as its own request when the file is larger than the split limit. The support team writes this word in lower case and does not abbreviate it.
- **retry**: a new attempt for the same upload or the same part after a failed one. The support team writes this word in lower case and does not abbreviate it.
- **wait**: the pause between a failed attempt and the retry that follows it. The support team writes this word in lower case and does not abbreviate it.
- **final failure**: the state of an upload whose last permitted retry has failed. The support team writes this word in lower case and does not abbreviate it.
- **client**: the program that sends files; the policy in this project is written for it and not for the service. The support team writes this word in lower case and does not abbreviate it.
- **status**: the three-digit code the service returns for a request. The support team writes this word in lower case and does not abbreviate it.
- **permanent status**: a status that will be the same on every later attempt. The support team writes this word in lower case and does not abbreviate it.
- **transient status**: a status that can change on a later attempt without any change on the client's side. The support team writes this word in lower case and does not abbreviate it.
- **log entry**: one line written to a log file by the client. The support team writes this word in lower case and does not abbreviate it.
- **version**: the release number of the client in the form major.minor. The support team writes this word in lower case and does not abbreviate it.
- **split limit**: the file size above which a file is sent in parts. The support team writes this word in lower case and does not abbreviate it.

## Conventions of the notes

1. A note names its source by path and line, and gives the source's own words in double quotes.
2. A number is copied with its unit exactly as the source writes it: `two seconds` stays `two seconds`.
3. A word that limits a statement (`at most`, `always`, `never`, `before any`) belongs to the quote and is never dropped.
4. Two statements that could disagree are listed side by side; choosing between them is not the reader's task.
5. What the source does not say is a question, and the question names what a later reader would need to know.
6. The name of a file or a log is copied character by character, including its extension.
7. A statement about a version stays attached to the sentence that carries the version.
8. The order of the notes follows the order of the source.

## Release history of the client

| Version | What changed |
| --- | --- |
| 1.0 | the client sent every file in one request and did not retry |
| 1.1 | files above the split limit were sent in parts |
| 1.2 | the client began to write failed file names to a log |
| 1.3 | the status of every response was recorded with the request |
| 1.4 | the retry policy was introduced |

## What this handbook is not

It is not a source for notes. A fact about the retry policy is taken from the material the brief names, with its path and line.
