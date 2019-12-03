import logging
from typing import OrderedDict, Optional, TYPE_CHECKING
from lft.consensus.messages.data import Data, DataFactory
from lft.consensus.messages.vote import Vote, VoteFactory
from lft.consensus.events import ReceiveDataEvent, ReceiveVoteEvent
from lft.consensus.term import Term
from lft.consensus.layers.sync import SyncMessages
from lft.consensus.exceptions import InvalidRound, InvalidTerm, AlreadyProposed, AlreadyVoted
from lft.event import EventSystem
from lft.event.mediators import DelayedEventMediator


if TYPE_CHECKING:
    from lft.consensus.layers.round import RoundLayer

__all__ = ("SyncLayer",)

TIMEOUT_PROPOSE = 2.0
TIMEOUT_VOTE = 2.0


class SyncLayer:
    def __init__(self,
                 round_layer: 'RoundLayer',
                 node_id: bytes,
                 term: Term,
                 round_num: int,
                 event_system: EventSystem,
                 data_factory: DataFactory,
                 vote_factory: VoteFactory):
        self._round_layer = round_layer
        self._node_id = node_id

        self._term = term
        self._round_num = round_num

        self._event_system = event_system
        self._data_factory = data_factory
        self._vote_factory = vote_factory
        self._logger = logging.getLogger(node_id.hex())

        self._messages = SyncMessages()

        self._vote_timeout_started = False

    async def round_start(self):
        await self._new_unreal_datums()
        await self._round_layer.round_start()

    async def receive_data(self, data: Data):
        try:
            await self._receive_data(data)
        except (InvalidTerm, InvalidRound, AlreadyProposed):
            pass

    async def receive_vote(self, vote: Vote):
        try:
            await self._receive_vote(vote)
        except (InvalidTerm, InvalidRound, AlreadyVoted):
            pass

    async def _receive_data(self, data: Data):
        self._verify_acceptable_data(data)

        self._messages.add_data(data)
        await self._round_layer.receive_data(data)
        await self._receive_votes_if_exist(data)

    async def _receive_vote(self, vote: Vote):
        self._verify_acceptable_vote(vote)

        self._messages.add_vote(vote)
        await self._receive_vote_if_data_exist(vote)
        await self._raise_lazy_votes_if_available()

    async def _raise_receive_data(self, delay: float, data: Data):
        event = ReceiveDataEvent(data)
        event.deterministic = False

        mediator = self._event_system.get_mediator(DelayedEventMediator)
        mediator.execute(delay, event)

    async def _raise_receive_vote(self, delay: float, vote: Vote):
        event = ReceiveVoteEvent(vote)
        event.deterministic = False

        mediator = self._event_system.get_mediator(DelayedEventMediator)
        mediator.execute(delay, event)

    async def _raise_lazy_votes_if_available(self):
        if self._vote_timeout_started:
            return
        if not self._messages.reach_quorum(self._term.quorum_num):
            return
        if self._messages.reach_quorum_consensus(self._term.quorum_num):
            return

        self._vote_timeout_started = True
        for voter in self._term.get_voters_id():
            vote = await self._vote_factory.create_lazy_vote(voter, self._term.num, self._round_num)
            await self._raise_receive_vote(delay=TIMEOUT_VOTE, vote=vote)

    async def _new_unreal_datums(self):
        none_data = await self._data_factory.create_none_data(term_num=self._term.num,
                                                              round_num=self._round_num,
                                                              proposer_id=self._term.get_proposer_id(self._round_num))
        # NoneData must be received before RoundStart
        await self._receive_data(none_data)

        expected_proposer = self._term.get_proposer_id(self._round_num)
        lazy_data = await self._data_factory.create_lazy_data(self._term.num,
                                                              self._round_num,
                                                              expected_proposer)
        await self._raise_receive_data(delay=TIMEOUT_PROPOSE, data=lazy_data)

    async def _receive_votes_if_exist(self, data: Data):
        votes_by_data_id = self._messages.get_votes(data_id=data.id)
        for vote in votes_by_data_id.values():
            await self._round_layer.receive_vote(vote)

    async def _receive_vote_if_data_exist(self, vote: Vote):
        if self._messages.get_data(vote.data_id):
            await self._round_layer.receive_vote(vote)

    def _verify_acceptable_data(self, data: Data):
        if self._term.num != data.term_num:
            raise InvalidTerm(data.term_num, self._term.num)
        if self._round_num != data.round_num:
            raise InvalidRound(data.term_num, data.round_num, self._term.num, self._round_num)
        if data in self._messages:
            raise AlreadyProposed(data.id, data.proposer_id)

    def _verify_acceptable_vote(self, vote: Vote):
        if self._term.num != vote.term_num:
            raise InvalidTerm(vote.term_num, self._term.num)
        if self._round_num != vote.round_num:
            raise InvalidRound(vote.term_num, vote.round_num, self._term.num, self._round_num)
        if vote in self._messages:
            raise AlreadyVoted(vote.id, vote.voter_id)
