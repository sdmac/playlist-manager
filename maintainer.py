#!/usr/bin/python

import time
import calendar

import playlist
import manager
import kcrw

import credentials


def maintain_kcrw_playlists(up_to_date, playlist_manager=None):
    playlist_updater = kcrw.PlaylistUpdater()
    year = up_to_date.tm_year
    month = up_to_date.tm_mon
    (_, num_days_in_month) = calendar.monthrange(year, month)
    for day in range(1, (min(num_days_in_month, up_to_date.tm_mday)+1)):
        ret = playlist_updater.update(year, month, day)
        if ret == 1:
            print "Can't go further than {0}/{1}/{2}".format(month, day, year)
            break

    if playlist_manager:
        (play_list, play_list_name,
            file_name) = playlist_updater.get_playlist(year, month)
        def skip_filter(entry):
            for s in entry.sources:
                if 'ECLECTIC' in s or 'eclectic' in s:
                    return False
            return True
        name = play_list_name + '-mbe'
        playlist_manager.update_playlist(play_list, name, skip_filter)
        play_list.to_json_file(file_name)



playlist_manager = manager.Manager.create('Spotify', credentials)

yesterday = time.localtime(time.time() - (60*60*24 - 1))

maintain_kcrw_playlists(yesterday, playlist_manager)
