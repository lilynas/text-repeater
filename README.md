# 内容分享 WebUI (Content Share)

一个轻量级的自托管内容分享工具，支持创建文本内容、生成分享链接、配置热加载和历史管理。

## 功能特性

- **内容分享**: 填写任意文本内容，一键生成分享链接
- **链接访问**: 点击链接直接查看原始内容，无需登录
- **过期控制**: 支持设置链接过期时间（1小时 ~ 永不过期）
- **密码保护**: 管理界面需要密码登录，分享链接公开访问
- **配置热加载**: WebUI 中直接修改配置，无需重启即可生效
- **历史管理**: 查看、复制、删除历史分享记录
- **响应式布局**: 左右分栏设计，适配桌面和移动设备

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

```bash
python app.py
```

服务默认运行在 `http://0.0.0.0:8080`

### 访问

- **管理界面**: http://localhost:8080/ (默认密码: `admin123`)
- **分享链接**: http://localhost:8080/s/{short_id}

## 配置说明

配置文件 `config.yaml`:

```yaml
server:
  host: "0.0.0.0"      # 监听地址
  port: 8080           # 监听端口
  debug: false         # 调试模式
  secret_key: "change-this-in-production"  # Session 密钥

auth:
  password: "admin123" # 管理界面登录密码

content:
  default_expire_hours: 24    # 默认过期时间（小时）
  max_content_size: 1048576   # 最大内容大小（字节，默认 1MB）

database:
  path: "./data/content.db"   # SQLite 数据库路径
```

### 配置热加载

在 WebUI 右侧配置区域修改配置后点击保存，以下配置立即生效：
- 管理密码
- 默认过期时间

以下配置需要重启服务：
- 端口
- 监听地址

## 项目结构

```
repeater/
├── app.py              # Flask 主应用
├── config.yaml         # 配置文件
├── requirements.txt    # Python 依赖
├── data/
│   └── content.db      # SQLite 数据库
├── templates/
│   ├── login.html      # 登录页面
│   ├── index.html      # 管理界面
│   └── view.html       # 内容展示页面
├── static/
│   └── style.css       # 样式文件
└── tests/              # pytest 测试
```

## API 接口

| 路由 | 方法 | 说明 | 需要登录 |
|------|------|------|----------|
| `/login` | GET/POST | 登录页面 | 否 |
| `/logout` | GET | 退出登录 | 是 |
| `/` | GET | 管理界面 | 是 |
| `/create` | POST | 创建内容 | 是 |
| `/delete/<id>` | POST | 删除内容 | 是 |
| `/config` | GET/POST | 获取/更新配置 | 是 |
| `/s/<id>` | GET | 查看分享内容 | 否 |

## 运行测试

```bash
python -m pytest -v
```

## 部署建议

### 生产环境

1. 修改 `config.yaml` 中的 `secret_key` 为随机字符串
2. 修改默认密码
3. 使用 Nginx 反向代理并配置 HTTPS
4. 使用 gunicorn 或 uWSGI 运行

```bash
# 使用 gunicorn 运行
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8080 app:app
```

### Nginx 反向代理配置示例

```nginx
server {
    listen 443 ssl;
    server_name share.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 技术栈

- **后端**: Python 3.12+ / Flask 3.0+
- **数据库**: SQLite
- **配置**: YAML
- **前端**: 原生 HTML/CSS/JavaScript

## License

MIT
