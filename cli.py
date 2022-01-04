# coding: utf-8
import config

from lib.db import db
from lib.db import Credits
from lib.db import Rewards
from lib.db import Clusters
from lib.db import Validators
from lib.db import get_db_validators
from lib.rpc import get_epoch_info
from lib.rpc import get_vote_accounts
from lib.common import fatal_error
from lib.solana import grab_rewards


import asyncio
import asyncclick as click

from aiohttp import ClientSession


async def update_node_credits(db_node, cluster, vote_info):
    # Collect epoch numbers for delete
    epoches_numbers = set()
    insert_queries = []

    for epoch_no, creds_max, creds_min in vote_info["epochCredits"]:
        epoches_numbers.add(epoch_no)

        insert_queries.append(
            Credits.create(validator_id=db_node.id, cluster=cluster.value,
                           epoch_no=epoch_no, credits=(creds_max - creds_min)))

    # Remove all epoch credits from database
    await Credits.delete.where(
        Credits.validator_id == db_node.id and
        Credits.cluster == cluster.value and
        Credits.epoch_no in epoches_numbers
    ).gino.status()

    # Execute all insert queries
    await asyncio.gather(*insert_queries)


async def update_node_rewards(db_node, cluster, cluster_rpc, num_epoches):
    # Collect epoch numbers for delete
    epoches_numbers = set()
    insert_queries = []

    for epoch_no, lamports in grab_rewards(db_node.vote_pk, cluster_rpc):
        epoches_numbers.add(epoch_no)

        insert_queries.append(
            Rewards.create(validator_id=db_node.id, cluster=cluster.value,
                           epoch_no=epoch_no, rewards=lamports))

    # Remove all epoch credits from database
    await Rewards.delete.where(
        Rewards.validator_id == db_node.id and
        Rewards.cluster == cluster.value and
        Rewards.epoch_no in epoches_numbers
    ).gino.status()

    # Execute all insert queries
    await asyncio.gather(*insert_queries)


async def node_get_or_create(vote_info, cluster):
    """ Ensure node exists
    """
    db_node = await Validators.query.where(
        Validators.node_pk == vote_info["nodePubkey"]
    ).gino.first()

    if not db_node:
        db_node = await Validators.create(node_pk=vote_info["nodePubkey"],
                                          vote_pk=vote_info["votePubkey"],
                                          cluster=cluster.value)
    return db_node


async def read_cluster_nodes(cluster, cluster_rpc):
    async with ClientSession() as http:
        cluster_nodes = await get_vote_accounts(
            http=http, cluster_rpc=cluster_rpc, merge=True)

    if not cluster_nodes:
        fatal_error(f"Unable to get vote_accounts for {cluster_rpc}")

    return cluster_nodes


async def update_cluster_credits(cluster, cluster_rpc):
    """ Update vote credits for all cluster nodes
    """
    # Read all database validators
    for vote_info in await read_cluster_nodes(cluster, cluster_rpc):
        db_node = await node_get_or_create(vote_info, cluster)
        await update_node_credits(
            db_node=db_node, cluster=cluster, vote_info=vote_info)


async def update_cluster_rewards(cluster, cluster_rpc, num_epoches):
    """ Update vote rewards for all cluster nodes
    """
    for vote_info in await read_cluster_nodes(cluster, cluster_rpc):
        db_node = await node_get_or_create(vote_info, cluster)
        await update_node_rewards(db_node=db_node, cluster_rpc=cluster_rpc,
                                  cluster=cluster, num_epoches=num_epoches)


@click.group()
async def cli():
    await db.set_bind(config.PG_URL)


@cli.command()
async def update_credits():
    """ Update cluster credits
    """
    click.echo("Update testnet credits")
    await update_cluster_credits(Clusters.testnet, config.TESTNET_RPC_URL)

    click.echo("Update mainnet credits")
    await update_cluster_credits(Clusters.mainnet, config.MAINNET_RPC_URL)


@cli.command()
@click.option('--num-epoches', default=1, help='Number of epoches')
async def update_rewards(num_epoches):
    """ Update cluster rewards
    """
    # click.echo("Update testnet rewards")
    # await update_cluster_rewards(
    #     Clusters.testnet, config.TESTNET_RPC_URL, num_epoches)

    click.echo("Update mainnet rewards")
    await update_cluster_rewards(
        Clusters.mainnet, config.MAINNET_RPC_URL, num_epoches)


@cli.command()
async def update_clusters():
    """ Update cluster info
    """
    click.echo("Update testnet cluster")
    await update_cluster_credits(Clusters.testnet, config.TESTNET_RPC_URL)

    click.echo("Update mainnet cluster")
    await update_cluster_credits(Clusters.mainnet, config.MAINNET_RPC_URL)


if __name__ == '__main__':
    cli(_anyio_backend="asyncio")