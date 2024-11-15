from flask import Flask, request, render_template_string
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re
from difflib import SequenceMatcher

# Spotify API credentials
CLIENT_ID = 'your_spotify_client_id'
CLIENT_SECRET = 'your_spotify_client_secret'
REDIRECT_URI = 'http://example.com/callback'  # Replace this with your actual redirect URI

# Spotify Authentication
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="playlist-modify-public"
))

# Flask app setup
app = Flask(__name__)

# Function to clean and split the prompt into words
def get_words_from_prompt(prompt):
    prompt = re.sub(r'[^a-zA-Z0-9\s]', '', prompt)  # Remove special characters
    words = prompt.split()
    return words[:25]  # Limit to 25 words

# Function to search for a song by title
def search_song(query):
    try:
        results = sp.search(q=f'track:{query}', type='track', limit=5)
        tracks = results.get('tracks', {}).get('items', [])
        if tracks:
            return tracks[0]['uri'], tracks[0]['name']
        else:
            return None, None
    except Exception as e:
        return None, None

# Function to create a Spotify playlist with error handling
def create_playlist(name, user_id):
    try:
        playlist = sp.user_playlist_create(user=user_id, name=name, public=True)
        return playlist['id'], playlist['external_urls']['spotify']
    except Exception as e:
        return None, None

# Function to add songs to a playlist with error handling
def add_songs_to_playlist(playlist_id, track_uris):
    try:
        sp.playlist_add_items(playlist_id, track_uris)
    except Exception as e:
        print(f"Error adding songs: {e}")

# Function to generate a playlist from a prompt
def generate_playlist_from_prompt(prompt):
    words = get_words_from_prompt(prompt)
    track_uris = []
    current_index = 0

    while current_index < len(words):
        best_uri, best_combination = find_best_match_from_start(words, current_index)

        if best_uri:
            track_uris.append(best_uri)
            current_index += len(best_combination)
        else:
            track_uri, track_name = search_song(words[current_index])
            if track_uri:
                track_uris.append(track_uri)
            else:
                fallback_track_uri, _ = search_song("music")
                if fallback_track_uri:
                    track_uris.append(fallback_track_uri)
            current_index += 1

    user_id = sp.current_user()['id']
    playlist_name = f"Playlist for: {prompt[:20]}..."
    playlist_id, playlist_url = create_playlist(playlist_name, user_id)

    if playlist_id:
        add_songs_to_playlist(playlist_id, track_uris)
        return playlist_url
    else:
        return "Error in creating playlist"

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        user_prompt = request.form.get("prompt")
        if user_prompt:
            playlist_url = generate_playlist_from_prompt(user_prompt)
            return render_template_string("""
                <h1>Spotify Playlist Generator</h1>
                <p>Playlist created successfully! <a href="{{ playlist_url }}">Click here to open your playlist</a></p>
                <a href="/">Generate another playlist</a>
            """, playlist_url=playlist_url)
    return render_template_string("""
        <h1>Spotify Playlist Generator from Prompt</h1>
        <form method="post">
            <label for="prompt">Enter your prompt (25 words max):</label><br><br>
            <input type="text" id="prompt" name="prompt" required><br><br>
            <input type="submit" value="Generate Playlist">
        </form>
    """)

if __name__ == "__main__":
    app.run(debug=True)
