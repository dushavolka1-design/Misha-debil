# Integrated build progress

```json
{
  "conclusion": "",
  "headSha": "11b8e167657739751358beceedfabfe7d40db71d",
  "jobs": [
    {
      "completedAt": "0001-01-01T00:00:00Z",
      "conclusion": "",
      "databaseId": 102198549947,
      "name": "integrated-windows",
      "startedAt": "2026-09-08T19:05:46Z",
      "status": "in_progress",
      "steps": [
        {
          "completedAt": "2026-09-08T19:05:48Z",
          "conclusion": "success",
          "name": "Set up job",
          "number": 1,
          "startedAt": "2026-09-08T19:05:47Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T19:05:54Z",
          "conclusion": "success",
          "name": "Run actions/checkout@v4",
          "number": 2,
          "startedAt": "2026-09-08T19:05:48Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T19:05:54Z",
          "conclusion": "success",
          "name": "Run actions/setup-python@v5",
          "number": 3,
          "startedAt": "2026-09-08T19:05:54Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T19:06:00Z",
          "conclusion": "success",
          "name": "Run actions/setup-node@v4",
          "number": 4,
          "startedAt": "2026-09-08T19:05:54Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T19:06:05Z",
          "conclusion": "success",
          "name": "Merge and verify every requested branch snapshot except main",
          "number": 5,
          "startedAt": "2026-09-08T19:06:00Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T19:06:11Z",
          "conclusion": "success",
          "name": "Validate installer scripts and launcher safety regressions",
          "number": 6,
          "startedAt": "2026-09-08T19:06:05Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T19:06:21Z",
          "conclusion": "success",
          "name": "Build integrated EXE",
          "number": 7,
          "startedAt": "2026-09-08T19:06:11Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T19:09:53Z",
          "conclusion": "success",
          "name": "Install, first launch, repeat launch, reinstall and uninstall",
          "number": 8,
          "startedAt": "2026-09-08T19:06:21Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T19:09:55Z",
          "conclusion": "success",
          "name": "Keep evidence",
          "number": 9,
          "startedAt": "2026-09-08T19:09:53Z",
          "status": "completed"
        },
        {
          "completedAt": "0001-01-01T00:00:00Z",
          "conclusion": "",
          "name": "Publish only tested integrated prerelease",
          "number": 10,
          "startedAt": "2026-09-08T19:09:55Z",
          "status": "in_progress"
        },
        {
          "completedAt": "0001-01-01T00:00:00Z",
          "conclusion": "",
          "name": "Persist continuation checkpoint and failure evidence",
          "number": 11,
          "startedAt": "0001-01-01T00:00:00Z",
          "status": "pending"
        },
        {
          "completedAt": "0001-01-01T00:00:00Z",
          "conclusion": "",
          "name": "Post Run actions/setup-node@v4",
          "number": 20,
          "startedAt": "0001-01-01T00:00:00Z",
          "status": "pending"
        },
        {
          "completedAt": "0001-01-01T00:00:00Z",
          "conclusion": "",
          "name": "Post Run actions/setup-python@v5",
          "number": 21,
          "startedAt": "0001-01-01T00:00:00Z",
          "status": "pending"
        },
        {
          "completedAt": "0001-01-01T00:00:00Z",
          "conclusion": "",
          "name": "Post Run actions/checkout@v4",
          "number": 22,
          "startedAt": "0001-01-01T00:00:00Z",
          "status": "pending"
        }
      ],
      "url": "https://github.com/dushavolka1-design/Misha-debil/actions/runs/34266940257/job/102198549947"
    }
  ],
  "status": "in_progress",
  "url": "https://github.com/dushavolka1-design/Misha-debil/actions/runs/34266940257"
}
```
