# dj_api_auto

DJ 音乐播放器后台接口的自动化测试工程，覆盖歌单查询、播放与暂停、上下切歌、音量、均衡器、播放模式。
技术栈：Python 3.13 + requests + pytest + PyYAML + Allure + loguru，被测服务用 Flask 起在本地。

被测服务是仓库里的一个 Flask 应用（`mock_server/app.py`），9 个业务接口，带参数校验、状态机约束和签名校验。
测试代码直接请求这个服务，克隆仓库、装好依赖就能跑，不依赖内网环境。当前用例 20 条。

## 环境要求

| 项 | 说明 |
| --- | --- |
| Python | 3.10 及以上（验证用的是 3.13） |
| 被测服务 | 仓库内 `mock_server/app.py`，默认监听 9300 端口 |
| Allure 命令行 | 可选。装了才能生成 HTML 报告，不装仍可跑用例，原始数据留在 `report/allure_raw` |

## 依赖与用途

| 包 | 用途 | 备注 |
| --- | --- | --- |
| `requests` | HTTP 请求 | 统一走 `common/request_handler.py` 的 Session |
| `PyYAML` | 读取环境配置和用例数据 | 数据层用 `yaml.safe_load` |
| `pytest` | 用例执行、参数化、fixture | `pytest.ini` 固定扫描路径与执行参数 |
| `allure-pytest` | 报告，附带请求/响应与软断言明细 | 需要 allure 命令行转 HTML |
| `pytest-rerunfailures` | 失败重跑 | 最多 2 次，间隔 1 秒 |
| `loguru` | 日志 | 控制台 + 按天切文件，10MB 轮转，保留 7 天 |
| `flask` | 起被测服务 | 仅 `mock_server` 使用，测试代码不依赖 |

安装：

```powershell
pip install -r requirements.txt
```

## 目录与职责

| 路径 | 职责 |
| --- | --- |
| `api/dj_api.py` | 播放器接口：歌单、播放、暂停、切歌、音量、均衡器、播放模式，只拼参数不做断言 |
| `common/conf_handler.py` | 读 `config/env.yaml`，用 `config/env_local.yaml` 深度覆盖，产出 `config` 单例 |
| `common/request_handler.py` | 请求封装：拼 URL、算签名、带 token、401 重登、记日志，产出 `client` 单例 |
| `common/logger_handler.py` | loguru 初始化，输出到 `report/logs/dj_api_日期.log` |
| `common/assert_handler.py` | 软断言。一条用例里的多个检查点全部执行完再统一抛错 |
| `config/env.yaml` | local / ci 两套地址，外加 Mock 账号与签名密钥 |
| `data/dj_data.yaml` | 音量、均衡器、播放模式、播放的用例参数与预期业务码、提示 |
| `testcases/conftest.py` | `client` fixture（session 级）、`prepared_env` fixture（复位数据并登录） |
| `testcases/test_dj.py` | 只做三件事：读数据、调 api 层、写断言 |
| `mock_server/app.py` | 被测服务，9 个业务接口 + `/health` + `/__admin/reset` |
| `run.py` | 起服务、跑用例、生成报告的入口 |
| `Jenkinsfile` / `docker-compose.yml` | 流水线和容器编排 |

`api` 和 `common` 的分界：`api` 只描述「哪个接口、传什么」，`common` 只负责「怎么发出去、怎么记录」。

## 跑起来

```powershell
# 方式一：一条命令（自动起服务、跑完自动关）
python run.py

# 方式二：分开执行，方便看日志
python mock_server/app.py      # 终端 1，保持前台运行
pytest                          # 终端 2

# 只跑某个场景
pytest testcases/test_dj.py -k 音量
```

正常输出结尾：

```
============================= 20 passed in 0.51s ==============================
```

服务单独起的时候，先确认它活着：

```powershell
curl http://127.0.0.1:9300/health
# {"service":"mock-dj-api","sign_check":false,"status":"ok"}
```

## 一次请求的调用链

以「播放歌曲」为例：

```
testcases/test_dj.py::test_play
  → api/dj_api.py::DjApi.play(song_id)              拼 payload
  → common/request_handler.py::RequestHandler.send() 算 X-Sign、带 Authorization、发请求、记日志
  → mock_server/app.py::dj_play()                   校验歌曲存在，写播放状态
  → 返回 {"code":200,"data":{"song_id":2,"playing":true,...}}
  → common/assert_handler.py::AssertHandler          记录每个检查点，最后统一抛错
```

排查问题按这条链自上而下看，日志里每一步都有对应的 `-->` / `<--` 记录。

## 配置

`config/env.yaml`：

```yaml
current_env: "local"

local:
  base_url: "http://127.0.0.1:9300"
  timeout: 10
  sign_key: "mock-sign-key-2026"

ci:
  base_url: "http://host.docker.internal:9300"
  timeout: 15
  sign_key: "mock-sign-key-2026"

account:
  username: "testuser"
  password: "123456"
```

