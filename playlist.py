import json

from difflib import SequenceMatcher


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


class PlaylistEntryEncoder(json.JSONEncoder):

    def default(self, playlist):
        return playlist.__dict__


class Playlist(object):

    def __init__(self, playlist=[], source=None,
                 name=None, frequency=None, records=[]):
        self.playlist = playlist
        self.source = source
        self.name = name
        self.frequency = frequency
        self.records = records

    def to_json_file(self, file_name):
        with open(file_name, 'w') as o:
            json.dump(self, o, cls=PlaylistEntryEncoder)

    def from_json_file(self, file_name):
        self.playlist = []
        with open(file_name, 'r') as i:
            j = json.load(i)
            for attr_name in self.__dict__:
                if attr_name == 'playlist':
                    for e in j[attr_name]:
                        self.playlist.append(PlaylistEntry(e))
                else:
                    setattr(self, attr_name, j[attr_name])


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
