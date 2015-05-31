#!/usr/bin/env python3
"""
Lets-Chat API for Python. Useful for writing clients, bots, or microservice integrations.
"""

import requests

class Room:
    def __init__(self, api, id, slug, name, description, created, lastActive, owner):
        self.api = api
        self.id = id
        self.slug = slug
        self._name = name
        self._description = description
        self.created = created
        self.lastActive = lastActive
        self.owner = owner
        self._last_seen = ''
        try:
            # Try to make _last_seen the most recent message so bots using this
            # don't accidentally re-answer old messages every time they spin up.
            most_recent = self.api.get_messages(self.id, take=1)[0]
            self._last_seen = most_recent['id']
        except IndexError:
            # Assuming that the room hasn't yet been posted in.
            pass

    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, new_name):
        self.api.update_room(self.slug, name=new_name)

    @property
    def description(self):
        return self._description
    
    @description.setter
    def description(self, new_description):
        self.api.update_room(self.slug, description=new_description)
        
    @property
    def messages(self):
        return self.api.get_messages(self.id, reverse=False,
            expand_owner = True, expand_room = True)
    
    def unread(self):
        m = self.api.get_messages(self.id, since_id=self._last_seen,
            reverse=False, expand_owner = True, expand_room = True)
        if m:
            self._last_seen = m[-1]['id']
        return m
        
    def post(self, message):
        return self.api.make_message(self.id, message)

class LetsChatAPI:
    def __init__(self, endpoint, token):
        self.endpoint = endpoint.rstrip().rstrip("/")
        self.token = token
    
    def _make_call(self, method: str, api_bits: list, params: dict = {})->(list, dict, None):
        """
        method should be 'post', 'put', 'get', 'delete'.
        api_bits should be a tuple of strings for each part of the API URL, which
        get combined with self.endpoint to form the full API endpoint.
        Params is dealt with in the usual way for requests.
        """
        req_method = {
            'get': requests.get,
            'post': requests.post,
            'put': requests.put,
            'delete': requests.delete
        }[method.lower()]
        final_ep = self.endpoint + '/' + '/'.join(api_bits)
        call = req_method(final_ep, auth=(self.token, 'password not needed'), params=params)
        call.raise_for_status()
        if call.text:
            return call.json()
        else:
            return None
    
    def get_rooms(self, room=None, skip=None, take=None):
        if room:
            # Single-room usage
            return self._make_call('get', ['rooms', room])
        else:
            params = {}
            if skip:
                params['skip'] = skip
            if take:
                params['take'] = take
            return self._make_call('get', ['rooms'], params)

    @property
    def rooms(self):
        return {v['slug']: Room(self, **v) for v in self.get_rooms()}
    
    def make_room(self, name: str, slug: str, description: str)->dict:
        return self._make_call('post', ['rooms'], {
                'name': name,
                'slug': slug,
                'description': description
            })
    
    def update_room(self, room_slug: str, name: str=None, description: str=None)->None:
        params = {}
        if name is not None:
            params['name'] = name
        if description is not None:
            params['description'] = description
        return self._make_call('put', ['rooms', room_slug], params)

    def remove_room(self, room_slug: str)->None:
        return self._make_call('delete', ['rooms', room_slug])
    
    def get_room_users(self, room_slug: str)->list:
        return self._make_call('get', ['rooms', room_slug, 'users'])

    def get_messages(self,  room_id: str, # Filter by room; id only?
                            since_id: str = None,  # Since message with this ID
                            from_: str = None, # Format: 2015-02-02T01:43:19Z
                            to: str = None, # Same as from
                            skip: int = 0, # How many messages to discard
                            take: int = 500, # How many messages to retrieve
                            reverse: bool = True, # Whether to reverse
                            expand_owner: bool = False,  # Expand ownerid to user object
                            expand_room:  bool = False # Expand roomid to room object
                            )->list:
        """
        Gets messages, optionally filtering by one or many parameters.
        
        room_id (str): Filter rooms by Room ID.
        since_id (str): Returns results with an ID greater than (more recent than)
            the specified ID.
        from (str): Returns results with a posted date greater than (more recent
            than) the specified date. Format: 2015-02-02T01:43:19Z
        to (str): Returns results with a posted date less than or equal to the
            specified date. Same format as 'from'
        skip (int): Specifies the number of messages to skip
        take (int): Specifies the number of messages to return (Max: 5000)
        reverse (bool): Reverses order of messages (default is True)
        expand_owner (bool): Include detailed information for owner 
        expand_room (bool): Include detailed information for room 
        """
        params = {'room': room_id}
        if since_id is not None:
            params['since_id'] = since_id
        if from_ is not None:
            params['from'] = from_
        if to is not None:
            params['to'] = to
        if skip != 0:
            params['skip'] = skip
        if take != 500:
            params['take'] = take
        if not reverse:
            params['reverse'] = reverse
        expands = ''
        if expand_owner:
            expands = 'owner'
        if expand_room:
            if expands:
                expands += ','
            expands += 'room'
        if expands:
            params['expand'] = expands
        return self._make_call('get', ['messages'], params)

    def make_message(self, room_id: str, text: str)->dict:
        return self._make_call('post', ['messages'], {'text':text, 'room':room_id})
    
    def get_files(self, room_id: str, skip: int = 0, take: int = 500)->list:
        params = {'room': room_id}
        if skip != 0:
            params['skip'] = skip
        if take != 500:
            params['take'] = take
        return self._make_call('get', ['files'], params)

    def get_users(self, skip: int = 0, take: int = 500)->list:
        params = {}
        if skip != 0:
            params['skip'] = skip
        if take != 500:
            params['take'] = take
        return self._make_call('get', ['users'], params)
        
    def get_user(self, user_id: str)->dict:
        return self._make_call('get', ['users', user_id])

    def get_account(self)->dict:
        return self._make_call('get', ['account'])

