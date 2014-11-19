import os
import time
import requests
import htmlentitydefs

from playlist import PlaylistEntry, Playlist, merge_playlists

from HTMLParser import HTMLParser


class PlaylistParser(HTMLParser):

    def __init__(self, playlist):
        HTMLParser.__init__(self)
        self.last_tag = None
        self.last_attr = None
        self.entry = PlaylistEntry()
        self.playlist = playlist
        self.search_date = ''
        self.data = ''

    def handle_starttag(self, tag, attrs):
        self.last_tag = tag
        if tag == 'td':
            for name, value in attrs:
                if name == 'class' and value in self.entry.fields:
                    self.last_attr = value
                    setattr(self.entry, value, None)
                if (name == 'class' and value == 'search_date'
                        and not self.search_date):
                    self.last_attr = value

    def handle_endtag(self, tag):
        if tag == 'td' and self.last_attr in self.entry.fields:
            setattr(self.entry, self.last_attr, self.data.strip())
            self.data = ''
            if self.entry.ready():
                self.entry.play_count = 1
                self.playlist.append(self.entry)
                self.entry = PlaylistEntry()
                self.last_tag = None
                self.last_attr = None
        if tag == 'td' and self.last_attr == 'search_date':
            self.data = ''

    def handle_data(self, data):
        if self.last_tag == 'td' and (self.last_attr in self.entry.fields 
                                      or self.last_attr == 'search_date'):
            if data:
                if self.last_attr == 'search_date' and not self.search_date:
                    self.search_date = data.strip()
                self.data = self.data + data

    def handle_entityref(self, name):
        if self.last_tag == 'td' and (self.last_attr in self.entry.fields
                                      or self.last_attr == 'search_date'):
            codepoint = htmlentitydefs.name2codepoint[name]
            self.data = self.data + unichr(codepoint)


class PlaylistFetcher(object):
    url = 'http://newmedia.kcrw.com/tracklists/search.php'

    def __init__(self):
        self.max_start = 300

    def fetch(self, date):
        start = 0
        playlist = []
        parser = PlaylistParser(playlist)
        while start < self.max_start:
            playlist_size = len(playlist)
            self._fetch(parser, date, start)
            if len(playlist) == playlist_size:
                break
            start = start + 50
        try:
            sd = time.strptime(parser.search_date, "%A, %B %d, %Y")
            actual_date = "{0}/{1}/{2}".format(sd.tm_mon,
                                               sd.tm_mday,
                                               sd.tm_year)
            return (playlist, actual_date)
        except ValueError:
            return (None, None)

    def _fetch(self, parser, date, start):
        params = {'search_type': '0',
                  'date_from': date,
                  'start': start}
        this_url = ''
        def grab_url(r, *args, **kwargs):
            this_url = r.url
        r = requests.get(self.url, params=params,
                         timeout=2, stream=True,
                         hooks=dict(response=grab_url))
        if r.status_code != 200:
            raise RuntimeError('GET failed with params=%s' % params)
        r.encoding = 'utf-8'
        parser.feed(r.text)


class PlaylistUpdater(object):
    file_prefix = 'kcrw_playlist_'
    file_suffix = '.json'

    def __init__(self):
        self.fetcher = PlaylistFetcher()

    def get_playlist(self, year, month):
        play_list = None
        file_name = "{0}{1}{2}{3}".format(self.file_prefix,
                                          year, month,
                                          self.file_suffix)
        if os.path.exists(file_name):
            play_list = Playlist()
            play_list.from_json_file(file_name)
        else:
            play_list = Playlist(source='kcrw',
                                 name='%s%s' % (year, month),
                                 frequency='daily')
        play_list_name = "kcrw-{0}-{1}".format(year, month)
        return (play_list, play_list_name, file_name)

    def update(self, year, month, day):
        (play_list, play_list_name, file_name) = self.get_playlist(year, month)
        the_date = "{0}/{1}/{2}".format(month, day, year)
        if the_date in play_list.records:
            print "Playlist for {0} already exists".format(the_date)
            return -1
        else:
            print "Fetching playlist for new date {0}".format(the_date)
            (p_list, search_date) = self.fetcher.fetch(the_date)
            if search_date == the_date:
                print ("New date is valid, merging into {0} playlist"
                        .format(play_list_name))
                play_list.playlist = merge_playlists(play_list.playlist, p_list)
                play_list.records.append(the_date)
                play_list.to_json_file(file_name)
                return 0
            else:
                print ("Latest date available is {0}".format(search_date))
                return 1
