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

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="playlist-modify-public",
    requests_timeout=10,
    open_browser=False,
    cache_path="/tmp/.spotify_cache"  # Use /tmp/ in Render for write access
))

# Function to clean and split the prompt into words
def get_words_from_prompt(prompt):
    prompt = re.sub(r'[^a-zA-Z0-9\s]', '', prompt)  # Remove special characters
    words = prompt.split()
    return words[:25]  # Limit to 25 words

# Function to search for a song by title
def search_song(query):
    results = sp.search(q=f'track:{query}', type='track', limit=5)
    tracks = results.get('tracks', {}).get('items', [])
    if tracks:
        return tracks[0]['uri'], tracks[0]['name']
    else:
        return None, None

# Function to create a Spotify playlist
def create_playlist(name, user_id):
    playlist = sp.user_playlist_create(user=user_id, name=name, public=True)
    return playlist['id'], playlist['external_urls']['spotify']

# Function to add songs to a playlist
def add_songs_to_playlist(playlist_id, track_uris):
    sp.playlist_add_items(playlist_id, track_uris)

# Function to generate playlist from a prompt
def generate_playlist(prompt):
    words = get_words_from_prompt(prompt)
    track_uris = []
    current_index = 0

    while current_index < len(words):
        track_uri, _ = search_song(words[current_index])
        if track_uri:
            track_uris.append(track_uri)
        current_index += 1

    user_id = sp.current_user()['id']
    playlist_name = f"Playlist for: {prompt[:20]}..."
    playlist_id, playlist_url = create_playlist(playlist_name, user_id)
    add_songs_to_playlist(playlist_id, track_uris)
    return playlist_url

# Flask Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    prompt = request.form.get('prompt')
    if not prompt:
        return redirect(url_for('index'))

    try:
        playlist_url = generate_playlist(prompt)
        return render_template('index.html', playlist_url=playlist_url)
    except Exception as e:
        return render_template('index.html', error=str(e))

# Callback route to handle Spotify OAuth redirect
@app.route('/callback')
def callback():
    # Extract the authorization code from the query parameters
    code = request.args.get('code')
    if not code:
        return "Authorization failed: No code received.", 400

    # Exchange the authorization code for access and refresh tokens
    try:
        token_info = sp.auth_manager.get_access_token(code=code)
        print(f"Access Token: {token_info['access_token']}")
        return "Authorization successful! You can now use the app."
    except Exception as e:
        print(f"Error during token exchange: {e}")
        return "Authorization failed during token exchange.", 500

if __name__ == '__main__':
    app.run(debug=False)
