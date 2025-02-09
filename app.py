import mysql.connector
import os
from flask import Flask, render_template, request, redirect, session, url_for, flash
import spotipy
import time
from spotipy.oauth2 import SpotifyOAuth
import requests
import json
import re
import random
from PIL import Image
from io import BytesIO
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash



load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.static_folder = 'static'


#DIARY
#DIARY
#DIARY
#DIARY
#DIARY


# MySQL configurations
import mysql.connector

db = mysql.connector.connect(
    host="mysql-d3f8126-matching-avatar.e.aivencloud.com",
    user="avnadmin",
    password=os.getenv('SQL_PASSWORD'),
    database="defaultdb",
    port=int(15132),  # Ensure port is an integer
    ssl_ca="ca.pem"  # Path to the SSL certificate
)

cursor = db.cursor()

# Create or modify the users table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(255) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        bio TEXT,
        birth_day INT,
        birth_month INT,
        birth_year INT,
        news_interests TEXT,
        favorite_shows_movies TEXT
    )
""")
db.commit()

# Check if new columns exist and add if necessary
columns_to_add = {
    "birth_day": "INT",
    "birth_month": "INT",
    "birth_year": "INT",
    "news_interests": "TEXT",
    "favorite_shows_movies": "TEXT"
}

for column, datatype in columns_to_add.items():
    cursor.execute(f"""
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_NAME = 'users' AND COLUMN_NAME = '{column}'
    """)
    column_exists = cursor.fetchone()[0]

    if not column_exists:
        cursor.execute(f"ALTER TABLE users ADD COLUMN {column} {datatype}")
        db.commit()

cursor.close()


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        birth_day = int(request.form['birth_day'])
        birth_month = int(request.form['birth_month'])
        birth_year = int(request.form['birth_year'])

        cursor = db.cursor()

        # Check if username already exists
        cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
        existing_user = cursor.fetchone()
        if existing_user:
            cursor.close()
            flash("Username already exists. Please choose a different one.", "error")
            return render_template('register.html', username=username)

        # Insert user into the database (news_interests & favorite_shows_movies left empty)
        cursor.execute("INSERT INTO users (username, password, birth_day, birth_month, birth_year, bio, news_interests, favorite_shows_movies) VALUES (%s, %s, %s, %s, %s, '', '', '')",
                       (username, password, birth_day, birth_month, birth_year))
        db.commit()
        cursor.close()

        # Create a user-specific diary table
        cursor = db.cursor()
        cursor.execute(f"CREATE TABLE IF NOT EXISTS diary_{username} (id INT AUTO_INCREMENT PRIMARY KEY, entry TEXT, response TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        db.commit()
        cursor.close()

        session['username'] = username
        return redirect(url_for('home'))

    return render_template('register.html')




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = db.cursor()
        cursor.execute("SELECT id, password FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()

        if user and check_password_hash(user[1], password):
            session['username'] = username
            return redirect(url_for('home'))
        else:
            return "Invalid credentials, please try again."

    return render_template('login.html')



@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))






@app.route('/diary')
def diary():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    table_name = f"diary_{username}"

    cursor = db.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    entries = cursor.fetchall()
    entries.reverse()
    cursor.close()

    return render_template('diary.html', entries=entries, username=username)
 
@app.route('/submit', methods=['POST'])
def submit():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    cursor = db.cursor()

    cursor.execute("SELECT bio FROM users WHERE username = %s", (username,))
    bio = cursor.fetchone()

    db.commit()
    cursor.close()



    entry = request.form['diaryInput']
    headers = {
        'Content-Type': 'application/json',
    }

    jokes = {
    "contents": [
        {
            "parts": [
                {"text": "Based on the following diary entry: "+entry+"\n Give me commentary about my day as if you're my diary (be honest but empathetic). Give me sympathy, analysis, a scolding, reassurance, empathy, tough love, sarcasm, advice, honesty, or whatever I need based on what I write. Just output the commentary and nothing else."}
            ]
        }
    ],
    "systemInstruction": {
    "role": "system",
    "parts": [
      {
        "text": "Keep it short. Just answer the prompt and don't generate anything extra. Context about me only if it helps:"+bio[0]
      }
    ]
  } 
    }
    api_key = os.getenv('API_KEY')
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}"
    response = requests.post(url, headers=headers, json=jokes)
    response_content = response.json()['candidates'][0]['content']['parts'][0]['text']

    # Insert entry into user-specific diary table
    table_name = f"diary_{username}"
    cursor = db.cursor()
    query = f"INSERT INTO {table_name} (entry, response) VALUES (%s, %s)"
    cursor.execute(query, (entry, response_content))
    db.commit()
    cursor.close()

    return redirect(url_for('diary'))

@app.route('/delete/<int:entry_id>', methods=['POST'])
def delete_entry(entry_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    table_name = f"diary_{username}"

    cursor = db.cursor()
    query = f"DELETE FROM {table_name} WHERE id = %s"
    cursor.execute(query, (entry_id,))
    db.commit()
    cursor.close()

    return redirect(url_for('diary'))











#HOME
#HOME
#HOME
#HOME
#HOME



def get_horoscope_sign(month, day):
    zodiac_signs = [
        ("Capricorn", (1, 1), (1, 19)),
        ("Aquarius", (1, 20), (2, 18)),
        ("Pisces", (2, 19), (3, 20)),
        ("Aries", (3, 21), (4, 19)),
        ("Taurus", (4, 20), (5, 20)),
        ("Gemini", (5, 21), (6, 20)),
        ("Cancer", (6, 21), (7, 22)),
        ("Leo", (7, 23), (8, 22)),
        ("Virgo", (8, 23), (9, 22)),
        ("Libra", (9, 23), (10, 22)),
        ("Scorpio", (10, 23), (11, 21)),
        ("Sagittarius", (11, 22), (12, 21)),
        ("Capricorn", (12, 22), (12, 31))
    ]

    for sign, start, end in zodiac_signs:
        if (month == start[0] and day >= start[1]) or (month == end[0] and day <= end[1]):
            return sign
    return "Unknown"






@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    cursor = db.cursor()

    # Fetch birth month and day for the logged-in user
    cursor.execute("SELECT birth_month, birth_day FROM users WHERE username = %s", (username,))
    user_data = cursor.fetchone()
    cursor.close()


    if not user_data or not user_data[0] or not user_data[1]:
        flash("Please update your profile with your birth date to get your horoscope.", "warning")
        return redirect(url_for('profile'))  # Redirect to a profile update page if missing

    birth_month, birth_day = user_data
    zodiac_sign = get_horoscope_sign(birth_month, birth_day)


    url = "https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily"
    params = {
        'sign': zodiac_sign,  # Change 'Scorpio' to any other sign if needed
        'day': 'TODAY'
    }
    response = requests.get(url, params=params)
    data = response.json()
    horoscope = data["data"]["horoscope_data"]
    # Render the horoscope on the page
    comic_url = "https://xkcd.com/info.0.json"
    comic_response = requests.get(comic_url)
    comic = {}
    if comic_response.status_code == 200:
        comic_data = comic_response.json()
        comic = {
            'title': comic_data.get('title'),
            'img_url': comic_data.get('img'),
            'alt_text': comic_data.get('alt')
        }

    # Render the horoscope and comic on the homepage
    return render_template('home.html', horoscope=horoscope, comic=comic)
  









#TV
#TV
#TV
#TV
#TV

YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
#shows = [
 #       "Parks and Recreation","Brooklyn Nine-Nine","Ghost World", "Spaceballs", "But I'm a Cheerleader",
  #      "Harry Potter", "Friends", "Lord of the Rings", "Wynonna Earp", "Supernatural",
   #     "Call the Midwife", "The L Word", "Sex and the City", "Frasier", 
    #    "Buffy the Vampire Slayer", "Clueless", "Mean Girls", "Dude, Where's My Car?", "Jennifer's Body", "Bridget Jones' Diary", "Heathers", "Imagine Me & You"
    #]




@app.route('/tv', methods=['GET', 'POST'])
def tv():
    # Predefined list of TV shows
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    cursor = db.cursor()
    
    # Fetch favorite shows from the database
    cursor.execute("SELECT favorite_shows_movies FROM users WHERE username = %s", (username,))
    user_data = cursor.fetchone()
    cursor.close()

    # If no data found, use default "Friends"
    shows = user_data[0].split(";;") if user_data and user_data[0] else ["Friends"]
    
    
    # Randomly select a show
    selected_show = request.form.get('show_name') if request.method == 'POST' else random.choice(shows)

    # YouTube Data API search endpoint
    youtube_url = "https://www.googleapis.com/youtube/v3/search"

    # Query parameters
    params = {
        "part": "snippet",
        "q": f"{selected_show} scenes",
        "type": "video",
        "maxResults": 20,  # Fetch up to 10 videos
        "key": YOUTUBE_API_KEY
    }

    # Make the API request
    response = requests.get(youtube_url, params=params)
    data = response.json()
    print (data)

    # Extract video IDs from the results
    videos = [item['id']['videoId'] for item in data.get('items', [])]
    
    # Randomly select a video ID
    video_id = random.choice(videos) if videos else None

    # Render the page with the selected show and video ID
    return render_template('tv.html', video_id=video_id, show_name=selected_show)





#SPOTIFY
#SPOTIFY
#SPOTIFY
#SPOTIFY
#SPOTIFY
#SPOTIFY

@app.route('/music')
def music():
    session.clear()
    if os.path.exists(".cache"):
        os.remove(".cache")
    if 'token_info' in session:  # Check if the user is logged in
        # User is logged in, proceed to music page
        return render_template('music.html')
    else:
        # User is not logged in, redirect to login
        return redirect(url_for('loginspotify')) # Use url_for for better maintainability

# Spotify API credentials
CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')
SPOTIFY_SCOPE = os.getenv('SPOTIFY_SCOPE')

# Initialize Spotipy client
sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SPOTIFY_SCOPE
)



@app.route('/loginspotify')
def loginspotify():
    session.clear()
    if os.path.exists(".cache"):
        os.remove(".cache")
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    print ("works")
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect(url_for('stats'))


@app.route('/stats')
def stats():
    token_info = get_token()
    if not token_info:
        return redirect('/')
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    results = sp.current_user_top_artists(limit=10, time_range='long_term')
    top_artists = results['items']

    track_results = sp.current_user_top_tracks(limit=10, time_range='long_term')
    top_tracks = track_results['items']
    

    
    return render_template('music.html', top_artists=top_artists, top_tracks=top_tracks)

@app.route('/aboutme')
def aboutme():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    cursor = db.cursor()

    cursor.execute("SELECT birth_day,birth_month,birth_year FROM users WHERE username = %s", (username,))
    birth = cursor.fetchone()
    db.commit()

    cursor.execute("SELECT bio FROM users WHERE username = %s", (username,))
    bio = cursor.fetchone()
    db.commit()

    cursor.execute("SELECT news_interests FROM users WHERE username = %s", (username,))
    news_interests = cursor.fetchone()
    db.commit()

    cursor.execute("SELECT favorite_shows_movies FROM users WHERE username = %s", (username,))
    favorite_shows_movies = cursor.fetchone()
    db.commit()

    cursor.close()


    return render_template('aboutme.html', username=username,bio=bio[0], day=birth[0],month=birth[1],year=birth[2], news_interests=news_interests[0], favorite_shows_movies=favorite_shows_movies[0])



@app.route("/update_bio", methods=["POST"])
def update_bio():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    new_bio = request.form.get("bio")
    if new_bio:
        cursor = db.cursor()
        cursor.execute("UPDATE users SET bio = %s WHERE username = %s", (new_bio, username,))
        db.commit()
        cursor.close()

    
    return redirect("/aboutme")


@app.route("/update_news", methods=["POST"])
def update_news():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    news_interests = request.form.get("news_interests")
    if news_interests:
        cursor = db.cursor()
        cursor.execute("UPDATE users SET news_interests = %s WHERE username = %s", (news_interests, username,))
        db.commit()
        cursor.close()

    
    return redirect("/aboutme")



@app.route("/update_shows", methods=["POST"])
def update_shows():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    new_shows = request.form.get("favorite_shows_movies")
    if new_shows:
        cursor = db.cursor()
        cursor.execute("UPDATE users SET favorite_shows_movies = %s WHERE username = %s", (new_shows, username,))
        db.commit()
        cursor.close()

    
    return redirect("/aboutme")




@app.route('/switch-account')
def switch_account():
    print("Switching account...")
    session.clear()
    if os.path.exists(".cache"):
        os.remove(".cache")
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


def get_token():
    token_info = session.get('token_info', None)
    if not token_info:
        return None
    
    now = int(time.time())
    is_expired = token_info['expires_at'] - now < 60
    if is_expired:
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
    
    return token_info



#WORKING ON IT
@app.route('/generate', methods=['POST'])
def generate():
    # Get the token and create a Spotify client
    token_info = get_token()
    if not token_info:
        return redirect('/')

    sp = spotipy.Spotify(auth=token_info['access_token'])
    top_artists_str = request.form.get('top_artists')
    top_tracks_str = request.form.get('top_tracks')

    # Check if the form data was received
    if not top_artists_str or not top_tracks_str:
        return "Error: Missing form data.", 400

    # Convert strings to lists
    top_artists = top_artists_str.split(', ')
    top_tracks = top_tracks_str.split(', ')
    # Get the user's prompt from the form
    user_prompt = request.form.get('user_prompt')

    openai_prompt = (
        f"Top Artists:\n{top_artists}\n"
        f"Top Tracks:\n{top_tracks}\n"
        f"User Prompt:\n{user_prompt}"
    )
    headers = {
        'Content-Type': 'application/json',
    }


        

    completion = {
    "contents": [
        {
            "parts": [
                {"text": "Here's some info about the user:\n "+openai_prompt+"Here's what they want: "+user_prompt+"\nGive a list of 25 songs such that the list is in this format: [Song1:Artist1 ; Song2:Artist2; ...]. An example output is [Love Story:Taylor Swift ; Shape of You: Ed Sheeran]."}
            ]
        }
    ],
    "systemInstruction": {
    "role": "system",
    "parts": [
      {
        "text": "Provide a list of songs in this format: [Song1:Artist1 ; Song2:Artist2; ...] without bolding, italicizing, or adding commentary. Make sure the songs match the vibe of the user's request."
      }
    ]
  },
    "safetySettings": [
        
    {
      "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
      "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE"
    }
   ]
   }
    

    name = {
    "contents": [
        {
            "parts": [
                {"text": "Based on the following user prompt for a playlist: "+user_prompt+"\n Come up with a funny sarcastic short title for the Spotify playlist in a 90s mean girl way or dad joke way that makes fun of why the user's request and music taste'."}
            ]
        }
    ],
    "systemInstruction": {
    "role": "system",
    "parts": [
      {
        "text": "Only give one title for the playlist and just give the title without commentary. Nothing should be generated except the title."
      }
    ]
  }
    }
    api_key = os.getenv("API_KEY")

# Set the request URL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}"
    response = requests.post(url, headers=headers, json=completion)
    response = response.json()
    print (response)
    response_content=response['candidates'][0]['content']['parts'][0]['text']
    match=re.search(r'\[.*?\]', response_content.strip())
    response_content=match.group(0) 
    # Parse the response to extract songs and artists
    song_artist_pairs = [pair.strip() for pair in response_content.split(';')]
    tracks_to_search = []
    for pair in song_artist_pairs:
        if ':' in pair:
            song, artist = pair.split(':')
            tracks_to_search.append((song.strip(), artist.strip()))
    
    # Search for tracks on Spotify
    track_uris = []
    for song, artist in tracks_to_search:
        search_query = f"track:{song} artist:{artist}"
        search_results = sp.search(q=search_query, type='track', limit=1)
        if search_results['tracks']['items']:
            track_uris.append(search_results['tracks']['items'][0]['uri'])
    
    # Get the current user's ID
    user_id = sp.current_user()['id']
    response = requests.post(url, headers=headers, json=name)
    response = response.json()
    print (response)
    response_content=response['candidates'][0]['content']['parts'][0]['text']
    # Create a new playlist
    playlist_name = response_content
    # Create a new playlist
    
    playlist = sp.user_playlist_create(user=user_id, name=playlist_name, public=True)
    
    # Add tracks to the playlist
    if track_uris:
        sp.user_playlist_add_tracks(user=user_id, playlist_id=playlist['id'], tracks=track_uris)
    
    # Render the result page with the playlist link
    playlist_url = playlist['external_urls']['spotify']
    playlist_id = playlist['id']
    return render_template('music.html', playlist_url=playlist_url, playlist_name=playlist_name, playlist_id=playlist_id, top_artists=top_artists, top_tracks=top_tracks)





#BOOKS
#BOOKS
#BOOKS
#BOOKS
#BOOKS



books = [
    {
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "url": "https://www.gutenberg.org/files/1342/1342-h/1342-h.htm"
    },
    {
        "title": "Jane Eyre",
        "author": "Charlotte Bronte",
        "url": "https://www.gutenberg.org/files/1260/1260-h/1260-h.htm"
    },
    {
        "title": "The Three Musketeers",
        "author": "Alexandre Dumas",
        "url": "https://www.gutenberg.org/files/1257/1257-h/1257-h.htm"
    },
    {
        "title": "The Adventures of Sherlock Holmes",
        "author": "Arthur Conan Doyle",
        "url": "https://www.gutenberg.org/files/1661/1661-h/1661-h.htm"
    },
    {
        "title": "Little Women",
        "author": "Louisa May Alcott",
        "url": "https://www.gutenberg.org/files/514/514-h/514-h.htm"
    },
    {
        "title": "Anton Chekhov Short Stories",
        "author": "Anton Chekhov",
        "url": "https://www.gutenberg.org/files/57333/57333-h/57333-h.htm"
    }
    ,
    {
        "title": "Dracula",
        "author": "Bram Stoker",
        "url": "https://www.gutenberg.org/files/345/345-h/345-h.htm"
    }
    
]

@app.route('/books')
def books_page():
    return render_template('books.html', books=books)

@app.route('/book/<book_title>')
def book_page(book_title):
    # Find the book URL by title
    selected_book = next((book for book in books if book["title"].replace(" ", "-").lower() == book_title.lower()), None)
    
    if selected_book:
        return render_template('book.html',books=books, book=selected_book)
    else:
        return "Book not found", 404





#NEWS
#NEWS
#NEWS
#NEWS
#NEWS

#INTEREST_TOPICS = ["Celebrities","Movies","Fashion", "Animals", "Movies", "Video Games", "TV", "Fandom","Feminism"]





GEMINI_API_KEY = os.getenv('API_KEY')  # Gemini API Key

def generate_gemini_summary(article_summaries):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}"
    
    headers = {
        'Content-Type': 'application/json',
    }
    
    prompt = f"Summarize the following news articles in a conversational way that is entertaining (but also sensitive when needed):\n{article_summaries}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "systemInstruction": {
            "role": "system",
            "parts": [
                {"text": "Give a news summary of the articles in an entertaining way. Be serious when talking about sensitive topics though."}
            ]
        }
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        try:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError):
            return "Failed to generate a summary."
    
    return "Error retrieving summary from Gemini."





# API key and base URL
NEWS_API_KEY = os.getenv("NEWS_API")
NEWS_API_URL = "https://newsapi.org/v2/everything"

@app.route('/news')
def news():

    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    cursor = db.cursor()
    
    # Fetch news interests from the database
    cursor.execute("SELECT news_interests FROM users WHERE username = %s", (username,))
    user_data = cursor.fetchone()
    cursor.close()

    # If no interests are found, default to "Politics"
    INTEREST_TOPICS = user_data[0].split(";;") if user_data and user_data[0] else ["Politics"]
    articles=[]
    topic_index = 0  # Keep track of which topic to fetch next

    while len(articles) < 15:
        topic = INTEREST_TOPICS[topic_index]  # Select the current topic
        topic_index = (topic_index + 1) % len(INTEREST_TOPICS)  # Move to next topic in round-robin

        params = {
            "q": topic,
            "language": "en",
            "sortBy": "relevancy",
            "pageSize": 2,
            "apiKey": NEWS_API_KEY
        }
        
        response = requests.get(NEWS_API_URL, params=params)
        
        if response.status_code == 200:
            data = response.json()
            for article in data.get("articles", []):
                if len(articles) < 15:  # Stop once we have 10 articles
                    articles.append({
                        "title": article.get("title"),
                        "description": article.get("description"),
                        "url": article.get("url"),
                        "source": article.get("source", {}).get("name"),
                        "topic": topic  # Store the topic for reference
                    })
                    print (article.get("title"))
                else:
                    break  
    
    # Ensure no duplicate articles
    seen_urls = set()
    curated_articles = []
    for article in articles:
        if article['url'] not in seen_urls:
            curated_articles.append(article)
            seen_urls.add(article['url'])
    
    # Limit to 10 articles (in case duplicates were removed)
    curated_articles = curated_articles[:20]

    article_summaries = "\n".join([f"- {article['title']}: {article['description']}" for article in curated_articles if article['description']])
    gemini_summary = "No summary available."
    if article_summaries:
        gemini_summary = generate_gemini_summary(article_summaries)
    
    # Render news page with curated articles
    return render_template('news.html', articles=curated_articles, gemini_summary=gemini_summary)





#HISTORY
#HISTORY
#HISTORY
#HISTORY
#HISTORY









# API Endpoints and constants
CHRONICLING_AMERICA_API = "https://chroniclingamerica.loc.gov/suggest/titles/?q=manh&callback=suggest"
MEDIA_HISTORY_API = "https://mediahistoryproject.org/api/v1"

# Sample data for Zines
ZINE_DATA = "data/zines.json"


def fetch_chronicling_america(query):
    """Fetch title suggestions from Chronicling America."""
    params = {
        "q": query,
        "callback": "suggest"
    }
    
    try:
        response = requests.get(CHRONICLING_AMERICA_API, params=params)
        response.raise_for_status()
        # Extract the JSONP response and clean it
        content = response.text
        json_string = content[8:-2]  # Removing 'suggest(' and ');'
        data = json.loads(json_string)
        return {
            "query": data[0],
            "titles": data[1],
            "lccns": data[2],
            "urls": data[3],
        }
    except requests.RequestException as e:
        print(f"Error fetching data from Chronicling America API: {e}")
        return {}


def fetch_media_history(decade):
    """Fetch media data from Media History Digital Library."""
    params = {
        "year_start": decade,
        "year_end": decade + 9,
        "limit": 5,
    }
    response = requests.get(MEDIA_HISTORY_API, params=params)
    if response.ok:
        return response.json()
    return []


def fetch_wikimedia(decade):
    """Fetch image URLs from Wikimedia Commons based on a given decade."""
    WIKIMEDIA_COMMONS_API = "https://en.wikipedia.org/w/api.php"
    
    # First query: search for pages related to the given decade
    search_params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"{decade}s People",
        "gsrlimit": 5
    }
    
    response = requests.get(WIKIMEDIA_COMMONS_API, params=search_params)
    
    if response.ok:
        data = response.json()
        print (data)
        pages = data.get("query", {}).get("pages", {})
        page_ids = [page["pageid"] for page in pages.values()]

        # Second query: fetch images from the identified pages
        if page_ids:
            image_params = {
                "action": "query",
                "format": "json",
                "pageids": '|'.join(map(str, page_ids)),
                "prop": "images"
            }
            
            image_response = requests.get(WIKIMEDIA_COMMONS_API, params=image_params)
            
            if image_response.ok:
                image_data = image_response.json()
                print (image_data)
                images = []

                for page in image_data.get("query", {}).get("pages", {}).values():
                    if "images" in page:
                        images.extend([img["title"] for img in page["images"]])

                # Fetch URLs for each image title
                image_urls = []
                for image in images:
                    img_info_params = {
                        "action": "query",
                        "format": "json",
                        "titles": image,
                        "prop": "imageinfo",
                        "iiprop": "url"
                    }
                    img_info_response = requests.get(WIKIMEDIA_COMMONS_API, params=img_info_params)
                    if img_info_response.ok:
                        img_info_data = img_info_response.json()
                        for img_page in img_info_data.get("query", {}).get("pages", {}).values():
                            if "imageinfo" in img_page:
                                image_urls.append(img_page["imageinfo"][0]["url"])
                
                return image_urls
            
    return []


API_KEY = 'your_api_key_here'
API_URL = 'https://api.ap.org/media/v2.0/content/feed'

def get_feed(query, page_size=10):
    headers = {
        'x-api-key': API_KEY
    }
    params = {
        'q': query,
        'page_size': page_size
    }
    response = requests.get(API_URL, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None



@app.route("/history")
def history():
    """Homepage."""
    return render_template("history.html")


@app.route("/decade/<int:decade>")
def show_decade(decade):
    """Show content for a specific decade."""
    chronicling_data = fetch_chronicling_america(decade)
    media_data = fetch_media_history(decade)
    wikimedia_images = fetch_wikimedia(decade)

    try:
        with open(ZINE_DATA, "r") as f:
            zines = json.load(f)  # Parse JSON data for zines
    except FileNotFoundError:
        zines = [] 

    return render_template(
        "decade.html",
        decade=decade,
        chronicling_data=chronicling_data,
        media_data=media_data,
        wikimedia_images=wikimedia_images,
       zines=zines
    )






























#END 
#END
#END
#END








if __name__ == '__main__':
    app.run(debug=True)