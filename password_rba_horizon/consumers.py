# Copyright 2022 Vincent Unsel & Stephan Wiefling
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import logging
import secrets
import time

from channels.generic.websocket import WebsocketConsumer
from django.conf import settings

LOG = logging.getLogger(__name__)


class RoundTripTimeConsumer(WebsocketConsumer):
    round_trips = {}

    def connect(self):
        if self.scope['session'].session_key is None:
            self.close()
        else:
            self.accept()
            self.scope['session']['rtt'] = None
            records = self.round_trips.setdefault(
                self.scope['session'].session_key, {})
            records.setdefault('rtts', [])
            self.start_measurement()

    def start_measurement(self):
        token = secrets.token_urlsafe(32)
        start_time = time.perf_counter()
        self.send(token)
        self.round_trips[self.scope['session'].session_key
                         ].setdefault(token, start_time)

    def receive(self, text_data=None):
        end_time = time.perf_counter()
        try:
            start_time = self.round_trips[
                self.scope['session'].session_key][text_data]
            rtt = end_time - start_time
            rtt *= 1000
            self.round_trips[
                self.scope['session'].session_key]['rtts'].append(rtt)
        except KeyError:
            self.close()
        else:
            if len(self.round_trips[self.scope['session'].session_key]['rtts']) < 5:
                self.start_measurement()
            else:
                self.close()

    def disconnect(self, close_code):
        if self.scope['session'].session_key is not None:
            lowest_value = min(self.round_trips[
                self.scope['session'].session_key]['rtts'])
            if isinstance(lowest_value, float):
                self.scope['session']['rtt'] = str(round(lowest_value))
                self.scope['session'].save()
                self.scope['session'].modified = True
            del self.round_trips[self.scope['session'].session_key]
