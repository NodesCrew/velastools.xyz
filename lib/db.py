# coding: utf-8

import enum
from dataclasses import dataclass
from collections import defaultdict

from gino.ext.aiohttp import Gino


db = Gino()


class Clusters(enum.Enum):
    devnet = 0
    testnet = 1
    mainnet = 2


class Validators(db.Model):
    __tablename__ = "validators"

    id = db.Column(db.BigInteger(), primary_key=True)
    node_pk = db.Column(db.Unicode())
    vote_pk = db.Column(db.Unicode())
    cluster = db.Column(db.SmallInteger)


class Rewards(db.Model):
    __tablename__ = "rewards"

    validator_id = db.Column(db.Integer, db.ForeignKey("validators.id"))
    cluster = db.Column(db.SmallInteger)
    epoch_no = db.Column(db.SmallInteger)
    rewards = db.Column(db.BigInteger)


class Credits(db.Model):
    __tablename__ = "credits"

    validator_id = db.Column(db.Integer, db.ForeignKey("validators.id"))
    cluster = db.Column(db.SmallInteger)
    epoch_no = db.Column(db.SmallInteger)
    credits = db.Column(db.BigInteger)


@dataclass
class ValidatorCredits:
    id_: int
    node_pk: str
    vote_pk: str
    credits: dict


@dataclass
class ValidatorRewards:
    id_: int
    node_pk: str
    vote_pk: str
    rewards: dict


async def get_db_validators(cluster):
    validators = []
    q = Validators.query.where(Validators.cluster == cluster.value)
    for row in await q.gino.all():
        validators.append(row)
    return validators


async def get_db_credits(cluster, max_epoches=5):
    epoches = set()
    vals_creds = dict()

    # Find max epoch_no with strange method due max func difficultes
    # todo: rewrite with db.max fumction
    most_fresh_credits = await Credits.query.where(
        Credits.cluster == cluster.value
    ).order_by(
        db.desc(Credits.epoch_no)
    ).gino.first()

    # Find all credits for epoch_no > max_epoch_no and cluster
    q = db.select(
        [
            Validators.id,
            Validators.node_pk,
            Validators.vote_pk,
            Credits.epoch_no,
            Credits.credits,
        ]
    ).select_from(
        Credits.join(Validators)
    ).where(
        db.and_(
            Credits.cluster == cluster.value,
            Credits.epoch_no > (most_fresh_credits.epoch_no - max_epoches)
        )
    )

    for row in await q.gino.all():
        val_id, node_pk, vote_pk, epoch_no, creds = row
        epoches.add(epoch_no)
        if val_id not in vals_creds:
            vals_creds[val_id] = ValidatorCredits(
                id_=val_id, node_pk=node_pk, vote_pk=vote_pk, credits=dict())
        vals_creds[val_id].credits[epoch_no] = creds
    return vals_creds, list(sorted(epoches))


async def get_db_rewards(cluster, max_epoches=5):
    epoches = set()
    vals_rewards = dict()

    most_fresh_record = await Rewards.query.where(
        Rewards.cluster == cluster.value
    ).order_by(
        db.desc(Rewards.epoch_no)
    ).gino.first()

    # Find all credits for epoch_no > max_epoch_no and cluster
    q = db.select(
        [
            Validators.id,
            Validators.node_pk,
            Validators.vote_pk,
            Rewards.epoch_no,
            Rewards.rewards,
        ]
    ).select_from(
        Rewards.join(Validators)
    ).where(
        db.and_(
            Rewards.cluster == cluster.value,
            Rewards.epoch_no > (most_fresh_record.epoch_no - max_epoches)
        )
    )

    for row in await q.gino.all():
        val_id, node_pk, vote_pk, epoch_no, rewards = row
        epoches.add(epoch_no)
        if val_id not in vals_rewards:
            vals_rewards[val_id] = ValidatorRewards(
                id_=val_id, node_pk=node_pk, vote_pk=vote_pk, rewards=dict())
        vals_rewards[val_id].rewards[epoch_no] = float(
            "%.2f" % (rewards / 1_000_000_000))
    return vals_rewards, list(sorted(epoches))
