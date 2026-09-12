# Microblog

基于 Flask 的类 Twitter 社交平台，涵盖用户认证、关注体系、私信通知、全文搜索、REST API、国际化与异步任务队列，并针对真实瓶颈完成了一轮系统的性能优化（吞吐量提升 6.5 倍）。

## 功能特性

- **用户系统**：注册 / 登录 / 密码重置（PyJWT 签发限时 Token）、密码加盐慢哈希存储、CSRF 防护
- **社交体系**：关注 / 取关（多对多自引用）、聚合时间线（本人 + 关注者动态联合查询）、用户主页
- **内容与互动**：动态发布（140 字限制 + 语言自动检测）、未读私信、站内通知（AJAX 轮询）
- **全文搜索**：Elasticsearch 倒排索引，通过 SQLAlchemy 事件钩子（before_commit / after_commit）自动同步索引，未配置 ES 时自动降级为纯数据库模式
- **REST API**：Token 认证（Basic Auth 换发 / 吊销）、用户资源 CRUD、HAL 风格分页元数据、HTML/JSON 自适应错误响应
- **国际化**：Flask-Babel 中英双语 + 腾讯云机器翻译（自动识别源语言）
- **异步任务**：Redis + RQ 任务队列处理邮件发送，独立 Worker 消费，Redis 不可用时自动降级为线程发送

## 技术栈

| 层       | 技术                                                                        |
| -------- | --------------------------------------------------------------------------- |
| 框架     | Flask 3（应用工厂 + 蓝图）                                                  |
| 数据库   | SQLAlchemy 2.0（Mapped 注解）+ Flask-Migrate（Alembic）+ SQLite（WAL 模式） |
| 异步任务 | Redis + RQ，Windows 兼容 SimpleWorker                                       |
| 搜索     | Elasticsearch 9                                                             |
| 认证     | Flask-Login + Werkzeug + PyJWT                                              |
| 部署     | waitress（生产级多线程 WSGI）                                               |
| 测试     | unittest + fakeredis（自包含，无需外部服务）                                |

## 性能优化

编写多级并发压测脚本（1 → 500 并发逐级加压，统计 RPS / P95 / P99 / 错误率），定位并消除瓶颈：

| 指标             | 优化前                | 优化后                 |
| ---------------- | --------------------- | ---------------------- |
| 读吞吐天花板     | ~75 RPS               | **~485 RPS**（6.5 倍） |
| 10 并发 P95 延迟 | 752 ms                | **31 ms**              |
| 500 并发         | 延迟劣化至 9s，不可用 | **0 错误**，P95 1.07s  |

三层优化：

1. **代码层**：`before_request` 钩子原实现每请求都写 `last_seen`，导致纯读页面也触发 SQLite 单写锁排队——改为 60 秒节流，消除绝大部分写事务
2. **数据库层**：SQLite 开启 WAL 模式（读写不互斥）+ `busy_timeout` + `synchronous=NORMAL`
3. **服务器层**：Flask 开发服务器（无 keep-alive、单进程）替换为 waitress 多线程 WSGI

压测脚本见 [`_load_test.py`](_load_test.py)，复现方法：`python _load_test.py --server waitress`

## 快速开始

### 环境要求

- Python 3.10+
- （可选）Redis：异步邮件任务队列，未运行时自动降级为线程发送
- （可选）Elasticsearch：全文搜索，未配置时自动降级
- （可选）腾讯云 API 密钥：动态翻译功能

### 安装

```bash
git clone https://github.com/ruohuan417/microblog.git
cd microblog
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### 配置

复制 `.env.example` 为 `.env` 并填写（所有外部服务均可选）：

```ini
SECRET_KEY=change-me
MAIL_SERVER=smtp.example.com   # 密码重置邮件需要
ADMINS=admin@example.com
REDIS_URL=redis://localhost:6379/0
ELASTICSEARCH_URL=             # 留空则禁用 ES
```

### 初始化数据库并运行

```bash
flask db upgrade               # 应用数据库迁移
flask shell                    # 创建初始用户
>>> u = User(username='demo', email='demo@example.com')
>>> u.set_password('your-password')
>>> db.session.add(u); db.session.commit()

# 开发模式
flask run

# 生产模式（waitress 多线程）
waitress-serve --host=0.0.0.0 --port=5000 --threads=16 microblog:app
```

### 启动异步任务 Worker（可选）

```bash
python run_worker.py
```

> Windows 下 rq 默认 Worker 依赖 fork，本项目的 `run_worker.py` 已使用 `SimpleWorker` 兼容。

## 测试

测试套件完全自包含（内存数据库、禁用 ES、fakeredis 模拟 Redis），无需任何外部服务：

```bash
python -m unittest tests -v
```

覆盖：密码哈希、Gravatar、关注关系、关注流排序、邮件任务的线程降级路径与入队参数校验。

## 项目结构

```
microblog/
├── app/
│   ├── __init__.py        # 应用工厂、扩展初始化、SQLite WAL、日志
│   ├── models.py          # User / Post / Message / Notification + SearchableMixin
│   ├── email.py           # RQ 异步邮件 + 线程降级
│   ├── search.py          # Elasticsearch 索引封装
│   ├── translate.py       # 腾讯云 TMT 翻译
│   ├── auth/              # 认证蓝图（登录/注册/密码重置）
│   ├── main/              # 主蓝图（动态/关注/私信/通知/搜索）
│   ├── api/               # REST API 蓝图
│   ├── errors/            # 错误处理蓝图
│   └── templates/         # Jinja2 模板 + i18n
├── migrations/            # Alembic 数据库迁移
├── config.py              # 配置（全部经环境变量注入）
├── tests.py               # 单元测试（自包含）
├── run_worker.py          # RQ Worker 启动脚本（Windows 兼容）
└── _load_test.py          # 并发压测脚本
```
