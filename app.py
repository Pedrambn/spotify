import os
from flask import Flask, request, render_template, redirect, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re
from rapidfuzz import process, fuzz

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

# Function to search for songs using a sliding window
def find_best_songs(sp, prompt):
    words = prompt.split()
    current_index = 0
    track_uris = []
    matched_phrases = []  # Keep track of matched phrases for debugging

    while current_index < len(words):
        best_match = None
        best_uri = None
        best_phrase = None
        max_score = 0

        # Start with the longest possible phrase and reduce size
        for phrase_length in range(len(words) - current_index, 0, -1):
            phrase = ' '.join(words[current_index:current_index + phrase_length])
            
            # Search for songs that match the current phrase
            results = sp.search(q=f'track:"{phrase}"', type='track', limit=5)
            tracks = results.get('tracks', {}).get('items', [])
            
            # Check for the best match in the results
            for track in tracks:
                score = fuzz.ratio(phrase.lower(), track['name'].lower())
                if score > max_score:
                    max_score = score
                    best_match = track['name']
                    best_uri = track['uri']
                    best_phrase = phrase
            
            # Break if we find a strong match (e.g., score > 90)
            if max_score >= 90:
                break

        # If a match is found, add it to the playlist
        if best_match:
            print(f"Matched phrase: '{best_phrase}' -> '{best_match}' (Score: {max_score})")
            matched_phrases.append(best_phrase)
            track_uris.append(best_uri)
            current_index += len(best_phrase.split())  # Skip words matched by this phrase
        else:
            # Skip the current word if no match is found
            print(f"No match found for '{words[current_index]}'. Skipping.")
            current_index += 1

    return track_uris, matched_phrases


# Function to create a Spotify playlist
def create_playlist(sp, name, user_id):
    playlist = sp.user_playlist_create(user=user_id, name=name, public=True)
    return playlist['id'], playlist['external_urls']['spotify']

# Function to add songs to a playlist
def add_songs_to_playlist(sp, playlist_id, track_uris):
    sp.playlist_add_items(playlist_id, track_uris)


# Updated playlist generation function
def generate_playlist_optimized(sp, prompt):
    track_uris, matched_phrases = find_best_songs(sp, prompt)
    
    # Create a playlist in the user's Spotify account
    user_id = sp.current_user()['id']
    playlist_name = f"Playlist for: {prompt[:20]}..."
    playlist_id, playlist_url = create_playlist(sp, playlist_name, user_id)
    add_songs_to_playlist(sp, playlist_id, track_uris)

    print(f"Matched phrases: {matched_phrases}")
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
        playlist_url = generate_playlist_optimized(sp, prompt)
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
