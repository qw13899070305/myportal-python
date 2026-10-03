"""开发 / 生产启动入口。

监听地址与端口来自配置，默认 ``::``（**真正的双栈**：IPv4 + IPv6 都能连）。

    python app.py                 # 内网可访问，日志会打印具体地址
    HOST=127.0.0.1 python app.py  # 只允许本机
    HOST=0.0.0.0 PORT=9000 python app.py   # 只听 IPv4

启动日志里会直接列出可访问地址，例如：

    监听地址: [::]:8000, 0.0.0.0:8000
    可从以下地址访问本服务（监听 8000）：
      http://192.168.1.2:8000                      [enp6s0 ipv4]
      http://[2409:8a7c:4810:d4e0:2e0:23ff:fe21:5116]:8000   [enp6s0 ipv6]

两个坑都在 :mod:`backend.core.server` 里处理掉了：

1. 必须传**导入字符串**给 uvicorn —— ``reload=True`` 只支持导入字符串，
   传 app 对象时 uvicorn 会直接报错退出（exit code 3）。
2. 必须**自己建监听 socket** —— uvicorn 走 asyncio 建 socket 时会被强制
   设成 ``IPV6_V6ONLY=1``，``host="::"`` 就只监听 IPv6，IPv4 内网连不上。
"""

#: uvicorn 的导入字符串。reload / workers 都依赖它
APP_IMPORT_STRING = "backend.main:app"

if __name__ == "__main__":
    from backend.core.config import settings
    from backend.core.network import log_listening
    from backend.core.server import serve

    # 启动前先把"可以从哪些地址访问"打出来，省得去找 IP
    log_listening(settings.PORT)

    serve(
        APP_IMPORT_STRING,
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        # 经过反向代理时也能拿到真实客户端 IP
        forwarded_allow_ips="*",
    )
