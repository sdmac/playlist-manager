#!/usr/bin/python

import json

from difflib import SequenceMatcher

import spotipy
from spotipy import util

import playlist


class WebServiceBase(object):
    redirect_uri = 'http://example.com/callback'

    def __init__(self, key, secret):
        self.ws_key = key
        self.ws_secret = secret

class Session(WebServiceBase):

    def __init__(self, ws_key, ws_secret, username):
        WebServiceBase.__init__(self, ws_key, ws_secret)
        self.username = username

    def _get_token(self, scope):
        token = util.prompt_for_user_token(self.username,
                                           scope=scope,
                                           client_id=self.ws_key,
                                           client_secret=self.ws_secret,
                                           redirect_uri=self.redirect_uri)
        if not token:
            raise RuntimeError("Cannot get token for user %s" % self.username)
        return token

    def get_playlists(self, limit=50):
        token = self._get_token(scope='playlist-modify-public')
        sp = spotipy.Spotify(auth=token)
        results = sp.user_playlists(self.username)
        playlists = {}
        for r in results['items']:
            playlists[r['name']] = r['id']
        return playlists

    def create_playlist(self, name):
        token = self._get_token(scope='playlist-modify-public')
        sp = spotipy.Spotify(auth=token)
        result = sp.user_playlist_create(self.username, name)
        return result['id']

    def get_playlist_tracks(self, play_list_id):
        token = self._get_token(scope='playlist-modify-public')
        sp = spotipy.Spotify(auth=token)
        track_ids = []
        page_offset = 0
        next_page = True
        while next_page:
            result = sp.user_playlist_tracks(self.username,
                                            play_list_id,
                                            fields='items.track.uri,next',
                                            offset=page_offset)
            for r in result['items']:
                track_ids.append(r['track']['uri'])
            if result['next']:
                page_offset = page_offset + 100
            else:
                next_page = False
        return track_ids

    def add_tracks_to_playlist(self, play_list_id, track_ids):
        token = self._get_token(scope='playlist-modify-public')
        sp = spotipy.Spotify(auth=token)
        track_groups = [track_ids[i:i+100] for i in range(0, len(track_ids), 100)]
        for track_group in track_groups:
            try:
                sp.user_playlist_add_tracks(self.username,
                                            play_list_id,
                                            track_group)
            except SpotifyException, e:
                print 'ERROR adding tracks to %s: %s' % (play_list_id, e)
                return False
        return True

    def search_track(self, song, artist=None, limit=10):
        query = 'track:' + song
        if artist:
            query = query + ' artist:' + artist
        sp = spotipy.Spotify()
        #sp.trace = True
        results = sp.search(q=query, limit=limit, type='track')
        #print json.dumps(results)
        items = results['tracks']['items']
        hits = []
        if len(items):
            for item in items:
                pe = playlist.PlaylistEntry()
                setattr(pe, 'album', item['album']['name'])
                setattr(pe, 'artist', item['artists'][0]['name'])
                setattr(pe, 'song', item['name'])
                setattr(pe, 'song_id', item['uri'])
                setattr(pe, 'popularity', item['popularity'])
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

    def _find_match(self, original):
        hits = self.search_track(song=original.song, artist=original.artist)
        matches = self._filter_matches(original, hits)
        if matches and len(matches):
            ranked = sorted(matches, key=lambda h: h.factor, reverse=True)
            return ranked[0]
        else:
            return None

    def search_entry(self, playlist_entry):
        match = self._find_match(playlist_entry)
        return match
