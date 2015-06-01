#!/usr/bin/env python3
"""
Lets-Chat API for Python. Useful for writing clients, bots, or microservice integrations.
"""

import requests
import imghdr

def _guess_img_mimetype(filename):
    img_type = imghdr.what(filename)
    if img_type is None:
        raise ValueError("File contents are not recognisable as an image")
    return {
            'rgb': 'image/x-rgb',
            'gif': 'image/gif',
            'png': 'image/png',
            'pbm': 'x-pbm',
            'pgm': 'x-pgm',
            'ppm': 'x-ppm',
            'tiff': 'image/tiff',
            'rast': 'image/x-rast',
            'xbm': 'image/xbm',
            'jpeg': 'image/jpeg',
            'bmp': 'image/bmp'
        }[img_type]

class Account:
    """
    Wraps an account to provide convenience properties that assist in working with
    API generated data. Can also fetch/store Gravatars, but this is done only when
    the self.gravatar property is first accessed.
    """
    def __init__(self, api, username, id, displayName, avatar, firstName='', lastName=''):
        self.api = api
        self.username = username
        self.id = id
        self.displayName = displayName
        self.firstName = firstName
        self.lastName = lastName
        self.avatar = avatar
        self._gravatar = b''
        
    @property
    def gravatar_url(self)->str:
        return 'https://www.gravatar.com/avatar/{}'.format(self.avatar)

    @property
    def gravatar(self)->bytes:
        if not self._gravatar:
            r = requests.get(self.gravatar_url)
            r.raise_for_status()
            self._gravatar = r.content
        return self._gravatar


class File:
    """
    Wraps a file object as returned by the API, allowing authenticated download
    of file content.
    """
    def __init__(self,  api: 'API object',
                        id: str, 
                        name: str, 
                        owner: str, 
                        room: str, 
                        size: str, 
                        type: str, 
                        uploaded: str, 
                        url: str):
        self.api = api
        self.id = id
        self.name = name
        self.owner = Account(self.api, api.get_user(owner))
        self.room = room
        self.size = size
        self.type = type
        self.uploaded = uploaded
        self.url = url
        self._content = b''
    
    def content(self):
        if not self._content:
            auth = (self.api.token, "!")
            r = requests.get(self.api.endpoint + "/" + self.url, auth=auth)
            r.raise_for_status()
            self._content = r.content
        return self._content

class Message:
    """
    Wraps a message to provide convenience properties and functions.
    
    Messages 'belong' to their parent room and grandparent API, and have both as
    properties.
    """
    def __init__(self,  api: 'API object',
                        parent_room: 'Room object',
                        room: str,
                        id: str,
                        text: str,
                        posted: str,
                        owner: dict):
        self.api = api
        self.room = parent_room
        self.room_id = room
        self.id = id
        self.text = text
        self.posted = posted
        self.owner = Account(api, **owner)
        
    def __str__(self):
        return '{}: {}'.format(self.owner.username, self.text)

    def __repr__(self):
        return 'Message<#{}: "{}">'.format(self.room.slug, str(self)[:18])

    def reply(self, message)->dict:
        """
        Reply to this message, beginning with an @mention of the replied-to author.
        
        eg, calling Message.reply("I denounce thee!") on something written by
        a user named heretic14 would result in "@heretic14: I denounce thee!".
        """
        return self.room.post('@{}: {}'.format(self.owner.username, message))


class Room:
    def __init__(self, api, id, slug, name, description, created, lastActive, owner):
        """
        Represents a room on the LetsChat server. Provides methods for sending/
        reading messages, and convenient properties for reading/writing "name"
        and "description" settings for the Room (i.e. assignment to self.name or
        self.description triggers an API call to make the change on server-side).
        """
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
    def users(self)->[Account]:
        return [Account(self.api, **u) for u in self.api.get_room_users(self.slug)]
    
    @property
    def files(self)->[File]:
        return [File(self.api, **F) for F in self.api.get_files(self.id)]

    @property
    def name(self)->str:
        return self._name
    
    @name.setter
    def name(self, new_name):
        self.api.update_room(self.slug, name=new_name)

    @property
    def description(self)->str:
        return self._description
    
    @description.setter
    def description(self, new_description):
        self.api.update_room(self.slug, description=new_description)
        
    @property
    def messages(self)->[Message]:
        "Returns up to 500 messages from this channel."
        m = self.api.get_messages(self.id, reverse=False,
            expand_owner = True, expand_room = True)
        return [Message(self.api, self, **msg) for msg in m]
    
    def unread(self)->[Message]:
        "Return messages since last-seen *or* the message preceding joining room."
        m = self.api.get_messages(self.id, since_id=self._last_seen,
            reverse=False, expand_owner = True, expand_room = True)
        if m:
            self._last_seen = m[-1]['id']
        return [Message(self.api, self, **msg) for msg in m]
        
    def post(self, message)->dict:
        """
        Simply post a message to this room. This message will be among those
        returned by self.unread (changing this behaviour would require complex
        hacks to avoid accidentally missing messages posted by others).
        
        Returns the message object, with "room" and "owner" unexpanded.
        """
        return self.api.make_message(self.id, message)

    def post_image(self, filename)->dict:
        "Given an image file-name, guess mimetype and post using given filename."
        with open(filename, 'rb') as img:
            mimetype = _guess_img_mimetype(filename)
            img.seek(0)
            return self.api.post_file(self.id, img, filename, mimetype)


class API:
    def __init__(self, endpoint: str, token: str):
        """
        endpoint: The base URI for the lets-chat server, such as 'http://localhost:5000'
        token: The API token generated by the user.
        """
        self.endpoint = endpoint.rstrip().rstrip("/")
        self.token = token
        self._rooms = {}
        _ = self.rooms  # Initialise the property

    def __repr__(self):
        return "API('{}', <{}>)".format(self.endpoint, self.account.username)
    
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
        for room_dict in self.get_rooms():
            if room_dict['slug'] not in self._rooms:
                self._rooms[room_dict['slug']] = Room(self, **room_dict)
        return self._rooms
    
    def room_by_id(self, id):
        for room in self.rooms.values():
            if room.id == id:
                return room
    
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

    def post_file(self, room_id: str, file: 'file-like', filename: str, mimetype: str)->dict:
        """
        Uses the unspecified POST->/files API call, may not be a stable API.
        
        file argument should be a binary file-like object; either an open file,
        or an io object such as io.BytesIO.
        filename must be a string.
        mimetype must be a valid mimetype, bear in mind the permitted uploads on
          the API side. By default only images are permitted.
        """
        uri = self.endpoint + "/files"
        data = {'post': 'true', 'room': room_id}
        files = {'file': (filename, file, mimetype)}
        auth = (self.token, "password not needed")
        r = requests.post(uri, data = data, files = files, auth = auth)
        r.raise_for_status()
        return r

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
    
    def account(self)->Account:
        return Account(self, **self.get_account())

