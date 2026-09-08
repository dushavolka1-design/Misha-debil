# Installer failure diagnostic excerpt

Run: https://github.com/dushavolka1-design/Misha-debil/actions/runs/34257558249

```text
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:27.5421938Z [notice] A new release of pip is available: 25.0.1 -> 26.2.1
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:27.5423393Z [notice] To update, run: C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\api\.venv\Scripts\python.exe -m pip install --upgrade pip
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:29.2819736Z Obtaining file:///C:/Users/runneradmin/AppData/Local/Programs/Docly/packages/py_dar
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:29.2854404Z   Installing build dependencies: started
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:32.3956108Z   Installing build dependencies: finished with status 'done'
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:32.3974078Z   Checking if build backend supports build_editable: started
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:32.4592038Z   Checking if build backend supports build_editable: finished with status 'done'
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:32.4615132Z   Getting requirements to build editable: started
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:32.5848673Z   Getting requirements to build editable: finished with status 'done'
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:32.5877474Z   Installing backend dependencies: started
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:34.4507042Z   Installing backend dependencies: finished with status 'done'
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:34.4528047Z   Preparing editable metadata (pyproject.toml): started
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:34.6955759Z   Preparing editable metadata (pyproject.toml): finished with status 'done'
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:34.7037896Z Requirement already satisfied: pydantic-settings>=2.7 in c:\users\runneradmin\appdata\local\programs\docly\apps\api\.venv\lib\site-packages (from dar-core==0.1.0) (2.15.0)
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:34.7042655Z Requirement already satisfied: pydantic>=2.10 in c:\users\runneradmin\appdata\local\programs\docly\apps\api\.venv\lib\site-packages (from dar-core==0.1.0) (2.13.5)
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:34.7073902Z Requirement already satisfied: annotated-types>=0.6.0 in c:\users\runneradmin\appdata\local\programs\docly\apps\api\.venv\lib\site-packages (from pydantic>=2.10->dar-core==0.1.0) (0.8.0)
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:34.7078134Z Requirement already satisfied: pydantic-core==2.46.5 in c:\users\runneradmin\appdata\local\programs\docly\apps\api\.venv\lib\site-packages (from pydantic>=2.10->dar-core==0.1.0) (2.46.5)
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:34.7082184Z Requirement already satisfied: typing-extensions>=4.14.1 in c:\users\runneradmin\appdata\local\programs\docly\apps\api\.venv\lib\site-packages (from pydantic>=2.10->dar-core==0.1.0) (4.16.0)
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:34.7086162Z Requirement already satisfied: typing-inspection>=0.4.2 in c:\users\runneradmin\appdata\local\programs\docly\apps\api\.venv\lib\site-packages (from pydantic>=2.10->dar-core==0.1.0) (0.4.4)
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:34.7114281Z Requirement already satisfied: python-dotenv>=0.21.0 in c:\users\runneradmin\appdata\local\programs\docly\apps\api\.venv\lib\site-packages (from pydantic-settings>=2.7->dar-core==0.1.0) (1.2.3)
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:34.7161445Z Building wheels for collected packages: dar-core
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:34.7233143Z   Building editable for dar-core (pyproject.toml): started
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:34.7865551Z   Building editable for dar-core (pyproject.toml): finished with status 'done'
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:34.7883415Z   Created wheel for dar-core: filename=dar_core-0.1.0-py3-none-any.whl size=1142 sha256=d87adb7bf17c5c4bec8ca0078ea35418a20432113bd95dfb7482795864a8b8be
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:34.7885704Z   Stored in directory: C:\Users\runneradmin\AppData\Local\Temp\pip-ephem-wheel-cache-4qn_i43b\wheels\87\cb\30\575a5e1bcf18a4fdec630271c6524596cdd828b148b15383d3
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:34.7915738Z Successfully built dar-core
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:34.8558178Z Installing collected packages: dar-core
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:34.9213723Z Successfully installed dar-core-0.1.0
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:35.1135037Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:35.1137392Z [notice] A new release of pip is available: 25.0.1 -> 26.2.1
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:35.1139933Z [notice] To update, run: C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\api\.venv\Scripts\python.exe -m pip install --upgrade pip
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:48.4473270Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:48.4474123Z added 1 package in 11s
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:50.8160489Z Scope: all 6 workspace projects
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:50.8873527Z Lockfile is up to date, resolution step is skipped
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:50.9681212Z Progress: resolved 1, reused 0, downloaded 0, added 0
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:51.0773272Z Packages: +510
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:51.0774780Z ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:51.9820974Z Progress: resolved 510, reused 0, downloaded 0, added 0
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:52.9881649Z Progress: resolved 510, reused 0, downloaded 3, added 0
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:53.9923953Z Progress: resolved 510, reused 0, downloaded 4, added 0
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:58.3325724Z Progress: resolved 510, reused 0, downloaded 5, added 0
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:32:59.3374069Z Progress: resolved 510, reused 0, downloaded 6, added 0
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:04.5604145Z Progress: resolved 510, reused 0, downloaded 7, added 0
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:05.5605465Z Progress: resolved 510, reused 0, downloaded 13, added 1
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:06.5636543Z Progress: resolved 510, reused 0, downloaded 14, added 1
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:07.5648404Z Progress: resolved 510, reused 0, downloaded 15, added 2
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:08.5688584Z Progress: resolved 510, reused 0, downloaded 19, added 6
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:09.5727153Z Progress: resolved 510, reused 0, downloaded 20, added 6
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:11.6443485Z Progress: resolved 510, reused 0, downloaded 20, added 7
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:12.6549317Z Progress: resolved 510, reused 0, downloaded 22, added 8
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:13.6547262Z Progress: resolved 510, reused 0, downloaded 26, added 13
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:14.6703086Z Progress: resolved 510, reused 0, downloaded 30, added 17
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:15.6755366Z Progress: resolved 510, reused 0, downloaded 31, added 18
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:16.8955368Z Progress: resolved 510, reused 0, downloaded 32, added 18
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:17.8978557Z Progress: resolved 510, reused 0, downloaded 47, added 34
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:18.9057517Z Progress: resolved 510, reused 0, downloaded 63, added 50
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:19.9086751Z Progress: resolved 510, reused 0, downloaded 79, added 65
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:20.9090743Z Progress: resolved 510, reused 0, downloaded 104, added 90
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:21.9153326Z Progress: resolved 510, reused 0, downloaded 113, added 101
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:23.1620203Z Progress: resolved 510, reused 0, downloaded 114, added 101
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:24.1698402Z Progress: resolved 510, reused 0, downloaded 129, added 117
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:25.2431753Z Progress: resolved 510, reused 0, downloaded 130, added 117
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:26.2542635Z Progress: resolved 510, reused 0, downloaded 131, added 119
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:27.3370135Z Progress: resolved 510, reused 0, downloaded 132, added 119
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:28.3507347Z Progress: resolved 510, reused 0, downloaded 140, added 127
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:30.7201151Z Progress: resolved 510, reused 0, downloaded 141, added 127
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:31.7291544Z Progress: resolved 510, reused 0, downloaded 146, added 130
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:32.7318235Z Progress: resolved 510, reused 0, downloaded 158, added 143
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:33.7361446Z Progress: resolved 510, reused 0, downloaded 170, added 154
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:34.7380907Z Progress: resolved 510, reused 0, downloaded 172, added 157
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:35.7382748Z Progress: resolved 510, reused 0, downloaded 189, added 172
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:36.7403441Z Progress: resolved 510, reused 0, downloaded 190, added 172
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:37.7452253Z Progress: resolved 510, reused 0, downloaded 192, added 174
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:38.7455970Z Progress: resolved 510, reused 0, downloaded 198, added 182
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:39.7471531Z Progress: resolved 510, reused 0, downloaded 213, added 195
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:40.7485070Z Progress: resolved 510, reused 0, downloaded 242, added 225
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:41.7511934Z Progress: resolved 510, reused 0, downloaded 250, added 233
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:42.7537392Z Progress: resolved 510, reused 0, downloaded 257, added 240
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:43.7548611Z Progress: resolved 510, reused 0, downloaded 264, added 247
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:45.5522348Z Progress: resolved 510, reused 0, downloaded 265, added 247
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:46.5582754Z Progress: resolved 510, reused 0, downloaded 279, added 265
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:47.5599956Z Progress: resolved 510, reused 0, downloaded 290, added 273
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:48.5606546Z Progress: resolved 510, reused 0, downloaded 295, added 280
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:50.6004404Z Progress: resolved 510, reused 0, downloaded 296, added 280
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:51.6123197Z Progress: resolved 510, reused 0, downloaded 309, added 293
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:52.6173625Z Progress: resolved 510, reused 0, downloaded 310, added 294
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:53.6210335Z Progress: resolved 510, reused 0, downloaded 318, added 300
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:54.6219638Z Progress: resolved 510, reused 0, downloaded 322, added 307
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:55.6225735Z Progress: resolved 510, reused 0, downloaded 342, added 328
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:33:59.1826031Z Progress: resolved 510, reused 0, downloaded 342, added 329
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:00.1834011Z Progress: resolved 510, reused 0, downloaded 369, added 356
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:01.1840941Z Progress: resolved 510, reused 0, downloaded 384, added 370
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:03.8264164Z Progress: resolved 510, reused 0, downloaded 384, added 371
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:04.8293127Z Progress: resolved 510, reused 0, downloaded 404, added 390
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:05.8326322Z Progress: resolved 510, reused 0, downloaded 429, added 415
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:06.8487441Z Progress: resolved 510, reused 0, downloaded 431, added 418
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:10.4620332Z Progress: resolved 510, reused 0, downloaded 432, added 418
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:11.4725605Z Progress: resolved 510, reused 0, downloaded 439, added 426
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:15.0270951Z Progress: resolved 510, reused 0, downloaded 440, added 426
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:16.0303319Z Progress: resolved 510, reused 0, downloaded 442, added 429
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:17.0325067Z Progress: resolved 510, reused 0, downloaded 445, added 431
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:18.0344676Z Progress: resolved 510, reused 0, downloaded 446, added 433
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:19.0355659Z Progress: resolved 510, reused 0, downloaded 450, added 436
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:20.0394038Z Progress: resolved 510, reused 0, downloaded 467, added 455
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:21.0414890Z Progress: resolved 510, reused 0, downloaded 495, added 481
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:22.0420331Z Progress: resolved 510, reused 0, downloaded 506, added 493
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:22.4361089Z Progress: resolved 510, reused 0, downloaded 510, added 510, done
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:23.7242653Z .../sharp@0.34.5/node_modules/sharp install$ node install/check.js || npm run build
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:23.7251390Z .../node_modules/unrs-resolver postinstall$ node postinstall.js
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:23.7391291Z .../esbuild@0.28.2/node_modules/esbuild postinstall$ node install.js
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:23.7439455Z .../esbuild@0.25.12/node_modules/esbuild postinstall$ node install.js
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:23.8690439Z .../sharp@0.34.5/node_modules/sharp install: Done
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:23.9469702Z .../esbuild@0.25.12/node_modules/esbuild postinstall: Done
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:23.9479228Z .../esbuild@0.28.2/node_modules/esbuild postinstall: Done
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:24.8839646Z .../node_modules/unrs-resolver postinstall: Done
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:25.0625756Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:25.0626320Z devDependencies:
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:25.0626930Z + prettier 3.9.6
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:25.0627331Z + turbo 2.10.9
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:25.0627726Z + typescript 5.9.3
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:25.0627963Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:25.1387074Z Done in 1m 34.9s using pnpm v9.15.9
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:25.7177769Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:25.7178658Z > @dar/web@0.2.0 build C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\web
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:25.7180359Z > next build
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:25.7180509Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:26.9690085Z ⚠ No build cache found. Please configure build caching for faster rebuilds. Read more: https://nextjs.org/docs/messages/no-cache
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:26.9996871Z Attention: Next.js now collects completely anonymous telemetry regarding usage.
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:26.9998270Z This information is used to shape Next.js' roadmap and prioritize features.
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:26.9999488Z You can learn more, including how to opt-out if you'd not like to participate in this anonymous program, by visiting the following URL:
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:27.0000379Z https://nextjs.org/telemetry
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:27.0000627Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:27.1274025Z    ▲ Next.js 15.5.23
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:27.1274449Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:27.2212198Z    Creating an optimized production build ...
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:33.3037475Z Failed to compile.
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:33.3037854Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:33.3074067Z ./src/app/app/analyzer/AnalyzerHubClient.tsx
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:33.3075014Z Module not found: Can't resolve '../upload/UploadClient'
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:33.3075454Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:33.3075789Z https://nextjs.org/docs/messages/module-not-found
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:33.3076160Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:33.3103182Z 
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:33.3104956Z > Build failed because of webpack errors
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:33.3296902Z C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\web:
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:33.3299738Z  ERR_PNPM_RECURSIVE_RUN_FIRST_FAIL  @dar/web@0.2.0 build: `next build`
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:33.3300448Z Exit status 1
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:34.3310515Z Не удалось подготовить Docly: Ошибка выполнения C:\Program Files\nodejs\node.exe (код 1). См. журнал подготовки.
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:34.3312344Z Журнал: C:\Users\runneradmin\AppData\Local\Programs\Docly\artifacts\local-run\installer-bootstrap.log
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:34.3313600Z Закройте другой запуск Docly, проверьте интернет и повторите запуск ярлыка.
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:34.5856230Z not_running
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:34.6566920Z FAIL: first-run bootstrap and launcher
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:34.6568301Z At D:\a\Misha-debil\Misha-debil\installer\smoke-test.ps1:9 char:21
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:34.6568803Z +     if (-not $Ok) { throw "FAIL: $Name" }
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:34.6569161Z +                     ~~~~~~~~~~~~~~~~~~~
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:34.6569757Z     + CategoryInfo          : OperationStopped: (FAIL: first-run bootstrap and launcher:String) [], RuntimeException
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:34.6570491Z     + FullyQualifiedErrorId : FAIL: first-run bootstrap and launcher
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:34.6570968Z  
installer	Install, bootstrap, launch twice, reinstall and uninstall	2026-09-08T17:34:34.6747688Z ##[error]Process completed with exit code 1.
```
