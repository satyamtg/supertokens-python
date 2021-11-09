# Copyright (c) 2021, VRAI Labs and/or its affiliates. All rights reserved.
#
# This software is licensed under the Apache License, Version 2.0 (the
# "License") as published by the Apache Software Foundation.
#
# You may not use this file except in compliance with the License. You may
# obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from typing import Any, Union
from supertokens_python.framework.request import BaseRequest


class FlaskRequest(BaseRequest):

    def __init__(self, req):
        super().__init__()
        self.req = req

    def get_query_param(self, key, default=None):
        return self.req.args.get(key, default)

    async def json(self):
        return self.req.get_json()

    def method(self) -> str:
        if isinstance(self.req, dict):
            return self.req['REQUEST_METHOD']
        return self.req.method

    def get_cookie(self, key: str) -> Union[str, None]:
        return self.req.cookies.get(key, None)

    def get_header(self, key: str) -> Any:
        if isinstance(self.req, dict):
            return self.req.get(key, None)
        return self.req.headers.get(key)

    def url(self):
        return self.req.url

    def get_session(self):
        from flask import g
        if hasattr(g, 'supertokens'):
            return g.supertokens
        return None

    def set_session(self, session):
        from flask import g
        g.supertokens = session

    def get_path(self) -> str:
        if isinstance(self.req, dict):
            return self.req['PATH_INFO']
        return self.req.base_url

    async def form_data(self):
        return self.req.form.to_dict()
