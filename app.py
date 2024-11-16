import os
from flask import Flask, request, render_template, redirect, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re
from difflib import SequenceMatcher

app = Flask(__name__)

# Spotify API credentials from environment variables
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')

# Initialize Spotify OAuth with token caching in Render's writable directory
sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="playlist-modify-public",
    cache_path="/tmp/.spotify_cache",
    requests_timeout=10,
    open_browser=False
)

# Function to clean and split the prompt into words
def get_words_from_prompt(prompt):
    prompt = re.sub(r'[^a-zA-Z0-9\s]', '', prompt)  # Remove special characters
    words = prompt.split()
    return words[:25]  # Limit to 25 words

# Function to search for a song by title
def search_song(sp, query):
    results = sp.search(q=f'track:{query}', type='track', limit=5)
    tracks = results.get('tracks', {}).get('items', [])
    if tracks:
        return tracks[0]['uri'], tracks[0]['name']
    else:
        return None, None

# Function to create a Spotify playlist
def create_playlist(sp, name, user_id):
    playlist = sp.user_playlist_create(user=user_id, name=name, public=True)
    return playlist['id'], playlist['external_urls']['spotify']

# Function to add songs to a playlist
def add_songs_to_playlist(sp, playlist_id, track_uris):
    sp.playlist_add_items(playlist_id, track_uris)

# Function to generate playlist from a prompt
def generate_playlist(sp, prompt):
    words = get_words_from_prompt(prompt)
    track_uris = []
    current_index = 0

    while current_index < len(words):
        track_uri, _ = search_song(sp, words[current_index])
        if track_uri:
            track_uris.append(track_uri)
        current_index += 1

    user_id = sp.current_user()['id']
    playlist_name = f"Playlist for: {prompt[:20]}..."
    playlist_id, playlist_url = create_playlist(sp, playlist_name, user_id)
    add_songs_to_playlist(sp, playlist_id, track_uris)
    return playlist_url

# Flask Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    # Redirect user to Spotify login if no valid token exists
    token_info = sp_oauth.get_cached_token()
    if not token_info:
        # Generate Spotify login URL
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)

    # User is authenticated; proceed to generate the playlist
    sp = spotipy.Spotify(auth_manager=sp_oauth)
    prompt = request.form.get('prompt')
    if not prompt:
        return redirect(url_for('index'))

    try:
        playlist_url = generate_playlist(sp, prompt)
        return render_template('index.html', playlist_url=playlist_url)
    except Exception as e:
        return render_template('index.html', error=str(e))

@app.route('/callback')
def callback():
    # Handle Spotify's redirect with the authorization code
    code = request.args.get('code')
    if not code:
        return "Authorization failed: No code received.", 400

    try:
        sp_oauth.get_access_token(code=code)
        return redirect(url_for('index'))
    except Exception as e:
        return f"Authorization failed: {e}", 500

if __name__ == '__main__':
    app.run(debug=False)
