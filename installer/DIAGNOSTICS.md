# Installer diagnostic checkpoint

## Run 34258269841

```json
{
  "conclusion": "failure",
  "headSha": "cc539e25d14c48f0896756d8b2711f7df29cba8a",
  "jobs": [
    {
      "completedAt": "2026-09-08T17:43:19Z",
      "conclusion": "failure",
      "databaseId": 102169514657,
      "name": "installer",
      "startedAt": "2026-09-08T17:38:03Z",
      "status": "completed",
      "steps": [
        {
          "completedAt": "2026-09-08T17:38:06Z",
          "conclusion": "success",
          "name": "Set up job",
          "number": 1,
          "startedAt": "2026-09-08T17:38:04Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:38:10Z",
          "conclusion": "success",
          "name": "Run actions/checkout@v4",
          "number": 2,
          "startedAt": "2026-09-08T17:38:06Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:38:38Z",
          "conclusion": "success",
          "name": "Run actions/setup-node@v4",
          "number": 3,
          "startedAt": "2026-09-08T17:38:10Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:38:38Z",
          "conclusion": "success",
          "name": "Run actions/setup-python@v5",
          "number": 4,
          "startedAt": "2026-09-08T17:38:38Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:38:41Z",
          "conclusion": "success",
          "name": "Validate PowerShell syntax",
          "number": 5,
          "startedAt": "2026-09-08T17:38:38Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:38:50Z",
          "conclusion": "success",
          "name": "Build EXE",
          "number": 6,
          "startedAt": "2026-09-08T17:38:41Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:42:48Z",
          "conclusion": "failure",
          "name": "Install, bootstrap, launch twice, reinstall and uninstall",
          "number": 7,
          "startedAt": "2026-09-08T17:38:50Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:42:49Z",
          "conclusion": "success",
          "name": "Keep build and test evidence (not a release on failure)",
          "number": 8,
          "startedAt": "2026-09-08T17:42:48Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:42:49Z",
          "conclusion": "skipped",
          "name": "Publish smoke-tested prerelease",
          "number": 9,
          "startedAt": "2026-09-08T17:42:49Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:43:17Z",
          "conclusion": "success",
          "name": "Persist CI checkpoint to working branch",
          "number": 10,
          "startedAt": "2026-09-08T17:42:49Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:43:17Z",
          "conclusion": "skipped",
          "name": "Post Run actions/setup-python@v5",
          "number": 18,
          "startedAt": "2026-09-08T17:43:17Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:43:17Z",
          "conclusion": "skipped",
          "name": "Post Run actions/setup-node@v4",
          "number": 19,
          "startedAt": "2026-09-08T17:43:17Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:43:18Z",
          "conclusion": "success",
          "name": "Post Run actions/checkout@v4",
          "number": 20,
          "startedAt": "2026-09-08T17:43:17Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:43:18Z",
          "conclusion": "success",
          "name": "Complete job",
          "number": 21,
          "startedAt": "2026-09-08T17:43:18Z",
          "status": "completed"
        }
      ],
      "url": "https://github.com/dushavolka1-design/Misha-debil/actions/runs/34258269841/job/102169514657"
    }
  ],
  "status": "completed",
  "url": "https://github.com/dushavolka1-design/Misha-debil/actions/runs/34258269841"
}
```

