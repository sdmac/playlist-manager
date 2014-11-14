#!/usr/bin/python

import json
import requests
import htmlentitydefs

from difflib import SequenceMatcher

from HTMLParser import HTMLParser


class PlaylistEntry(object):
    fields = ['artist', 'song', 'album', 'label']

    def __init__(self, json_rep=None):
        self.play_count = 0
        if json_rep:
            for (k, v) in json_rep.iteritems():
                setattr(self, k, v)

    def ready(self):
        return all([hasattr(self, f) for f in self.fields])

    def __str__(self):
        nonempty = filter(lambda x: x is not None,
                            [getattr(self, f, None) for f in self.fields])
        encoded = [v.encode('utf-8', 'ignore') for v in nonempty]
        return '[{0}]'.format(' | '.join(encoded + [str(self.play_count)]))

    def __repr__(self):
        return str(self)


class PlaylistParser(HTMLParser):

    def __init__(self, playlist):
        HTMLParser.__init__(self)
        self.last_tag = None
        self.last_attr = None
        self.entry = PlaylistEntry()
        self.playlist = playlist
        self.data = ''

    def handle_starttag(self, tag, attrs):
        self.last_tag = tag
        if tag == 'td':
            for name, value in attrs:
                if name == 'class' and value in self.entry.fields:
                    self.last_attr = value
                    setattr(self.entry, value, None)

    def handle_endtag(self, tag):
        if tag == 'td' and self.last_attr in self.entry.fields:
            setattr(self.entry, self.last_attr, self.data.strip())
            self.data = ''
            if self.entry.ready():
                self.playlist.append(self.entry)
                self.entry = PlaylistEntry()
                self.last_tag = None
                self.last_attr = None

    def handle_data(self, data):
        if self.last_tag == 'td' and self.last_attr in self.entry.fields:
            if data:
                self.data = self.data + data

    def handle_entityref(self, name):
        if self.last_tag == 'td' and self.last_attr in self.entry.fields:
            codepoint = htmlentitydefs.name2codepoint[name]
            self.data = self.data + unichr(codepoint)


class PlaylistEntryEncoder(json.JSONEncoder):

    def default(self, playlist):
        return playlist.__dict__


class PlaylistFetcher(object):

    def __init__(self, url):
        self.url = url
        self.max_start = 200
        self.playlist = []
        self.parser = PlaylistParser(self.playlist)

    def fetch(self, date):
        start = 0
        while start < self.max_start:
            playlist_size = len(self.playlist)
            self._fetch(date, start)
            if len(self.playlist) == playlist_size:
                break
            start = start + 50
        return self.playlist

    def _fetch(self, date, start):
        params = {'search_type': '0',
                  'date_from': date,
                  'start': start}
        this_url = ''
        def grab_url(r, *args, **kwargs):
            this_url = r.url
        try:
            r = requests.get(self.url, params=params,
                             timeout=2, stream=True,
                             hooks=dict(response=grab_url))
            r.encoding = 'utf-8'
            self.parser.feed(r.text)
        except requests.exceptions.Timeout:
            print 'Request timeout for: {0}'.format(this_url)


def merge_playlists(old, new):
    for new_song in new:
        dup = False
        for old_song in old:
            s = SequenceMatcher(None,
                                old_song.artist.lower(),
                                new_song.artist.lower())
            if s.ratio() > 0.75:
                s = SequenceMatcher(None,
                                    old_song.song.lower(),
                                    new_song.song.lower())
                if s.ratio() > 0.75:
                    dup = True
                    old_song.play_count = old_song.play_count + 1
        if not dup:
            # updating old ensures dups within new list are handled
            old.append(new_song)
    return old
