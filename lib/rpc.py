# coding: utf-8

import json
from lib.common import fatal_error


async def call_rpc(params, http, cluster_rpc=None):
    """ Send request to RPC endpoint and returns result
    """
    response = await http.post(
        cluster_rpc,
        data=json.dumps({"jsonrpc": "2.0", "id": 1, **params}),
        headers={"Content-Type": "application/json"}
    )

    try:
        json_ = await response.json()
        return json_["result"]
    except Exception as e:
        fatal_error("Unable to parse response: status=%s, text=%s\n%s" % (
            response.status_code, response.text, e))

    fatal_error("Unable to call: %s" % {"jsonrpc": "2.0", "id": 1, **params})


async def get_balance(http, cluster_rpc, account):
    """ Get balance in lamports
    """
    result = await call_rpc({"method": "getBalance", "params": [account]},
                            http=http, cluster_rpc=cluster_rpc)
    return result["value"]


async def get_epoch_info(http, cluster_rpc):
    """ Get current epoch number from  RPC
    """
    return await call_rpc({"method": "getEpochInfo"},
                          http=http, cluster_rpc=cluster_rpc)


async def get_epoch_number(http, cluster_rpc):
    """ Get current epoch number from testnet RPC
    """
    data = await get_epoch_info(http=http, cluster_rpc=cluster_rpc)
    return data["epoch"]


async def get_slots_info(http, cluster_rpc):
    """ Get current slot in epoch
    """
    epoch_info = await call_rpc({"method": "getEpochInfo"},
                                http=http, cluster_rpc=cluster_rpc)

    return epoch_info["slotIndex"], epoch_info["slotsInEpoch"]


async def get_cluster_nodes(http, cluster_rpc):
    """ Get cluster nodes
    """
    return await call_rpc({"method": "getClusterNodes"},
                          http=http, cluster_rpc=cluster_rpc)


async def get_vote_accounts(http, cluster_rpc, merge=False):
    """ Returns validators
    """
    voters = await call_rpc({"method": "getVoteAccounts"},
                            http=http, cluster_rpc=cluster_rpc)

    if not merge:
        return voters

    return [*voters["current"], *voters["delinquent"]]
