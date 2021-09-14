#!/usr/bin/env python
# -*- coding: utf-8 -*-
import flask
from flask import Flask, render_template, jsonify, request
import joblib
import io
import base64 as b64
import pandas as pd
import numpy as np

# Time imports
import time as t
from datetime import datetime

# Tensorflow imports
from tensorflow import keras
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from flask import Flask, render_template, request

# Matplotib imports
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
# conda install -c conda-forge wordcloud
from PIL import Image
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator
#world map imports
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import re
import urllib
import folium

# Spark imports
import findspark

findspark.init()
import pyspark
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.sql import functions as F
from pyspark.sql.types import StringType

import tweepy
from tweepy import OAuthHandler # to authenticate Twitter API
from tweepy import Stream
from tweepy.streaming import StreamListener
import socket
import json
import threading

# Twitter developer Credentials to connect to twitter account
access_token = "1349741730791211009-EK0sfJl2Pii39XZPqm01kpOc3DLG3m"
access_secret= "qDJMRudNSbLivCvq81YEEgGkDSjAOnIYO9ozzJIJLfBwF"
consumer_key = "qEOSXDRumiptN17uNBlviYKUG"
consumer_secret = "U2VowST2I0mCrZbdjremTYGUCv0BLKDHOiQY9ZsCwGbI7XtTNb"

# Setting twitter developer credentials with TweePy
auth = OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_secret)


app = Flask(__name__)

#TweePy listener object
class TweetsListener(StreamListener):
    # initialized the constructor
    def __init__(self, csocket):
        self.client_socket = csocket

    def on_data(self, data):
        try:
            msg = json.loads( data )
            # if tweet is longer than 140 characters
            timestamp = str(msg['created_at'])
            if "extended_tweet" in msg:
                if msg['user']['location']:
                    text = str(msg['extended_tweet']['full_text'])
                    location = str(msg['user']['location'])
                    tEnd = "t_end"
                    chase = "["+location+"]"+"{"+timestamp+"}"+text+tEnd
                    
                    self.client_socket\
                    .send(chase\
                    .encode('utf-8'))  
                #else we still want the time info
                else:
                    text = str(msg['extended_tweet']['full_text'])
                    tEnd = "t_end"
                    chase = "{"+timestamp+"}"+text+tEnd
                    self.client_socket\
                    .send(chase\
                    .encode('utf-8'))  

            else:
                if msg['user']['location']:
                    text = str(msg['text'])
                    location = str(msg['user']['location']) 
                    tEnd = "t_end"
                    chase = "["+location+"]"+"{"+timestamp+"}"+text+tEnd
                    
                    self.client_socket\
                    .send(chase\
                    .encode('utf-8'))  
                      
                #else we still want the time info
                else:
                    text = str(msg['text'])
                    tEnd = "t_end"
                    chase = "{"+timestamp+"}"+text+tEnd
                    self.client_socket\
                    .send(chase\
                    .encode('utf-8')) 
            return True

        except BaseException as e:
            # Error handling
            print("Error : %s" % str(e))
            return False
      
    def on_error(self, status):
        print(status)
        return True

#function to initiate and connect with a socket
def socketTrigger(s, host, port, keyword):
    s.bind((host, port))
    s.listen(5)
    c, addr = s.accept()
    with c:
        print('Connected by', addr)
        twitter_stream = Stream(auth, TweetsListener(c))
        twitter_stream.filter(track=[keyword], languages=["en"])
        while True:
            data = c.recv(1024)
            if not data:
                break
            
# function to terminate read/write queries 
def queryTerminator(query):
    query.stop()

# function to preprocess tweets
def preprocessing(lines):
    words = lines.select(explode(split(lines.value, "t_end")).alias("Tweet"))
    words = words.na.replace('', None)
    words = words.na.drop()
    words = words.withColumn('Tweet', F.regexp_replace('Tweet', r'http\S+', ''))
    words = words.withColumn('Tweet', F.regexp_replace('Tweet', '@\w+', ''))
    words = words.withColumn('Tweet', F.regexp_replace('Tweet', '#', ''))
    words = words.withColumn('Tweet', F.regexp_replace('Tweet', 'RT', ''))
    words = words.withColumn('Tweet', F.regexp_replace('Tweet', ':', ''))
    return words

