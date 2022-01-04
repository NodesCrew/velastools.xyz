# coding: utf-8

MAINNET_RPC_URL = "https://api.velas.com"
TESTNET_RPC_URL = "https://api.testnet.velas.com"


PG_URL = "postgresql://{user}:{password}@{host}:{port}/{database}".format(
    host="localhost",
    port=5432,
    user="postgres",
    password="",
    database="velastools",
)

CACHE_JINJA2_DIR = "/tmp/velastools.xyz_jinja2"