| 字段 | 含义 | 说明 |
| --- | --- | --- |
| `current_env` | 默认生效的环境名 | 可被 `ENV` 环境变量覆盖 |
| `base_url` | 接口根地址 | 可被 `BASE_URL` 覆盖，CI 里用这个注入 |
| `timeout` | 请求超时（秒） | 传进 `requests` |
| `sign_key` | 签名密钥 | 必须与服务端 `SIGN_KEY` 一致 |
| `account` | 登录账号 | Mock 服务的固定账号，不是真实凭据 |

生效顺序：`BASE_URL` / `ENV` 环境变量 → `config/env_local.yaml` → `config/env.yaml`。
`env_local.yaml` 用同样的结构，只写要覆盖的字段（`deep_merge` 递归合并，不需要写全）。

```yaml
# config/env_local.yaml 示例（被 .gitignore 排除，不会进仓库）
local:
  base_url: "http://127.0.0.1:9301"
account:
  username: "your_name"
  password: "your_password"
```

切环境：

```powershell
$env:ENV = "ci"
$env:BASE_URL = "http://127.0.0.1:9301"
pytest
```

账号也可以用 `SDK_USER` / `SDK_PWD` 覆盖，适合流水线按环境注入不同账号。

## 覆盖的接口

| 模块 | 方法 | 路径 | 主要校验 |
| --- | --- | --- | --- |
| 登录 | POST | `/user/login` | 用户名空 → 400；密码错 → 401 |
| 歌单 | GET | `/dj/playlist` | 返回 `total` 与 `list`，每首歌带 `song_id`、`name`、`artist`、`duration` |
| 播放 | POST | `/dj/play` | 缺 `song_id` → 400；歌曲不存在 → 404；成功后记录当前曲目并置为播放中 |
| 暂停 | POST | `/dj/pause` | 当前无播放曲目 → 400；成功后保留当前曲目、`playing=false` |
| 下一首 | POST | `/dj/next` | 当前无播放曲目 → 400；末曲继续下一首时回到第一首 |
| 上一首 | POST | `/dj/prev` | 当前无播放曲目 → 400；首曲向前切时回到末曲 |
| 音量 | POST | `/dj/volume` | 0-100 的整数，越界与非整数 → 400 |
| 均衡器 | POST | `/dj/eq` | 只接受 `normal` / `rock` / `jazz` / `vocal` |
| 播放模式 | POST | `/dj/play_mode` | 只接受 `sequence` / `loop` / `single` / `random` |

业务码约定：HTTP 状态码统一 200，响应体 `code` 区分结果
（200 成功 / 400 参数非法或状态不允许 / 401 未登录或签名错误 / 404 歌曲不存在）。

## 用例清单

| 用例 | 条数 | 覆盖点 |
| --- | --- | --- |
| `test_playlist` | 1 | 总数与列表长度一致、字段完整、时长大于 0 |
| `test_play` | 2 | 播放存在的歌曲、播放不存在的歌曲 404 |
| `test_pause` | 1 | 播放后暂停，状态与当前曲目正确 |
| `test_pause_without_playing` | 1 | 未播放时暂停 → 400 |
| `test_next_song` | 1 | 第一首 → 第二首 |
| `test_next_without_playing` | 1 | 未播放时切歌 → 400 |
| `test_prev_song` | 1 | 第二首 → 第一首 |
| `test_prev_song_from_first` | 1 | 首曲向前切 → 末曲 |
| `test_volume` | 5 | 60 正常、0 与 100 边界、101 与 -1 越界 |
| `test_eq` | 3 | rock、jazz 正常、pop 非法 |
| `test_play_mode` | 3 | loop、random 正常、shuffle 非法 |

## 新增一条用例

### 只加场景，不改逻辑

在 `data/dj_data.yaml` 对应分组下加一项，代码不动：

```yaml
# data/dj_data.yaml
volume_cases:
  - case_name: "设置音量33"
    volume: 33
    expect:
      code: 200
```

```powershell
pytest testcases/test_dj.py -k "音量33"
```

`expect.msg` 可选，写了就检查提示文案是否包含该关键字，不写只比业务码。

### 加一个新接口

四步：

1. `mock_server/app.py` 加路由和校验逻辑，并加进 `STATE` 与 `/__admin/reset`。
2. `api/dj_api.py` 加方法，只拼参数：

```python
def seek(self, position: int):
    return self.client.post("/dj/seek", json={"position": position})
```

3. `data/` 里加分组（如果需要参数化）。
4. `testcases/` 里加用例，断言写完整（成功校验返回字段，失败校验业务码和提示）。

需要新的校验维度（响应头、状态持久化、并发）时，才动 `testcases` 里的断言代码。