def deEmojify(text):
    regrex_pattern = re.compile(pattern = "["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                           "]+", flags = re.UNICODE)
    return regrex_pattern.sub(r'',text)

def SentimentPredictor(to_predict_tweet):
    tw = PN_data_tokenizer.texts_to_sequences([to_predict_tweet])
    tw = pad_sequences(tw, maxlen=200)
    a = Sentiment_model.predict(tw)
    confidence = a.round(2).item()
    result = int(a.round().item())
    return result, confidence

def RTPredictor(to_predict_tweet):
    tw = RT_data_tokenizer.texts_to_sequences([to_predict_tweet])
    tw = pad_sequences(tw, maxlen=200)
    a = RT_model.predict(tw)
    confidence = a.round(2).item()
    result = int(a.round().item())
    return result, confidence

def applyModel(dataDF):
    index = 0
    for i, j in dataDF.iterrows():
        Sresult, confidence = SentimentPredictor(j[0])
        RTresult, confidenceRT = RTPredictor(j[0])
        #extract all within the square brackets which is the  location encoded in socket
        location = re.findall('\[(.*?)\]', str(j[0]))
        timestamp = re.findall('\{(.*?)\}', str(j[0]))

        #convert to python datetime
        if timestamp:
            timestamp = datetime.strftime(datetime.strptime(timestamp[0],'%a %b %d %H%M%S +0000 %Y'), '%Y-%m-%d %H:%M:%S')

        dataDF.loc[index, 'Location'] = location
        dataDF.loc[index, 'Timestamp'] = timestamp
        dataDF.loc[index, 'Sentiment Confidence'] = confidence
        dataDF.loc[index, 'RT Confidence'] = confidenceRT

        #remove all timestamps in the tweet text

        if Sresult == 1:
            if RTresult == 1:
                dataDF.loc[index, 'Sentiment'] = "Positive"
                dataDF.loc[index, 'Relaxed/Tensed'] = 'Relaxed'

            else:
                dataDF.loc[index, 'Sentiment'] = "Positive"
                dataDF.loc[index, 'Relaxed/Tensed'] = "Tensed"

        else:
            if RTresult == 1:
                dataDF.loc[index, 'Sentiment'] = "Negative"
                dataDF.loc[index, 'Relaxed/Tensed'] = 'Relaxed'
            else:
                dataDF.loc[index, 'Sentiment'] = "Negative"
                dataDF.loc[index, 'Relaxed/Tensed'] = 'Tensed'

        index += 1
    #remove the encoded locations and timestamps
    dataDF['Tweet'] = dataDF['Tweet'].str.replace(r"\{.*\}","")
    dataDF['Tweet'] = dataDF['Tweet'].str.replace(r"\[.*\]","")
    return dataDF


@app.route("/")
@app.route("/index.html")
def index():
    now = datetime.now()
    date_time = now.strftime("%d/%m/%Y, %H:%M:%S")
    return flask.render_template("index.html", date_time=date_time)


# post method from index form will get routed to /predict.html
def result():
    global tweetDF
    
    if request.method == "POST":
        to_predict = request.form['TestTweet']
        global s
        s = socket.socket()

        # Get local machine name : host and port
        host = "127.0.0.1"
        port = 3333

        # The socket has to be initiated on a separate thread as it needs to run in parallel with the main program
        # It takes the entered query as a parameter to fetch tweets about the topic
        SocketListener = threading.Thread(target=socketTrigger, args=[s, host, port, to_predict])
        SocketListener.start()

        # read the tweet data from socket
        unfiltered_stream = spark \
            .readStream \
            .format("socket") \
            .option("host", "127.0.0.1") \
            .option("port", 3333) \
            .load()

        # convert incoming tweets into String value
        df = preprocessing(unfiltered_stream)
        # Create a dataframe
        df = df.toDF("Tweet")
        df = df.withColumn('Sentiment', lit("empty").cast(StringType()))
        df = df.withColumn('Relaxed/Tensed', lit("empty").cast(StringType()))
        df = df.withColumn('Location', lit("empty").cast(StringType()))
        df = df.withColumn('Timestamp', lit("empty").cast(StringType()))
        df = df.withColumn('Sentiment Confidence', lit("empty").cast(StringType()))
        df = df.withColumn('RT Confidence', lit("empty").cast(StringType()))
        print("----- streaming is running -------")
        
        # write the above data into memory. consider the entire analysis in all iteration (output mode = complete).
        # and let the trigger runs in every 2 secs.
        global writeTweet
        writeTweet = df.writeStream. \
            outputMode("append"). \
            format("memory"). \
            queryName("tweetquery"). \
            trigger(processingTime='20 seconds'). \
            start()

        # Input time to sleep
        seconds = int(20)
        for i in range(seconds):
            t.sleep(1)
            print(str(seconds - i) + " seconds remaining ")

        print("Time to view sentiment!")

        # Prints a json object of the input and output of the iteration
        print(writeTweet.lastProgress)
        sparkdf = spark.sql("SELECT * FROM tweetquery where Tweet <> ''")
        pd.set_option('display.max_colwidth', None)
        tweetDF = sparkdf.toPandas()
        # Once the tweets have been stored in a dataframe, we apply the DL models to estimate the sentiments
        tweetDF = applyModel(tweetDF)
        
    return (tweetDF)


