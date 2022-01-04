# coding: utf-8

import config

import os
import time
import jinja2
import asyncio
import argparse
import aiohttp_jinja2
from aiohttp import web

from lib.db import db
from lib.db import Clusters
from lib.db import Credits
from lib.db import Rewards
from lib.db import Validators

from lib.db import get_db_credits
from lib.db import get_db_rewards
from lib.db import get_db_validators


loop = asyncio.get_event_loop()


@aiohttp_jinja2.template("index.html")
async def route_index(request):
    return {
        "active_page": "index",

        "clusters": {
            "testnet": {
                "versions_nodes": {}
            },
            "mainnet": {
                "versions_nodes": {}
            }
        }
    }


@aiohttp_jinja2.template("useful.html")
async def route_useful(request):
    return {
        "active_page": "useful",
    }


@aiohttp_jinja2.template("rewards.html")
async def route_rewards(request):
    cluster_name = request.match_info["cluster"]

    rewards, epoches = await get_db_rewards(Clusters[cluster_name],
                                            max_epoches=15)
    return {
        "active_page": "rewards",
        "active_cluster": cluster_name,
        "rewards": rewards,
        "epoches": epoches
    }


@aiohttp_jinja2.template("credits.html")
async def route_credits(request):
    cluster_name = request.match_info["cluster"]

    creds, epoches = await get_db_credits(Clusters[cluster_name], max_epoches=5)

    return {
        "active_page": "credits",
        "active_cluster": cluster_name,
        "credits": creds,
        "epoches": epoches
    }


def web_setup(app) -> web.Application:
    """ Configure routes
    """
    app.router.add_route(
        "GET", "/", route_index, name="index")

    app.router.add_route(
        "GET", "/useful.html", route_useful, name="useful")

    app.router.add_route(
        "GET", "/rewards/{cluster}.html", route_rewards, name="rewards")

    app.router.add_route(
        "GET", "/credits/{cluster}.html", route_credits, name="credits")

    return app


async def runtime_context(request):
    """ Append session data to response
    """
    return {
        "current_url": str(request.url),
        "current_host": str(request.host),
        "current_https_url": str(request.url).replace("http://", "https://"),
        "rel_url": request.rel_url
    }


async def handle_error(code, request, response):
    """ Render error404
    """
    code = 404 if code == 404 else 500
    return aiohttp_jinja2.render_template(f"errors/{code}.html", request, {})


async def errors_middleware(app, handler):
    """ Handle exceptions and store in folder
    """
    async def wraps(request):
        try:
            return await handler(request)
        except web.HTTPException as e:
            if e.status == 404:
                return await handle_error(404, request, e)
            else:
                raise
                return await handle_error(500, request, e)
    return wraps


async def timer_middleware(app, handler):
    """ Setup timer middleware
    """
    async def wraps(request):
        t0 = time.time()
        result = await handler(request)
        result.headers["X-Time-Exec"] = "{:.5f}".format(time.time() - t0)
        return result
    return wraps


async def create_app():
    """ Create web application """

    async def setup_jinja2(app) -> web.Application:
        """ Initialize Jinja2
        """
        cache_dir = config.CACHE_JINJA2_DIR
        theme_dir = os.path.abspath("templates")

        if cache_dir:
            if not os.path.exists(config.CACHE_JINJA2_DIR):
                os.mkdir(config.CACHE_JINJA2_DIR, 0o700)

            aiohttp_jinja2.setup(
                app,
                loader=jinja2.FileSystemLoader(theme_dir),
                bytecode_cache=jinja2.FileSystemBytecodeCache(cache_dir),
                context_processors=[
                    runtime_context,
                    aiohttp_jinja2.request_processor
                ]
            )

        aiohttp_jinja2.setup(
            app,
            app_key="uncache",
            loader=jinja2.FileSystemLoader(theme_dir),
            context_processors=[
                runtime_context,
                aiohttp_jinja2.request_processor
            ]
        )

        return app

    app = web.Application(
        middlewares=[
            db,
            errors_middleware,
            timer_middleware,
        ]
    )
    db.init_app(app, dict(dsn=config.PG_URL))

    async def create(app_):
        await db.gino.create_all()

    app.on_startup.append(create)

    app = await setup_jinja2(app)

    app = web_setup(app)
    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("port", type=int)
    args = parser.parse_args()
    host, port = args.host, args.port

    try:
        srv = loop.run_until_complete(create_app())
        web.run_app(srv, host=host, port=port)
    except KeyboardInterrupt:
        loop.close()