```text
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:07.4421221Z Progress: resolved 510, reused 0, downloaded 330, added 315
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:08.4420492Z Progress: resolved 510, reused 0, downloaded 347, added 332
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:09.4458018Z Progress: resolved 510, reused 0, downloaded 362, added 346
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:10.4568671Z Progress: resolved 510, reused 0, downloaded 365, added 351
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:11.4573058Z Progress: resolved 510, reused 0, downloaded 375, added 360
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:12.4573933Z Progress: resolved 510, reused 0, downloaded 380, added 364
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:13.4771686Z Progress: resolved 510, reused 0, downloaded 381, added 364
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:14.4753664Z Progress: resolved 510, reused 0, downloaded 396, added 378
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:15.4765645Z Progress: resolved 510, reused 0, downloaded 415, added 398
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:18.0517602Z Progress: resolved 510, reused 0, downloaded 416, added 398
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:19.0519966Z Progress: resolved 510, reused 0, downloaded 443, added 430
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:20.0555495Z Progress: resolved 510, reused 0, downloaded 468, added 454
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:21.0576622Z Progress: resolved 510, reused 0, downloaded 491, added 476
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:21.7641533Z Progress: resolved 510, reused 0, downloaded 510, added 510, done
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:23.3779330Z .../node_modules/unrs-resolver postinstall$ node postinstall.js
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:23.3787008Z .../sharp@0.34.5/node_modules/sharp install$ node install/check.js || npm run build
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:23.3868957Z .../esbuild@0.28.2/node_modules/esbuild postinstall$ node install.js
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:23.4007933Z .../esbuild@0.25.12/node_modules/esbuild postinstall$ node install.js
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:23.5090976Z .../sharp@0.34.5/node_modules/sharp install: Done
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:23.7227805Z .../esbuild@0.25.12/node_modules/esbuild postinstall: Done
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:23.7235451Z .../esbuild@0.28.2/node_modules/esbuild postinstall: Done
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:24.4940571Z .../node_modules/unrs-resolver postinstall: Done
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:24.7091002Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:24.7091515Z devDependencies:
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:24.7091806Z + prettier 3.9.6
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:24.7092010Z + turbo 2.10.9
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:24.7092227Z + typescript 5.9.3
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:24.7092370Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:24.7749444Z Done in 1m 10.4s using pnpm v9.15.9
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:25.2967045Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:25.2967851Z > @dar/web@0.2.0 build C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\web
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:25.2968310Z > next build
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:25.2968440Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:26.4056103Z ⚠ No build cache found. Please configure build caching for faster rebuilds. Read more: https://nextjs.org/docs/messages/no-cache
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:26.4182801Z Attention: Next.js now collects completely anonymous telemetry regarding usage.
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:26.4183652Z This information is used to shape Next.js' roadmap and prioritize features.
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:26.4184443Z You can learn more, including how to opt-out if you'd not like to participate in this anonymous program, by visiting the following URL:
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:26.4185009Z https://nextjs.org/telemetry
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:26.4185177Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:26.5241465Z    ▲ Next.js 15.5.23
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:26.5242068Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:26.5754807Z    Creating an optimized production build ...
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:38.4937733Z  ✓ Compiled successfully in 8.2s
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:38.4987270Z    Skipping linting
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:38.4989422Z    Checking validity of types ...
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:43.1007512Z    Collecting page data ...
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:45.0114487Z    Generating static pages (0/17) ...
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:46.1304119Z    Generating static pages (4/17) 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:46.2640873Z    Generating static pages (8/17) 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:46.4881416Z    Generating static pages (12/17) 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:46.6471833Z  ✓ Generating static pages (17/17)
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:47.2095508Z    Finalizing page optimization ...
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:47.2095929Z    Collecting build traces ...
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2329648Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2366717Z Route (app)                                 Size  First Load JS
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2367815Z ┌ ○ /                                    2.91 kB         118 kB
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2368512Z ├ ○ /_not-found                            996 B         103 kB
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2369242Z ├ ƒ /app                                 2.53 kB         109 kB
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2369853Z ├ ○ /app/analyzer                        9.09 kB         130 kB
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2370543Z ├ ○ /app/billing                         3.93 kB         111 kB
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2371216Z ├ ƒ /app/compare                           119 B         106 kB
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2371733Z ├ ○ /app/entry-wizard                      183 B         120 kB
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2372182Z ├ ○ /app/forms                           6.81 kB         118 kB
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2372619Z ├ ƒ /app/forms/[id]                      7.23 kB         122 kB
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2373064Z ├ ○ /app/generator                       5.01 kB         125 kB
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2373522Z ├ ƒ /app/jobs/[id]                       4.43 kB         112 kB
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2373962Z ├ ○ /app/profile                         3.92 kB         111 kB
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2374381Z ├ ƒ /app/reports/[id]                    4.42 kB         112 kB
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2374842Z ├ ƒ /app/sources                           120 B         106 kB
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2375278Z ├ ○ /app/upload                            185 B         121 kB
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2375705Z ├ ○ /auth/login                          1.29 kB         113 kB
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2376133Z ├ ○ /auth/register                       3.26 kB         115 kB
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2376561Z └ ○ /icon.svg                                0 B            0 B
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2376929Z + First Load JS shared by all             102 kB
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2377315Z   ├ chunks/560-6268896ae5bcbe66.js       45.9 kB
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2377675Z   ├ chunks/af3f158d-fea694c5ee5e0159.js  54.2 kB
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2378028Z   └ other shared chunks (total)          1.94 kB
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2378205Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2378213Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2378418Z ○  (Static)   prerendered as static content
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2378946Z ƒ  (Dynamic)  server-rendered on demand
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.2381730Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.5231909Z Wrote C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\assets\docly-icon.ico (14120 bytes)
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:55.5233807Z Wrote C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\assets\docly-logo.png and C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\web\public\docly-logo.png
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:56.7520014Z Font verified: C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\api\app\services\forms\fill\assets\NotoSans-Regular.ttf
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:41:56.7528263Z SHA-256: b85c38ecea8a7cfb39c24e395a4007474fa5a4fc864f6ee33309eb4948d232d5
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:42:48.2901798Z \u0421\u0435\u0440\u0432\u0438\u0441 \u043d\u0435 \u0437\u0430\u043f\u0443\u0441\u0442\u0438\u043b\u0441\u044f
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:42:48.2902566Z \u0421\u043c\u043e\u0442\u0440\u0438\u0442\u0435 artifacts\local-run\api.err.log
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:42:48.6994415Z Не удалось подготовить Docly: Ошибка выполнения C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\api\.venv\Scripts\python.exe (код 1). См. журнал подготовки.
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:42:48.6995868Z Журнал: C:\Users\runneradmin\AppData\Local\Programs\Docly\artifacts\local-run\installer-bootstrap.log
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:42:48.6996669Z Закройте другой запуск Docly, проверьте интернет и повторите запуск ярлыка.
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:42:48.8236206Z not_running
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:42:48.9303136Z FAIL: first-run bootstrap and launcher
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:42:48.9303803Z At D:\a\Misha-debil\Misha-debil\installer\smoke-test.ps1:9 char:21
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:42:48.9304546Z +     if (-not $Ok) { throw "FAIL: $Name" }
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:42:48.9304943Z +                     ~~~~~~~~~~~~~~~~~~~
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:42:48.9305494Z     + CategoryInfo          : OperationStopped: (FAIL: first-run bootstrap and launcher:String) [], RuntimeException
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:42:48.9306109Z     + FullyQualifiedErrorId : FAIL: first-run bootstrap and launcher
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:42:48.9306572Z  
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:42:48.9508589Z ##[error]Process completed with exit code 1.
```
## Run 34257846657