@app.route("/predict", methods=["POST"])
def predict():
    global tweetDF
    result()
    return render_template('predict.html', tables=[tweetDF.to_html(classes='data', header=True, index=False)])

# function that loads more tweets on the screen for bigger analysis
def reload():
    global tweetDF
    sparkdf = spark.sql("SELECT * FROM tweetquery where Tweet <> '' LIMIT 50")
        
    df2 = sparkdf.toPandas()
    # Merging the previously assessed tweets with the new ones just fetched
    newTweets = pd.merge(df2, tweetDF, on=['Tweet'], how="left", indicator=True).query('_merge=="left_only"')
    newTweets.rename(columns = {'Sentiment_x':'Sentiment', 'Relaxed/Tensed_x':'Relaxed/Tensed', 'Location_x':'Location','Timestamp_x':'Timestamp', 'Sentiment Confidence_x':'Sentiment Confidence', 'RT Confidence_x':'RT Confidence'}, inplace = True)  
    newTweets = newTweets.drop(['Sentiment_y', 'Relaxed/Tensed_y', 'Location_y', 'Timestamp_y', 'Sentiment Confidence_y', 'RT Confidence_y', '_merge'], axis = 1)
    # Adding 150 tweets to the dataframe
    newTweets = newTweets.head(150).reset_index()
    newTweets = newTweets.drop(['index'], axis = 1)
    newTweets = applyModel(newTweets)
    # After the model is applied, the new tweets are appended to the tweets dataframe with sentiments.
    tweetDF = pd.concat([tweetDF, newTweets], ignore_index = True)


@app.route("/reload", methods=["GET"])
def reloadDF():
    global tweetDF
    reload()
    return render_template('predict.html', tables=[tweetDF.to_html(classes='data', header=True, index=False)])


@app.route("/barchart", methods=["GET"])
def viewBarchart():
    if request.method == "GET":
        # Find number of positive sentiment
        positive = tweetDF["Sentiment"].value_counts()[1]

        # Find number of negative sentiment
        negative = tweetDF["Sentiment"].value_counts()[0]

        # Design plot
        labels = ['Positive', 'Negative']
        sentimentCount = [positive, negative]

        x = np.arange(len(labels))  # the label locations
        width = 0.35  # the width of the bars

        fig, ax = plt.subplots()
        fig.set_facecolor('#FFFFFF')
        ax.bar(x, sentimentCount, width)

        # Add some text for labels, title and custom x-axis tick labels, etc.
        ax.set_ylabel('Scores')
        ax.set_title('Twitter Sentiment Analysis')
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.legend()

        fig.tight_layout()

        # Convert plot to PNG image
        pngImage = io.BytesIO()
        FigureCanvas(fig).print_png(pngImage)

        # Encode PNG image to base64 string
        pngImageB64String = "data:image/png;base64,"
        pngImageB64String += b64.b64encode(pngImage.getvalue()).decode('utf8')
    return render_template('barchart.html', image=pngImageB64String)