### 断言怎么写

`AssertHandler` 是软断言：一条用例里多个检查点都会执行，最后统一抛错，失败信息汇总在一条消息里。

```python
a = AssertHandler()
a.eq(body["code"], case["expect"]["code"], "业务码")
a.contains(body["msg"], "0-100", "错误提示")
a.eq(body["data"]["volume"], case["volume"], "音量已生效")
a.finish()
```

`finish()` 必须调用，否则失败不会抛出。

## 关于签名

请求头带 `X-Sign`，客户端和服务端各实现一次，必须一致：

```
sign = MD5( METHOD + path + 按键排序的 "k=v" 拼接 + "&key=" + sign_key )
```

- 客户端：`common/request_handler.py::make_sign()`
- 服务端：`mock_server/app.py::make_sign()`

服务端由环境变量 `SIGN_CHECK` 控制是否强制校验，默认 `false`。本地默认关掉，排查用例失败时不必先怀疑签名；
要验证签名链路时打开：

```powershell
$env:SIGN_CHECK = "true"; python mock_server/app.py
```

打开后如果两端 `sign_key` 不一致，所有请求会返回 401「签名校验失败」。

## 测试数据与状态

服务端在内存里维护四项状态，`POST /__admin/reset` 恢复初始值：

| 字段 | 含义 | 初始值 |
| --- | --- | --- |
| `current` | 当前曲目 ID | `None` |
| `playing` | 是否处于播放中 | `false` |
| `volume` | 音量 | `50` |
| `eq` | 均衡器档位 | `normal` |
| `play_mode` | 播放模式 | `sequence` |

歌单是服务端的固定数据，4 首，不需要在用例里预置。
「暂停」「切歌」这类依赖前置状态的用例，自己在开头先把状态设好；依赖「未播放」这类空状态的用例，
先调 `POST /__admin/reset` 清空，再发请求。这样单条跑、重复跑、失败重跑都不会串状态。

## 报告与日志

```powershell
pytest
allure generate report/allure_raw -o report/allure_html --clean
allure open report/allure_html
```

- 控制台：每条用例的软断言明细（`[PASS]` / `[FAIL] 期望= 实际=`）
- 日志：`report/logs/dj_api_YYYYMMDD.log`，含完整请求体、响应体、状态码
- Allure：按 feature/story 分组，失败用例可定位到具体断言

`report/` 整个目录在 `.gitignore` 里，不会污染仓库。

## CI

**Docker Compose**

```powershell
docker compose up -d mock-dj          # 只起被测服务
docker compose run --rm api-test      # 起服务 + 跑用例
docker compose down
```

两个容器在同一 compose 网络里，用例容器的 `BASE_URL` 指向服务名 `http://mock-dj:9300`，
不走 `host.docker.internal`。

**Jenkins**

`Jenkinsfile` 分四段：拉代码 → 轮询 `/health` 等服务就绪 → 装依赖 → 执行 pytest。
服务没起来直接失败，不会出现「环境没起、用例全红、以为是代码问题」。
被测服务在宿主机跑时用 `host.docker.internal:9300`，报告由 `post` 段发布 JUnit + Allure。

## 排错对照

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `ConnectionError` / `prepared_env` 里 reset 失败 | 被测服务没起 | `python mock_server/app.py`，或改用 `python run.py` |
| 所有请求 401「签名校验失败」 | `SIGN_CHECK=true` 但两端 `sign_key` 不一致 | 对齐 `config/env.yaml` 的 `sign_key` 与服务端 `SIGN_KEY` |
| 401 且反复重登 | 账号密码错 | 检查 `account`、`SDK_USER` / `SDK_PWD` |
| `ModuleNotFoundError: No module named 'api'` | 直接 `python testcases/test_dj.py` 执行 | 用 `pytest` 从项目根目录跑，`conftest.py` 已补 `sys.path` |
| 「未播放时暂停/切歌」返回 200 | 前面用例留下了播放状态 | 确认用例开头调了 `/__admin/reset` |
| 「切歌」用例对不上曲目 | 歌单被改过 | 歌单固定在 `mock_server/app.py::SONGS`，改曲目要同步 `test_next_song`、`test_prev_song` 的预期 ID |
| `allure` 命令找不到 | 只装了 `allure-pytest`，没装命令行 | 装 allure 命令行；用例本身不受影响 |

## 已知限制

- Mock 服务状态在内存里，重启即清空；多进程并发（`pytest-xdist`）会互相覆盖状态，当前按串行设计。
- 切歌固定按歌单顺序前后移动，`play_mode` 只改状态值，不影响 `next` / `prev` 的实际取曲逻辑。
- 音量与均衡器只做数值与枚举校验，没有音频链路的真实效果验证。
- 没有实现播放进度、收藏、搜索等接口。
