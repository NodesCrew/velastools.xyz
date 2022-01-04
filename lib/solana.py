# coding: utf-8
import json
import datetime
import subprocess


def grab_rewards(vote_account, rpc_url, num_epoches=None):
    print(f"[{datetime.datetime.utcnow()}]: grab rewards for {vote_account}")

    if not num_epoches or num_epoches > 10 or num_epoches < 1:
        num_epoches = 10

    command = [
        "velas",
        "vote-account",  vote_account,
        "--url", rpc_url,
        "--with-rewards",
        "--num-rewards-epochs", f"{num_epoches}",
        "--output", "json"
    ]

    data = subprocess.check_output(command)

    for epoch_info in json.loads(data.decode())["epochRewards"]:
        yield epoch_info["epoch"], epoch_info["amount"]