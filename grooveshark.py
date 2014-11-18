import requests
import hmac
import hashlib
import json
import random
import playlist

from difflib import SequenceMatcher


class RateLimitExceeded(Exception):
    pass


class WebServiceBase(object):
    baseUrl = 'https://api.grooveshark.com/ws3.php'

    def __init__(self, key, secret):
        self.wsKey = key
        self.wsSecret = secret


class Session(WebServiceBase):

    def __init__(self, wsKey, wsSecret, session_id, **kwargs):
        WebServiceBase.__init__(self, wsKey, wsSecret)
        self.session_id = session_id
        self.playlists = kwargs.get('playlists', {})
        self.username = kwargs.get('username', None)
        if 'password' in kwargs:
            m = hashlib.md5()
            m.update(password)
            self.password = m.hexdigest()
        else:
            self.password = None

    def _post(self, payload):
        postData = json.dumps(payload)
        h = hmac.new(self.wsSecret, postData)
        r = requests.post(self.baseUrl,
                          data=postData,
                          params={'sig': h.hexdigest()})
        jr = r.json()
        if r.status_code != 200 or 'result' not in jr or not jr['result']:
            if 'errors' in jr and 'code' in jr['errors'][0]:
                if jr['errors'][0]['code'] == 11:
                    raise RateLimitExceeded(jr['errors'][0]['message'])
            raise RuntimeError('Grooveshark Error %s: %s'
                               % (r.status_code, jr['errors']))
        return jr

    field_map = {
            'song': 'SongName',
            'artist': 'ArtistName',
            'album': 'AlbumName',
            'song_id': 'SongID',
            'artist_id': 'ArtistID',
            'album_id': 'AlbumID',
            'popularity': 'Popularity'
            }

    def _search_internal(self, text, limit=3):
        payload = {'method': 'getSongSearchResults',
                   'parameters': {'query': text,
                                  'country': 'us',
                                  'limit': limit},
                   'header': {'wsKey': self.wsKey}}
        jr = self._post(payload)
        hits = []
        if 'result' in jr and 'songs' in jr['result']:
            for i, song in enumerate(jr['result']['songs'], start=1):
                if i > limit:
                    break
                pe = playlist.PlaylistEntry()
                for (attr_name, song_field) in self.field_map.iteritems():
                    setattr(pe, attr_name, song[song_field])
                pe.label = ''
                hits.append(pe)
        return hits

    def _close_match(self, a, b):
        s = SequenceMatcher(None, a.artist.lower(), b.artist.lower())
        if s.ratio() > 0.75:
            match_factor = s.ratio()
            s = SequenceMatcher(None, a.song.lower(), b.song.lower())
            if s.ratio() > 0.75:
                match_factor = match_factor + s.ratio()
                s = SequenceMatcher(None, a.album.lower(), b.album.lower())
                match_factor = match_factor + s.ratio()
                if s.ratio() > 0.75:
                    match_factor = match_factor + (b.popularity/100000000000.0)
                return (True, match_factor)
        return (False, 0)

    def _filter_matches(self, original, hits):
        def is_match(hit):
            (match, factor) = self._close_match(original, hit)
            if match:
                hit.factor = factor
            return match
        return filter(is_match, hits)

    def _find_match(self, original, text):
        hits = self._search_internal(text, 10)
        matches = self._filter_matches(original, hits)
        if matches and len(matches):
            ranked = sorted(matches, key=lambda h: h.factor, reverse=True)
            return ranked[0]
        else:
            return None

    def search(self, playlist_entry):
        text = playlist_entry.song + ' ' + playlist_entry.artist
        match = self._find_match(playlist_entry, text)
        if match:
            return match
        else:
            text = playlist_entry.artist + ' ' + playlist_entry.song.split()[0]
            return self._find_match(playlist_entry, text)

    def start_new(self):
        payload = {'method': 'startSession',
                   'header': {'wsKey': self.wsKey}}
        jr = self._post(payload)
        if 'result' in jr and 'sessionID' in jr['result']:
            self.session_id = jr['result']['sessionID']
        raise RuntimeError('Failed to start session: %s'
                            % jr['errors'])

    def authenticate(self):
        payload = {'method': 'authenticate',
                   'parameters': {'login': self.username,
                                  'password': self.password},
                   'header': {'wsKey': self.wsKey,
                              'sessionID': self.session_id}}
        jr = self._post(payload)
        if 'result' in jr and 'success' in jr['result']:
            if jr['result']['success']:
                return jr['result']['UserID']
        raise RuntimeError('Failed to authenticate user %s: %s'
                            % (self.username, jr['errors']))

    def get_user_info(self):
        payload = {'method': 'getUserInfo',
                   'header': {'wsKey': self.wsKey,
                              'sessionID': self.session_id}}
        jr = self._post(payload)
        if 'result' in jr and 'UserID' in jr['result']:
            return jr['result']['UserID']
        raise RuntimeError('Failed to get user info for %s: %s'
                            % (self.username, jr['errors']))

    def get_playlists(self):
        payload = {'method': 'getUserPlaylists',
                   'header': {'wsKey': self.wsKey,
                              'sessionID': self.session_id}}
        jr = self._post(payload)
        if 'result' in jr and 'playlists' in jr['result']:
            return jr['result']['playlists']
        raise RuntimeError('Failed to get playlists for %s: %s'
                            % (self.username, jr['errors']))

    def create_playlist(self, name):
        print('Creating playlist named \'%s\'..' % name)
        payload = {'method': 'createPlaylist',
                   'parameters': {'name': name,
                                  'songIDs': ''},
                   'header': {'wsKey': self.wsKey,
                              'sessionID': self.session_id}}
        jr = self._post(payload)
        if 'result' in jr and 'success' in jr['result']:
            if jr['result']['success']:
                return jr['result']['playlistID']
        raise RuntimeError('Failed to create playlist %s: %s'
                            % (name, jr['errors']))

    def add_songs_to_playlist(self, song_ids,
                              playlist_name=None, playlist_id=None):
        if playlist_id:
            print('Adding songs \'%s\' to playlist id %s..'
                  % (song_ids, playlist_id))
        else:
            if playlist_name and playlist_name in self.playlists:
                playlist_id = self.playlists[playlist_name]
                print('Adding songs \'%s\' to playlist named \'%s\'..'
                      % (song_ids, playlist_name))
            else:
                raise RuntimeError("Unknown playlist: " % playlist_name)
        exist_songs = []
        for es in self.get_songs_from_playlist(playlist_name):
            exist_songs.append(es['SongID'])
        new_songs = list(set(exist_songs + song_ids))
        payload = {'method': 'setPlaylistSongs',
                   'parameters': {'playlistID': playlist_id,
                                  'songIDs': new_songs},
                   'header': {'wsKey': self.wsKey,
                              'sessionID': self.session_id}}
        jr = self._post(payload)
        if ('result' in jr and 'success' in jr['result']
                and jr['result']['success']):
            return True
        else:
            return False

    def add_song_to_playlist(self, song_id, playlist_name):
        print('Adding song \'%s\' to playlist named \'%s\'..'
                % (song_id, playlist_name))
        if playlist_name not in self.playlists:
            raise RuntimeError("Unknown playlist")
        exist_songs = []
        for es in self.get_songs_from_playlist(playlist_name):
            exist_songs.append(es['SongID'])
        exist_songs.append(song_id)
        payload = {'method': 'setPlaylistSongs',
                   'parameters': {'playlistID': self.playlists[playlist_name],
                                  'songIDs': exist_songs},
                   'header': {'wsKey': self.wsKey,
                              'sessionID': self.session_id}}
        jr = self._post(payload)
        if ('result' in jr and 'success' in jr['result']
                and jr['result']['success']):
            return True
        else:
            return False

    def get_songs_from_playlist(self, playlist_name):
        if playlist_name not in self.playlists:
            raise RuntimeError("Unknown playlist")
        payload = {'method': 'getPlaylist',
                   'parameters': {'playlistID': self.playlists[playlist_name],
                                  'limit': 500},
                   'header': {'wsKey': self.wsKey,
                              'sessionID': self.session_id}}
        jr = self._post(payload)
        if 'result' in jr and 'Songs' in jr['result']:
            return jr['result']['Songs']
        raise RuntimeError('Failed to get songs from playlist %s: %s'
                            % (playlist_name, jr['errors']))