```json
{
  "conclusion": "failure",
  "headSha": "eaec1824e333e63ca0abd73808a08914761b59c0",
  "jobs": [
    {
      "completedAt": "2026-09-08T17:38:01Z",
      "conclusion": "failure",
      "databaseId": 102168404410,
      "name": "installer",
      "startedAt": "2026-09-08T17:34:48Z",
      "status": "completed",
      "steps": [
        {
          "completedAt": "2026-09-08T17:34:51Z",
          "conclusion": "success",
          "name": "Set up job",
          "number": 1,
          "startedAt": "2026-09-08T17:34:49Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:34:57Z",
          "conclusion": "success",
          "name": "Run actions/checkout@v4",
          "number": 2,
          "startedAt": "2026-09-08T17:34:51Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:35:02Z",
          "conclusion": "success",
          "name": "Run actions/setup-node@v4",
          "number": 3,
          "startedAt": "2026-09-08T17:34:57Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:35:02Z",
          "conclusion": "success",
          "name": "Run actions/setup-python@v5",
          "number": 4,
          "startedAt": "2026-09-08T17:35:02Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:35:05Z",
          "conclusion": "success",
          "name": "Validate PowerShell syntax",
          "number": 5,
          "startedAt": "2026-09-08T17:35:02Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:35:10Z",
          "conclusion": "success",
          "name": "Build EXE",
          "number": 6,
          "startedAt": "2026-09-08T17:35:05Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:37:50Z",
          "conclusion": "failure",
          "name": "Install, bootstrap, launch twice, reinstall and uninstall",
          "number": 7,
          "startedAt": "2026-09-08T17:35:10Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:37:52Z",
          "conclusion": "success",
          "name": "Keep build and test evidence (not a release on failure)",
          "number": 8,
          "startedAt": "2026-09-08T17:37:50Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:37:52Z",
          "conclusion": "skipped",
          "name": "Publish smoke-tested prerelease",
          "number": 9,
          "startedAt": "2026-09-08T17:37:52Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:37:57Z",
          "conclusion": "success",
          "name": "Persist CI checkpoint to working branch",
          "number": 10,
          "startedAt": "2026-09-08T17:37:52Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:37:57Z",
          "conclusion": "skipped",
          "name": "Post Run actions/setup-python@v5",
          "number": 18,
          "startedAt": "2026-09-08T17:37:57Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:37:57Z",
          "conclusion": "skipped",
          "name": "Post Run actions/setup-node@v4",
          "number": 19,
          "startedAt": "2026-09-08T17:37:57Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:37:59Z",
          "conclusion": "success",
          "name": "Post Run actions/checkout@v4",
          "number": 20,
          "startedAt": "2026-09-08T17:37:57Z",
          "status": "completed"
        },
        {
          "completedAt": "2026-09-08T17:37:59Z",
          "conclusion": "success",
          "name": "Complete job",
          "number": 21,
          "startedAt": "2026-09-08T17:37:59Z",
          "status": "completed"
        }
      ],
      "url": "https://github.com/dushavolka1-design/Misha-debil/actions/runs/34257846657/job/102168404410"
    }
  ],
  "status": "completed",
  "url": "https://github.com/dushavolka1-design/Misha-debil/actions/runs/34257846657"
}
```

