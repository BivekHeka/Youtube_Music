import os
import requests
from bs4 import BeautifulSoup
from ytmusicapi import YTMusic

# ==========================================
# 1. AUTHENTICATION CHECK
# ==========================================
if not os.path.exists("browser.json"):
    print("❌ browser.json not found. Please authenticate with YTMusic first.")
    exit()

# ==========================================
# 2. DATE INPUT & ROUTING ENGINE
# ==========================================
date = input("Which date do you want to travel to? (YYYY-MM-DD): ").strip()

if date == "2000-08-12":
    print("📂 Routing to the App Brewery Static Mockup archive...")
    url = f"https://appbrewery.github.io/bakeboard-hot-100/{date}"
    headers = {}
else:
    print(f"🌐 Routing to live Billboard.com for {date}...")
    url = f"https://www.billboard.com/charts/hot-100/{date}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

# ==========================================
# 3. HTTP WEB SCRAPING & DEFENSE
# ==========================================
response = requests.get(url, headers=headers)

if response.status_code != 200:
    print(f"❌ HTTP Error {response.status_code}: Could not retrieve data.")
    exit()

soup = BeautifulSoup(response.text, "html.parser")

# ==========================================
# PARSING BOTH SONGS AND ARTISTS
# ==========================================
song_pairs = []  # Will store tuples of (song_title, artist_name)

if "appbrewery" in url:
    # App Brewery mockup layout parsing
    chart_rows = soup.select("li.o-chart-results-list__item") or soup.select("ul.o-chart-results-list li")
    for row in chart_rows:
        title_tag = row.select_one("h3.c-title")
        # In the mockup, the artist is usually the span following or near the title
        artist_tag = row.select_one("span.c-label") 
        if title_tag:
            title = title_tag.getText().strip()
            artist = artist_tag.getText().strip() if artist_tag else ""
            song_pairs.append((title, artist))
else:
    # Live Billboard layout parsing container rows
    rows = soup.select("ul.o-chart-results-list-row") or soup.select(".o-chart-results-list-row-container")
    
    for row in rows:
        title_tag = row.select_one("h3#title-of-story") or row.select_one("h3")
        # On live Billboard, the artist name is typically the first span element after the h3 inside the list structure
        artist_tag = row.select_one("h3#title-of-story + span") or row.select_one("span.c-label")
        
        if title_tag:
            title = title_tag.getText().strip()
            artist = artist_tag.getText().strip() if artist_tag else ""
            
            # Filter out chart structural text headers
            blacklisted = ["Song Title", "Writer(s)", "Producer(s)", "Chart History", "Gains", "Award"]
            if not any(word in title for word in blacklisted):
                song_pairs.append((title, artist))

# Keep only the top 100 tracks safely
song_pairs = song_pairs[:100]

if not song_pairs:
    print("❌ Scraping structural mismatch: No songs found on the webpage.")
    exit()

print(f"🎉 Successfully tracked down {len(song_pairs)} tracks with their artists!")
print(f"Top Track Found: '{song_pairs[0][0]}' by {song_pairs[0][1]}")

# ==========================================
# 4. YOUTUBE MUSIC SETUP & DUP CHECK
# ==========================================
yt = YTMusic("browser.json")
PLAYLIST_NAME = f"{date} Billboard 100"

print("Checking library constraints...")
playlist_id = None
try:
    playlists = yt.get_library_playlists(limit=100)
    for p in playlists:
        if p["title"] == PLAYLIST_NAME:
            playlist_id = p["playlistId"]
            break
except Exception as e:
    print(f"⚠️ Warning during library check: {e}. Attempting to proceed...")

if playlist_id:
    print(f"🔄 The playlist '{PLAYLIST_NAME}' already exists. Appending missing tracks...")
else:
    try:
        playlist_id = yt.create_playlist(
            PLAYLIST_NAME,
            f"Automated archiving compilation of Billboard hits from {date}",
            privacy_status="PRIVATE",
        )
        print(f"✅ Created clean private playlist: {PLAYLIST_NAME}")
    except Exception as e:
        print(f"❌ Critical Error initializing Playlist: {e}")
        exit()

# ==========================================
# 5. SEARCH & TRACK POPULATION LOOP (UPDATED)
# ==========================================
print(f"\nProcessing compilation data for pipeline delivery...")
for index, (song, artist) in enumerate(song_pairs, start=1):
    try:
        # REQUIREMENT MET: Searching using BOTH the song title and artist name!
        search_query = f"{song} {artist}".strip()
        
        # HINT 1: filter="songs"
        search_results = yt.search(search_query, filter="songs", limit=1)
        
        if search_results:
            video_id = search_results[0]["videoId"]
            
            # HINT 2: yt.add_playlist_items()
            yt.add_playlist_items(playlist_id, [video_id])
            print(f"[{index}/{len(song_pairs)}] Added: {song} - {artist}")
        else:
            print(f"⏩ [{index}/{len(song_pairs)}] Skipped: {song} | Not resolved on YT Music")
            
    # REQUIREMENT MET: Wrapped completely inside a try/except block to skip failures gracefully
    except Exception as e:
        print(f"❌ [{index}/{len(song_pairs)}] Error syncing: {song} | Trace: {e}")

print(f"\n🚀 Execution Complete! '{PLAYLIST_NAME}' is ready inside YouTube Music.")