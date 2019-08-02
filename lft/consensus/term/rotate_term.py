# -*- coding: utf-8 -*-

# Copyright 2019 ICON Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import math
from typing import Sequence

from lft.consensus.factories import ConsensusData, ConsensusVote
from lft.consensus.term import Term
from lft.consensus.term.term import InvalidProposer, InvalidVoter


class RotateTerm(Term):
    def __init__(self, num: int, voters: Sequence[bytes], rotate_bound: int = 1):
        self._num = num
        self._rotate_bound = rotate_bound
        self._voters = tuple(voters)

    @property
    def num(self) -> int:
        return self._num

    @property
    def quorum_num(self) -> int:
        return math.ceil(len(self._voters) * 0.67)

    def verify_data(self, data: ConsensusData):
        self.verify_proposer(data.proposer_id, data.round_num)
        for i, vote in data.prev_votes:
            self.verify_vote(vote, i)

    def verify_vote(self, vote: ConsensusVote, vote_index: int = -1):
        self.verify_voter(vote.voter_id, vote_index)

    def verify_proposer(self, proposer_id: bytes, round_num: int):
        expected = self.get_proposer_id(round_num)
        if proposer_id != expected:
            raise InvalidProposer(proposer_id, expected)

    def verify_voter(self, voter: bytes, vote_index: int = -1):
        if vote_index >= 0:
            expected = self.get_voter_id(vote_index)
            if voter != expected:
                raise InvalidVoter(voter, expected)
        else:
            if voter not in self._voters:
                raise InvalidVoter(voter, bytes(0))

    def get_proposer_id(self, round_num: int) -> bytes:
        return self._voters[round_num // self._rotate_bound % len(self._voters)]

    def get_voter_id(self, vote_index: int):
        return self._voters[vote_index]

    def get_voters_id(self) -> Sequence[bytes]:
        return self._voters