@app.route("/pieChart", methods=["GET"])
def pieChart():
    global tweetDF
    result()
	
    nTensed = tweetDF.groupby('Sentiment')['Relaxed/Tensed'].value_counts()[0]
    nRelaxed = tweetDF.groupby('Sentiment')['Relaxed/Tensed'].value_counts()[1]
    pTensed = tweetDF.groupby('Sentiment')['Relaxed/Tensed'].value_counts()[2]
    pRelaxed = tweetDF.groupby('Sentiment')['Relaxed/Tensed'].value_counts()[3]

    sentimentCount = [nTensed, nRelaxed, pTensed, pRelaxed]
    labels = ['Negative/Tensed', 'Negative/Relaxed', 'Positive/Tensed', 'Positive/Relaxed']
	
    colors = ['#d22340','#fe90a2','#9271ad','#81b9ff']	
	
    fig, ax = plt.subplots()
    fig.set_facecolor('#FFFFFF')
    ax.pie(sentimentCount, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
    ax.axis('equal')

    pngImage = io.BytesIO()
    FigureCanvas(fig).print_png(pngImage)

    # Encode PNG image to base64 string
    pngImageB64String = "data:image/png;base64,"
    pngImageB64String += b64.b64encode(pngImage.getvalue()).decode('utf8')

    return render_template('pieChart.html', image=pngImageB64String)


def wordCloudImage():
    global tweetDF
    result()
    images = []
    labels = []
    text = " ".join(str(tweet) for tweet in tweetDF['Tweet'])
    # Create and generate a word cloud image:
    wordcloud = WordCloud(max_words=100, background_color="white").generate(text)

    # Display the generated image:
    plt.imshow(wordcloud, interpolation='bilinear', aspect='auto')
    plt.axis("off")
    image = io.BytesIO()
    plt.savefig(image, format='png')
    image.seek(0)
    string = b64.b64encode(image.read())
    image_64 = 'data:image/png;base64,' + urllib.parse.quote(string)
    return image_64


@app.route("/wordCloud", methods=["GET"])
def viewWordCloud():
    images = wordCloudImage()
    return render_template('wordCloud.html', image=images)

@app.route("/worldMap")
def base():
    global tweetDF
    locator = Nominatim(user_agent="myGeocoder")
    mapDF = tweetDF
    mapDF = mapDF[mapDF["Location"].str.len() != 0]
	# 1 - int function to delay between geocoding calls (to prevent flooding the free service)
    geocode = RateLimiter(locator.geocode, min_delay_seconds=0.5)
    # 2- - create location column
    mapDF['Location'] = mapDF['Location'].apply(geocode)
    mapDF = mapDF[mapDF.Location.notnull()]
    # 3 - create longitude, laatitude and altitude from location column (returns tuple)
    mapDF['point'] = mapDF['Location'].apply(lambda loc: tuple(loc.point) if loc else None)
    # 4 - split point column into latitude, longitude and altitude columns
    mapDF[['latitude', 'longitude', 'altitude']] = pd.DataFrame(mapDF['point'].tolist(), index=mapDF.index)
    map1 = folium.Map(
        location=[1.290270,103.851959]
    )
	
    mapDF.apply(lambda row:folium.CircleMarker(location=[row["latitude"], row["longitude"]], popup=row["Tweet"], fill=True, tooltip=row["Sentiment"]).add_to(map1), axis=1)
	
    folium.Marker
    return map1._repr_html_()

@app.route("/tweets", methods=["GET"])
def viewTweets():
    return render_template('predict.html', tables=[tweetDF.to_html(classes='data', header=True, index=False)])

#function to reset the TweePy listener in order to enter new query in the search bar
@app.route("/home")
def resetSearch():
    now = datetime.now()
    date_time = now.strftime("%d/%m/%Y, %H:%M:%S")
    stopWriteStream = threading.Thread(target=queryTerminator, args=[writeTweet])
    stopWriteStream.start()
    spark.streams.awaitAnyTermination()
    spark.streams.resetTerminated()
    return flask.render_template("index.html", date_time=date_time)

if __name__ == '__main__':
    tweetDF = pd.DataFrame(columns=['Tweet', 'Sentiment', 'Relaxed/Tensed'])
    # initiating SparkSession
    spark = SparkSession.builder.appName("TwitterSentimentAnalysis").getOrCreate()
    # globally loaded trained model
    Sentiment_model = keras.models.load_model("PNmodel.h5")
    RT_model = keras.models.load_model("RTmodel.h5")
    PN_data_tokenizer = joblib.load("PN_data_tokenizer.joblib")
    RT_data_tokenizer = joblib.load("RT_data_tokenizer.joblib")
    app.run(debug=True)
    tweetList = []
