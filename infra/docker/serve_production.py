"""Run Uvicorn behind one explicitly trusted proxy peer."""

from ipaddress import ip_address
from os import environ

import uvicorn


if __name__ == "__main__":
    peer = ip_address(environ["FORWARDED_ALLOW_IPS"])
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        proxy_headers=True,
        forwarded_allow_ips=str(peer),
        server_header=False,
        access_log=False,
        limit_concurrency=100,
        timeout_keep_alive=5,
    )
