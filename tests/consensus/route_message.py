from typing import Tuple, List
from unittest.mock import patch, MagicMock

import pytest

from lft.app.data import DefaultData
from lft.consensus.election import Election
from lft.consensus.messages.data import Data
from lft.consensus.messages.vote import Vote, VoteFactory
from lft.consensus.round import Round
from tests.consensus.setup_consensus import setup_consensus


@pytest.mark.asyncio
async def test_route_message_to_round():
    # GIVEN
    consensus, voters, vote_factories, epoch, genesis_data = await setup_consensus()

    # Advance round for test three case
    round_layer = MagicMock(Election(consensus._node_id, epoch, 0, consensus._event_system,
                                     consensus._data_factory, consensus._vote_factory,
                                     consensus._data_pool, consensus._vote_pool))
    new_round = MagicMock(Round(round_layer, consensus._node_id, epoch, 0,
                                consensus._event_system, consensus._data_factory, consensus._vote_factory))
    consensus._round_pool.first_round = MagicMock(return_value=new_round)
    consensus.round_start(epoch, 1)

    # WHEN
    # Three cases one is now round, other one is future round, another is past but acceptable round
    for i in range(3):
        data, votes = await create_sample_items_by_index(i, genesis_data, vote_factories, voters)
        await consensus.receive_data(data)
        for vote in votes:
            await consensus.receive_vote(vote)

    # THEN
    assert len(consensus._round_pool.get_round.call_args_list) == 15 + 8  # live data and prev_votes
    for i in range(3):
        data, votes = await create_sample_items_by_index(i, genesis_data, vote_factories, voters)
        # consensus._round_pool.get_round.


async def create_sample_items_by_index(index: int, genesis_data: Data, vote_factories: List[VoteFactory],
                                       voters: List[bytes]) -> Tuple[Data, List[Vote]]:
    data_id = b'id' + bytes([index+2])
    prev_id = b'id' + bytes([index+1])
    commit_id = b'id' + bytes([index])

    if index == 0:
        prev_votes = []
    else:
        prev_votes = [await vote_factory.create_vote(prev_id, commit_id, 1, index-1)
                      for vote_factory in vote_factories]

    data = DefaultData(
        id_=data_id,
        prev_id=prev_id,
        proposer_id=voters[0],
        number=index+1,
        epoch_num=1,
        round_num=index,
        prev_votes=prev_votes
    )
    votes = [await vote_factory.create_vote(data_id, prev_id, 1, index) for vote_factory in vote_factories]

    return data, votes
