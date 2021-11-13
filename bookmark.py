import tweepy
import os
import time
import requests
import json
import yaml


class BookmarkTweets:

    def __init__(self):
        with open("my_variables.yml", 'r') as stream:
            try:
                self.my_variables_map = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print("[Error]: while reading yml file", exc)
        self.initialiseTwitterClient()
        self.data = None

    def initialiseTwitterClient(self):
        # Read Twitter Credentials
        consumer_key = self.my_variables_map["TWITTER_CONSUMER_KEY"]
        consumer_secret = self.my_variables_map["TWITTER_CONSUMER_SECRET"]
        access_token = self.my_variables_map["TWITTER_ACCESS_TOKEN"]
        access_token_secret = self.my_variables_map["TWITTER_ACCESS_SECRET"]
        # Create and Intialise Twitter Api Client
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        self.twitterClient = tweepy.API(auth)

    def downloadTweets(self):
        """
        Download teeet data with similar replies: 
        Ex: `@TnvMadhav save=Notion #web3`
        """
        # Search for mentions
        fetched_tweets = self.twitterClient.search("@TnvMadhav save=Notion", count=100)
        data = []
        for fetched_tweet in fetched_tweets:
            d = {}
            d["Created At"] = fetched_tweet.created_at.isoformat()
            d["Original Tweet"] = "https://twitter.com/twitter/status/" + fetched_tweet.id_str
            d["Tweet Author"] = fetched_tweet._json["in_reply_to_screen_name"] or "unknown"
            if fetched_tweet._json["entities"] and fetched_tweet._json["entities"]["hashtags"]:
                d["Context"] = fetched_tweet._json["entities"]["hashtags"][0]["text"]
            else:
                d["Context"] = "Random"
            d["Saved By"] = self.my_variables_map["TWITTER_HANDLE"]
            data.append(d)
        self.data = data
    
    def saveToNotion(self):
        """
        A notion database (if integration is enabled) page with id `datbaseId`
        will updated with the Tweet Information.
        """
        url = "https://api.notion.com/v1/Pages/"
        headers = {
            'Notion-Version': '2021-08-16',
            'Authorization': 'Bearer ' + self.my_variables_map["NOTION_INTEGRATION_KEY"],
            'Content-Type': 'application/json'
        }
        database = self.my_variables_map["NOTION_DATABASE_ID"]
        db_query_endpoint = f"https://api.notion.com/v1/databases/{database}/query"
        for entry in self.data:
            body = json.dumps({
                "filter": {
                    "property": "Original Tweet",
                    "text": {
                        "contains": entry["Original Tweet"]
                    }
                }
            })
            response = requests.request("POST", db_query_endpoint, headers=headers, data=body)
            # Check if tweet link already stored in Notion Database
            if len(response.json()["results"]) > 0:
                print("Data already in notion")
                continue
            # Create Payload to save tweet data in Notion Database
            payload = json.dumps({
            "parent": {
                "database_id": database,
            },
            "properties": {
                "Context": {
                "type": "select",
                "select": {
                    "name": entry["Context"]
                }
                },
                "Created At": {
                "type": "date",
                "date": {
                    "start": entry["Created At"]
                }
                },
                "Original Tweet": {
                "id": "title",
                "type": "title",
                "title": [
                    {
                    "type": "text",
                    "text": {
                        "content": entry["Original Tweet"],
                        "link": {
                        "url": entry["Original Tweet"]
                        }
                    }
                    }
                ]
                },
                "Saved By": {
                "type": "rich_text",
                "rich_text": [
                    {
                    "type": "text",
                    "text": {
                        "content": entry["Saved By"]
                    }
                    }
                ]
                },
                "Tweet Author": {
                "type": "rich_text",
                "rich_text": [
                    {
                    "type": "text",
                    "text": {
                        "content": entry["Tweet Author"]
                    }
                    }
                ]
                }
            }
            })
            response = requests.request("POST", url, headers=headers, data=payload)
            # Print Response in the Terminal Console (for user debugging)
            print(response.text)

    def updateIndefinitely(self):
        """
        Orchestrates downloading of tweet links and updating the same
        in notion database.
        """
        while True:
            try:
                self.downloadTweets()
                self.saveToNotion()
            except Exception as e:
                print(f"[Error encountered]: {e}")
            # Sleep for 2 seconds before next iteration of updates
            time.sleep(2)

if __name__ == "__main__":
    # With 😴 sleeps to prevent rate limit from kicking in.
    BookmarkTweets().updateIndefinitely()