import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timezone
import json
import yaml
from sql import add_video

_cached_user_id = None
# open and load the config file
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

def crawl_house(con):
    response = requests.get(config["sources"]["house"]["base_url"]+config["sources"]["house"]["listing_url"])
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    new_videos = []
    for link in soup.find_all("a", href=re.compile(r"\.mp4$", re.IGNORECASE)):
        video_url = config['sources']['house']['base_url'] + link['href']
        name_start = link['href'].index('=') + 1
        filename = link['href'][name_start:]
        download_url = config['sources']['house']['base_url'] + config['sources']['house']['mp4_base'] + filename
        if add_video(con, url=video_url, title=filename, source='house', download_url=download_url):
            new_videos.append({'url': video_url, 'filename': filename, 'download_url': download_url, 'source': 'house'})
    return new_videos

def get_senate_user_id():
    global _cached_user_id
    if _cached_user_id:
        return _cached_user_id

    response = requests.get(config["sources"]["senate"]["config_api"], headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    data = response.json()
    _cached_user_id = data["user"]
    return _cached_user_id

def get_senate_recent_videos():
    user_id = get_senate_user_id()
    url = config["sources"]["senate"]["recent_api"].format(user_id=user_id)
    response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    # print(response.json()[0])
    return response.json()

def get_senate_video_url(video_id, user_id):
    response = requests.post(config["sources"]["senate"]["media_api"], 
    json={"file":{"_id": video_id}, "user": {"_id": user_id}, "type": "MP4"})
    response.raise_for_status()
    data = response.json()
    if not data.get("response", {}).get("success"):
        return None

    return data.get("response").get("payload").get("data")

def get_senate_captions_url(video_id, user_id):
    response = requests.post(config["sources"]["senate"]["captions_api"], 
    json={"file":{"_id": video_id}, "user": {"_id": user_id}})
    response.raise_for_status()
    data = response.json()

    if not data.get("response", {}).get("success"):
        return None

    return data.get("response").get("payload")

def crawl_senate(con):
    user_id = get_senate_user_id()
    recent_videos = get_senate_recent_videos()
    new_videos = []

    for video in recent_videos:
        video_id = video["_id"]
        title = video.get("metadata", {}).get("filename", "Untitled")
        is_captioned = video.get("captioned", False)
        url = "https://cloud.castus.tv/vod/misenate/video/" + video_id

        added = add_video(
            con,
            url=url,
            title=title,
            source="senate",
            download_url=None,       
            captions_url=None,
            video_id=video_id,        
            captioned_flag=video.get("captioned", False)
        )

        if added:
            new_videos.append({"video_id": video_id, "title": title})

    return new_videos


