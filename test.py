import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re
from difflib import SequenceMatcher
import streamlit as st
import time

# Spotify API credentials - Using Streamlit secrets
CLIENT_ID = st.secrets['spotify']['client_id']
CLIENT_SECRET = st.secrets['spotify']['client_secret']
REDIRECT_URI = st.secrets['spotify']['redirect_uri']

# Spotify Authentication
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="playlist-modify-public"
), requests_timeout=30)

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
        st.write(f"Error searching for song: {e}")
        return None, None

# Function to create a Spotify playlist with error handling
def create_playlist(name, user_id):
    try:
        st.write("Creating a new playlist...")
        playlist = sp.user_playlist_create(user=user_id, name=name, public=True)
        st.write("Playlist created successfully.")
        return playlist['id'], playlist['external_urls']['spotify']
    except Exception as e:
        st.write(f"Error creating playlist: {e}")
        return None, None

# Function to add songs to a playlist with error handling
def add_songs_to_playlist(playlist_id, track_uris):
    try:
        for uri in track_uris:
            sp.playlist_add_items(playlist_id, [uri])
            time.sleep(1)  # Adding a 1-second delay between adding songs
        st.write("Songs added to the playlist successfully.")
    except Exception as e:
        st.write(f"Error adding songs: {e}")

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

# Main function to generate a playlist from a prompt with detailed debugging
def generate_playlist_from_prompt(prompt):
    words = get_words_from_prompt(prompt)
    track_uris = []
    current_index = 0

    st.write("Processing words from the prompt...")

    while current_index < len(words):
        best_uri, best_combination = find_best_match_from_start(words, current_index)

        if best_uri:
            st.write(f"Best match found: {best_combination}")
            track_uris.append(best_uri)
            current_index += len(best_combination)
        else:
            st.write(f"No exact match found for words starting from index {current_index}")
            track_uri, track_name = search_song(words[current_index])
            if track_uri:
                st.write(f"Closest match found: {track_name}")
                track_uris.append(track_uri)
            else:
                st.write(f"No match found for '{words[current_index]}'. Adding fallback song.")
                fallback_track_uri, _ = search_song("music")
                if fallback_track_uri:
                    track_uris.append(fallback_track_uri)
            current_index += 1

    user_id = sp.current_user()['id']
    playlist_name = f"Playlist for: {prompt[:20]}..."
    st.write("Creating playlist...")
    playlist_id, playlist_url = create_playlist(playlist_name, user_id)

    if playlist_id:
        st.write("Adding songs to the playlist...")
        add_songs_to_playlist(playlist_id, track_uris)
        st.write("Playlist created and songs added successfully.")
        return playlist_url
    else:
        st.write("Failed to create playlist.")
        return "Error in creating playlist"

# Streamlit interface
st.title("Spotify Playlist Generator from Prompt")
user_prompt = st.text_input("Enter your prompt (25 words max):")

if st.button("Generate Playlist"):
    if user_prompt:
        with st.spinner('Generating your playlist...'):
            playlist_url = generate_playlist_from_prompt(user_prompt)
        st.success('Playlist created successfully!')
        st.markdown(f"[Click here to open your playlist]({playlist_url})")
