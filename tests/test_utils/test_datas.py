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
from collections import defaultdict
from typing import Optional, Dict, List, Sequence

from lft.consensus.factories import ConsensusVote, ConsensusData


NONE_ID = b"0"


class MockVote(ConsensusVote):
    def is_not(self) -> bool:
        pass

    def is_none(self) -> bool:
        pass

    def __init__(self, data_id: bytes, term_num: int, voter_id: bytes, round_num: int):
        self._data_id = data_id
        self._term_num = term_num
        self._voter_id = voter_id
        self._round_num = round_num
        self._id = self._create_id()

    @property
    def id(self) -> bytes:
        return self._id

    @property
    def data_id(self) -> bytes:
        return self._data_id

    @property
    def term_num(self) -> int:
        return self._term_num

    @property
    def voter_id(self) -> bytes:
        return self._voter_id

    @property
    def round_num(self) -> int:
        return self._round_num

    async def verify(self) -> bool:
        return True

    def _create_id(self) -> bytes:
        return self._voter_id + self._data_id + bytes([self._term_num]) + bytes([self._round_num])


class MockConsensusData(ConsensusData):

    def __init__(self, id_: bytes, prev_id: bytes, proposer: bytes, term_num: int, number: int, round_num: int,
                 votes: Sequence[ConsensusVote]):
        self._id = id_
        self._prev_id = prev_id
        self._proposer = proposer
        self._term_num = term_num
        self._number = number
        self._round_num = round_num
        self._votes = votes

    @property
    def id(self) -> bytes:
        return self._id

    @property
    def prev_id(self) -> bytes:
        return self._prev_id

    @property
    def proposer(self) -> bytes:
        return self._proposer

    @property
    def term_num(self) -> int:
        return self._term_num

    @property
    def number(self) -> int:
        return self._number

    @property
    def round_num(self) -> int:
        return self._round_num

    @property
    def prev_votes(self) -> Sequence['ConsensusVote']:
        return self._votes

    def is_not(self) -> bool:
        return False
