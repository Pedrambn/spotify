import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re
from difflib import SequenceMatcher
import streamlit as st

# Spotify API credentials - Make sure to replace these with your own
CLIENT_ID = 'your_client_id'
CLIENT_SECRET = 'your_client_secret'
REDIRECT_URI = 'http://localhost:8080'

# Spotify Authentication
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="playlist-modify-public"
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

# Function to calculate the similarity ratio between two strings
def calculate_similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

# Function to find the best match for the current sequence of words
def find_best_match_from_start(words, start_index):
    best_uri = None
    best_combination = []
    best_score = 0

    # Try combinations starting from the current index, moving sequentially
    for length in range(len(words) - start_index, 0, -1):
        phrase = ' '.join(words[start_index:start_index + length])
        track_uri, track_name = search_song(phrase)
        if track_uri:
            similarity_score = calculate_similarity(phrase, track_name)
            if similarity_score > best_score:
                best_combination = words[start_index:start_index + length]
                best_uri = track_uri
                best_score = similarity_score

    return best_uri, best_combination

# Main function to generate a playlist from a prompt
def generate_playlist_from_prompt(prompt):
    words = get_words_from_prompt(prompt)
    track_uris = []
    current_index = 0

    while current_index < len(words):
        best_uri, best_combination = find_best_match_from_start(words, current_index)

        if best_uri:
            # Add the best matching song to the playlist
            track_uris.append(best_uri)
            # Move the current index to the next unmatched word
            current_index += len(best_combination)
        else:
            # If no combination matches, find the closest match for the current word
            print(f"No exact song found for current phrase. Searching for the closest match.")
            track_uri, track_name = search_song(words[current_index])
            if track_uri:
                track_uris.append(track_uri)
            else:
                print(f"No match found for word: '{words[current_index]}'. Adding a generic popular song.")
                fallback_track_uri, _ = search_song("music")  # Fallback to a generic word like "music"
                if fallback_track_uri:
                    track_uris.append(fallback_track_uri)
            current_index += 1

    user_id = sp.current_user()['id']
    playlist_name = f"Playlist for: {prompt[:20]}..."
    playlist_id, playlist_url = create_playlist(playlist_name, user_id)
    add_songs_to_playlist(playlist_id, track_uris)
    return playlist_url

# Streamlit interface
st.title("Write something and let us turn int into songs")
user_prompt = st.text_input("Write something cool (25 words max):")

if st.button("Generate Playlist"):
    if user_prompt:
        with st.spinner('Abracadabra...'):
            playlist_url = generate_playlist_from_prompt(user_prompt)
        st.success('Playlist created successfully!')
        st.markdown(f"[Click here to open your playlist]({playlist_url})")