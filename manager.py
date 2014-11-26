import time

import grooveshark
import spotify


class Manager(object):

    def create(type, credentials):
        if type == 'Grooveshark': return GroovesharkManager(credentials)
        if type == 'Spotify': return SpotifyManager(credentials)
        assert 0, "Bad maanger type: %s" % type
    create = staticmethod(create)

    def update_playlist(self, play_list, play_list_name):
        pass


class GroovesharkManager(Manager):

    def __init__(self, credentials):
        self.session = grooveshark.Session(credentials.grooveshark_ws_key,
                                           credentials.grooveshark_ws_secret,
                                           credentials.grooveshark_session_id)

    def update_playlist(self, play_list, play_list_name):
        rate_limit_wait = 20 # minutes
        search_wait = 60 # seconds
        play_list_id = None
        gs_play_lists = self.session.get_playlists()
        for p in gs_play_lists:
            if p['PlaylistName'] == play_list_name:
                play_list_id = p['PlaylistID']
        if not play_list_id:
            play_list_id = self.session.create_playlist(play_list_name)
        songs_to_add = []
        existing_songs = set([s['SongID'] for s in
                self.session.get_songs_from_playlist(playlist_id=play_list_id)])
        print ('Updating grooveshark playlist {0} with {1} songs'
                .format(play_list_name, len(play_list.playlist)))

        for i, play_list_entry in enumerate(play_list.playlist):

            if (hasattr(play_list_entry, 'song_id') and
                    play_list_entry.song_id and
                    play_list_entry.song_id in existing_songs):
                print ("Skipping song already present: {0}"
                        .format(play_list_entry))
                continue

            search_successful = False
            while not search_successful:
                try:
                    print "Searching for %s ... " % play_list_entry,
                    match = self.session.search(play_list_entry)
                    if match:
                        print "Found a match: %s" % match.song_id
                        play_list_entry.song_id = match.song_id
                        if match.song_id not in existing_songs:
                            songs_to_add.append(match.song_id)
                    else:
                        print "No matches"
                        play_list_entry.song_id = None
                    search_successful = True
                    time.sleep(search_wait)
                except grooveshark.RateLimitExceeded, e:
                    print ("Hit the rate limit! Waiting %d minutes.. [%s]"
                            % (rate_limit_wait, e))
                    time.sleep(60 * rate_limit_wait)
                    continue
                except RuntimeError, e:
                    print "Uh-oh, exception: ", e
                    return -1

        if self.session.add_songs_to_playlist(songs_to_add,
                                              playlist_id=play_list_id):
            print ("Successfully added {0} songs (out of {1}) to playlist {2}"
                    .format(len(songs_to_add),
                            len(play_list.playlist),
                            play_list_name))
            return len(songs_to_add)
        else:
            print ("Failed to add songs to {0}".format(play_list_name))
            return -1


class SpotifyManager(Manager):

    def __init__(self, credentials):
        self.session = spotify.Session(credentials.spotify_client_id,
                                       credentials.spotify_client_secret,
                                       credentials.spotify_username)

    def update_playlist(self, play_list, play_list_name, skip_filter=None):
        spotify_play_lists = self.session.get_playlists()
        if play_list_name in spotify_play_lists:
            play_list_id = spotify_play_lists[play_list_name]
        else:
            play_list_id = self.session.create_playlist(play_list_name)
        songs_to_add = []
        existing_songs = self.session.get_playlist_tracks(play_list_id)
        print ('Updating Spotify playlist {0} based on list of {1} songs'
                .format(play_list_name, len(play_list.playlist)))
        (num_skipped, num_present, num_not_found) = (0, 0, 0)
        for i, play_list_entry in enumerate(play_list.playlist):

            if skip_filter and skip_filter(play_list_entry):
                num_skipped = num_skipped + 1
                continue

            if (hasattr(play_list_entry, 'song_id') and
                    play_list_entry.song_id and
                    play_list_entry.song_id in existing_songs):
                num_present = num_present + 1
                continue

            search_successful = False
            while not search_successful:
                try:
                    print "Searching for %s ... " % play_list_entry,
                    match = self.session.search_entry(play_list_entry)
                    if match:
                        print "Found a match: %s" % match.song_id
                        play_list_entry.song_id = match.song_id
                        songs_to_add.append(match.song_id)
                    else:
                        print "No matches"
                        play_list_entry.song_id = None
                        num_not_found = num_not_found + 1
                    search_successful = True
                    time.sleep(2)
                except Exception, e:
                    print 'Uh-oh.. encountered exceptional behavior: ', e
                    time.sleep(10)

        print 'Summary of completed search:'
        print '{0:>5} songs in playlist.'.format(len(play_list.playlist))
        print '{0:>5} songs filtered out.'.format(num_skipped)
        print '{0:>5} songs already present.'.format(num_present)
        print '{0:>5} songs not found during search.'.format(num_not_found)
        print '{0:>5} songs found and to be added.'.format(len(songs_to_add))

        if self.session.add_tracks_to_playlist(play_list_id=play_list_id,
                                               track_ids=songs_to_add):
            print ('Successfully added {0} songs to playlist {1}'
                    .format(len(songs_to_add), play_list_name))
            return len(songs_to_add)
        else:
            print ('Failed to add {0} songs to playlist {1}'
                    .format(len(songs_to_add), play_list_name))
            return -1


