"""
Step 1: Log into youtube
Step 2: Grab like video
Step 3: Create new playlist
Step 4: Search for the song
Step 5: Add this song into the new Spotify playlist
"""
import json
import os
# Youtube API
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

# For Spotify
import requests
from secrets import spotify_user_id, spotify_token

# Youtube dl
import youtube_dl


class CreatePlaylist:

    def __init__(self):
        self.user_id = spotify_user_id
        self.spotify_token = spotify_token
        self.youtube_client = self.get_yt_client()
        self.all_song_info = {}

    # Step 1: Log into youtube
    def get_yt_client(self):
        # copied from Youtube Data API
        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = "client_secret.json"

        # Get credentials and create an API client
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes)
        credentials = flow.run_console()
        youtube = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials)
        # flow.redirect_uri = 'https://www.youtube.com/oauth2callback'

        return youtube

    # Step 2: Grab like videos and creating a dictionary of song info
    def get_liked_videos(self):
        request = self.youtube_client.videos().list(
            part="snippet,contentDetails,statistics",
            myRating="like"
        )
        response = request.execute()

        # collect each video and get information
        for item in response["items"]:
            video_title = item["snippet"]["title"]
            youtube_url = "https://www.youtube.com/watch?v={}".format(item["id"])

            # use youtube_dl to collect the song name and artist name
            video = youtube_dl.YoutubeDL({}).extract_info(youtube_url, download=False)

            song_name = video["track"]
            artist = video["artist"]

            # save all information
            self.all_song_info[video_title]={
                "youtube_url": youtube_url,
                "song_name": song_name,
                "artist": artist,

                # add the uri, easy to get song to put into playlist
                "spotify_uri": self.get_spotify_uri(song_name, artist)
            }
            print(self.all_song_info)

    # Step 3: Create new playlist
    def create_playlist(self):
        request_body = json.dumps({
            "name": "Liked Youtube videos",
            "description": "All liked youtube videos",
            "public": True
        })

        query = "https://api.spotify.com/v1/users/{}/playlists".format(self.user_id)
        response = requests.post(
            query,
            data=request_body,
            headers= {
                "Content-Type":"application/json",
                "Authorization":"Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()

        # playlist id
        return response_json["id"]

    # Step 4: Search for the song
    def get_spotify_uri(self, song_name, artist):

        query = "https://api.spotify.com/v1/search?q=track%3A{}+artist%3A{}&type=track&limit=20&offset=0".format(
            song_name,
            artist
        )
        response = requests.get(
            query,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()
        songs = response_json["tracks"]["items"]

        # only use the first song
        uri = songs[0]["uri"]

        return uri

    # Step 5: Add this song into the new Spotify playlist
    def add_song_to_playlist(self):
        # populate our songs dictionary
        self.get_liked_videos()
        # collect all of uris
        uris = [info["spotify_uri"]
                for song, info in self.all_song_info.items()]
        # create a new playlist
        playlist_id = self.create_playlist()

        # add all songs into new playlist
        request_data = json.dumps(uris)

        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(playlist_id)

        response = requests.post(
            query,
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()
        return response_json


if __name__ == '__main__':
    cp = CreatePlaylist()
    cp.add_song_to_playlist()
