#!/usr/bin/python

import time
import calendar

import playlist
import manager

import kcrw

import grooveshark_state


def maintain_kcrw_playlists(up_to_date):
    kcrw_updater = kcrw.PlaylistUpdater()
    playlist_manager = manager.Manager(grooveshark_state.ws_key,
                                       grooveshark_state.ws_secret,
                                       grooveshark_state.session_id)
    year = up_to_date.tm_year
    month = up_to_date.tm_mon
    (_, num_days_in_month) = calendar.monthrange(year, month)
    for day in range(1, (min(num_days_in_month, up_to_date.tm_mday)+1)):
        ret = kcrw_updater.update(year, month, day)
        if ret == 1:
            print "Can't go further than {0}/{1}/{2}".format(month, day, year)
            break
    (play_list, play_list_name,
        file_name) = kcrw_updater.get_playlist(year, month)
    num_added = playlist_manager.update_grooveshark_playlist(play_list,
                                                             play_list_name)
    if num_added > 0:
        play_list.to_json_file(file_name)



#last_day_of_october = time.struct_time((2014, 10, 31, 0, 0, 0, None, None, 0))

yesterday = time.localtime(time.time() - (60*60*24 - 1))
maintain_kcrw_playlists(yesterday)
