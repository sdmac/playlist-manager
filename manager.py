import time

import grooveshark


class Manager(object):

    def __init__(self, ws_key, ws_secret, session_id):
        self.session = grooveshark.Session(ws_key,
                                           ws_secret,
                                           session_id)

    def update_grooveshark_playlist(self, play_list, play_list_name):
        rate_limit_wait = 10 # minutes
        search_wait = 60 # seconds
        play_list_id = None
        gs_play_lists = self.session.get_playlists()
        for p in gs_play_lists:
            if p['PlaylistName'] == play_list_name:
                play_list_id = p['PlaylistID']
        if not play_list_id:
            play_list_id = self.session.create_playlist(play_list_name)
        songs_to_add = []
        print ('Updating grooveshark playlist {0} with {1} songs'
                .format(play_list_name, len(play_list.playlist)))
        for i, play_list_entry in enumerate(play_list.playlist):
            try:
                if i < 101 and not hasattr(play_list_entry, 'song_id'):
                    print "Searching for %s ... " % play_list_entry,
                    match = self.session.search(play_list_entry)
                    if match:
                        print "Found a match: %s" % match.song_id
                        play_list_entry.song_id = match.song_id
                        songs_to_add.append(match.song_id)
                    else:
                        print "No matches"
                        play_list_entry.song_id = None
                    time.sleep(search_wait)
            except grooveshark.RateLimitExceeded, e:
                print ("Hit the rate limit! Waiting %d minutes.. [%s]"
                       % (rate_limit_wait, e))
                time.sleep(60 * rate_limit_wait)
                continue
            except RuntimeError, e:
                print "Uh-oh, exception: ", e
                return -1

        if s.add_songs_to_playlist(songs_to_add, playlist_id=play_list_id):
            print ("Successfully added {0} songs (out of {1}) to playlist {2}"
                    .format(len(songs_to_add), len(play_list), play_list_name))
            return len(songs_to_add)
        else:
            print ("Failed to add songs to {0}".format(play_list_name))
            return -1
