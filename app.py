import os
from flask import Flask, request, render_template, redirect, url_for, session
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re
from rapidfuzz import fuzz

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Needed for session management

# Spotify API credentials from environment variables
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')

# Initialize Spotify OAuth
sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="playlist-modify-public user-read-private user-read-email",
    requests_timeout=10,
    open_browser=False
)


def find_best_songs(sp, prompt):
    words = prompt.split()
    current_index = 0
    track_uris = []
    matched_phrases = []

    while current_index < len(words):
        best_match = None
        best_uri = None
        best_phrase = None
        max_score = 0

        for phrase_length in range(len(words) - current_index, 0, -1):
            phrase = ' '.join(words[current_index:current_index + phrase_length])
            results = sp.search(q=f'track:"{phrase}"', type='track', limit=5, market="from_token")
            tracks = results.get('tracks', {}).get('items', [])
            for track in tracks:
                score = fuzz.ratio(phrase.lower(), track['name'].lower())
                if score > max_score:
                    max_score = score
                    best_match = track['name']
                    best_uri = track['uri']
                    best_phrase = phrase

            if max_score >= 90:
                break

        if best_match:
            matched_phrases.append(best_phrase)
            track_uris.append(best_uri)
            current_index += len(best_phrase.split())
        else:
            current_index += 1

    return track_uris, matched_phrases


def create_playlist(sp, name, user_id):
    playlist = sp.user_playlist_create(user=user_id, name=name, public=True)
    return playlist['id'], playlist['external_urls']['spotify']


def add_songs_to_playlist(sp, playlist_id, track_uris):
    sp.playlist_add_items(playlist_id, track_uris)


def generate_playlist_optimized(sp, prompt):
    track_uris, matched_phrases = find_best_songs(sp, prompt)
    user_id = sp.current_user()['id']
    playlist_name = f"Playlist for: {prompt[:20]}..."
    playlist_id, playlist_url = create_playlist(sp, playlist_name, user_id)
    add_songs_to_playlist(sp, playlist_id, track_uris)
    return playlist_url


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    if 'token_info' not in session:
        # Redirect to Spotify login if no token exists
        return redirect(url_for('login'))

    # Use the token from the session to create a Spotify client
    token_info = session['token_info']
    sp = spotipy.Spotify(auth=token_info['access_token'])

    prompt = request.form.get('prompt')
    if not prompt:
        return redirect(url_for('index'))

    try:
        playlist_url = generate_playlist_optimized(sp, prompt)
        return render_template('index.html', playlist_url=playlist_url)
    except Exception as e:
        return render_template('index.html', error=str(e))


@app.route('/login')
def login():
    # Redirect to Spotify's login page
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


@app.route('/callback')
def callback():
    # Handle Spotify's redirect with the authorization code
    code = request.args.get('code')
    if not code:
        return "Authorization failed: No code received.", 400

    try:
        token_info = sp_oauth.get_access_token(code)
        session['token_info'] = token_info  # Store token in session
        return redirect(url_for('index'))
    except Exception as e:
        return f"Authorization failed: {e}", 500


if __name__ == '__main__':
    app.run(debug=False)