```text
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:36:42.8150949Z Progress: resolved 510, reused 0, downloaded 36, added 22
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:36:43.8159236Z Progress: resolved 510, reused 0, downloaded 39, added 26
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:36:44.9472918Z Progress: resolved 510, reused 0, downloaded 40, added 26
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:36:45.9497093Z Progress: resolved 510, reused 0, downloaded 48, added 33
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:36:46.9502439Z Progress: resolved 510, reused 0, downloaded 61, added 46
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:36:49.0021593Z Progress: resolved 510, reused 0, downloaded 61, added 47
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:36:50.0144124Z Progress: resolved 510, reused 0, downloaded 79, added 63
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:36:51.0162518Z Progress: resolved 510, reused 0, downloaded 110, added 96
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:36:52.0325485Z Progress: resolved 510, reused 0, downloaded 131, added 118
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:36:54.3715608Z Progress: resolved 510, reused 0, downloaded 132, added 118
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:36:55.3725738Z Progress: resolved 510, reused 0, downloaded 132, added 120
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:36:57.0107962Z Progress: resolved 510, reused 0, downloaded 133, added 120
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:36:58.0245787Z Progress: resolved 510, reused 0, downloaded 147, added 132
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:36:59.0248439Z Progress: resolved 510, reused 0, downloaded 159, added 144
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:00.0362005Z Progress: resolved 510, reused 0, downloaded 160, added 144
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:01.0413037Z Progress: resolved 510, reused 0, downloaded 178, added 166
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:02.0409343Z Progress: resolved 510, reused 0, downloaded 198, added 186
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:03.9179307Z Progress: resolved 510, reused 0, downloaded 199, added 186
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:04.9215334Z Progress: resolved 510, reused 0, downloaded 220, added 206
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:05.9230728Z Progress: resolved 510, reused 0, downloaded 242, added 227
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:06.9286125Z Progress: resolved 510, reused 0, downloaded 261, added 247
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:07.9288615Z Progress: resolved 510, reused 0, downloaded 272, added 258
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:08.9356398Z Progress: resolved 510, reused 0, downloaded 280, added 265
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:09.9406244Z Progress: resolved 510, reused 0, downloaded 283, added 268
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:10.9471125Z Progress: resolved 510, reused 0, downloaded 284, added 268
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:11.9626370Z Progress: resolved 510, reused 0, downloaded 290, added 273
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:12.9638091Z Progress: resolved 510, reused 0, downloaded 294, added 279
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:14.8610081Z Progress: resolved 510, reused 0, downloaded 295, added 279
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:15.8634427Z Progress: resolved 510, reused 0, downloaded 295, added 280
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:16.8652081Z Progress: resolved 510, reused 0, downloaded 300, added 286
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:17.8660088Z Progress: resolved 510, reused 0, downloaded 314, added 297
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:18.8819721Z Progress: resolved 510, reused 0, downloaded 330, added 312
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:19.8829264Z Progress: resolved 510, reused 0, downloaded 346, added 332
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:20.8830601Z Progress: resolved 510, reused 0, downloaded 352, added 336
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:21.8847319Z Progress: resolved 510, reused 0, downloaded 357, added 342
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:22.8872062Z Progress: resolved 510, reused 0, downloaded 365, added 350
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:25.5232026Z Progress: resolved 510, reused 0, downloaded 366, added 350
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:26.5333695Z Progress: resolved 510, reused 0, downloaded 380, added 364
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:27.5422204Z Progress: resolved 510, reused 0, downloaded 383, added 368
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:28.5428486Z Progress: resolved 510, reused 0, downloaded 384, added 368
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:29.5457017Z Progress: resolved 510, reused 0, downloaded 396, added 378
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:30.5454667Z Progress: resolved 510, reused 0, downloaded 435, added 421
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:31.5467171Z Progress: resolved 510, reused 0, downloaded 461, added 443
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:34.6125417Z Progress: resolved 510, reused 0, downloaded 461, added 444
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:35.6257149Z Progress: resolved 510, reused 0, downloaded 475, added 463
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:36.6273969Z Progress: resolved 510, reused 0, downloaded 497, added 489
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:38.7943071Z Progress: resolved 510, reused 0, downloaded 498, added 489
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:39.1790965Z Progress: resolved 510, reused 0, downloaded 510, added 510, done
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:40.4346010Z .../node_modules/unrs-resolver postinstall$ node postinstall.js
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:40.4354875Z .../sharp@0.34.5/node_modules/sharp install$ node install/check.js || npm run build
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:40.4365931Z .../esbuild@0.28.2/node_modules/esbuild postinstall$ node install.js
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:40.4567873Z .../esbuild@0.25.12/node_modules/esbuild postinstall$ node install.js
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:40.5729291Z .../sharp@0.34.5/node_modules/sharp install: Done
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:40.6512823Z .../esbuild@0.28.2/node_modules/esbuild postinstall: Done
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:40.6579597Z .../esbuild@0.25.12/node_modules/esbuild postinstall: Done
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:40.6688826Z .../node_modules/unrs-resolver postinstall: Done
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:40.9157383Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:40.9160971Z devDependencies:
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:40.9161404Z + prettier 3.9.6
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:40.9161626Z + turbo 2.10.9
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:40.9161848Z + typescript 5.9.3
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:40.9161985Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:40.9856757Z Done in 1m 16.5s using pnpm v9.15.9
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:41.5588920Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:41.5589963Z > @dar/web@0.2.0 build C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\web
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:41.5590574Z > next build
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:41.5590727Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:42.7741182Z ⚠ No build cache found. Please configure build caching for faster rebuilds. Read more: https://nextjs.org/docs/messages/no-cache
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:42.7908496Z Attention: Next.js now collects completely anonymous telemetry regarding usage.
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:42.7909634Z This information is used to shape Next.js' roadmap and prioritize features.
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:42.7910906Z You can learn more, including how to opt-out if you'd not like to participate in this anonymous program, by visiting the following URL:
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:42.7911656Z https://nextjs.org/telemetry
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:42.7911857Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:42.9392558Z    ▲ Next.js 15.5.23
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:42.9393470Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:43.0294279Z    Creating an optimized production build ...
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:49.2735113Z Failed to compile.
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:49.2735482Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:49.2737673Z ./src/app/app/analyzer/AnalyzerHubClient.tsx
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:49.2738761Z Module not found: Can't resolve '../upload/UploadClient'
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:49.2739390Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:49.2739787Z https://nextjs.org/docs/messages/module-not-found
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:49.2740365Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:49.2795234Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:49.2797201Z > Build failed because of webpack errors
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:49.2996791Z C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\web:
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:49.2999213Z  ERR_PNPM_RECURSIVE_RUN_FIRST_FAIL  @dar/web@0.2.0 build: `next build`
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:49.2999842Z Exit status 1
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:49.7791482Z Не удалось подготовить Docly: Ошибка выполнения C:\Program Files\nodejs\node.exe (код 1). См. журнал подготовки.
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:49.7792746Z Журнал: C:\Users\runneradmin\AppData\Local\Programs\Docly\artifacts\local-run\installer-bootstrap.log
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:49.7793509Z Закройте другой запуск Docly, проверьте интернет и повторите запуск ярлыка.
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:50.0370729Z not_running
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:50.1177122Z FAIL: first-run bootstrap and launcher
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:50.1178069Z At D:\a\Misha-debil\Misha-debil\installer\smoke-test.ps1:9 char:21
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:50.1178694Z +     if (-not $Ok) { throw "FAIL: $Name" }
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:50.1179011Z +                     ~~~~~~~~~~~~~~~~~~~
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:50.1179622Z     + CategoryInfo          : OperationStopped: (FAIL: first-run bootstrap and launcher:String) [], RuntimeException
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:50.1180692Z     + FullyQualifiedErrorId : FAIL: first-run bootstrap and launcher
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:50.1181256Z  
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:37:50.1362526Z ##[error]Process completed with exit code 1.
```
