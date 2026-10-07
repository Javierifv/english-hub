import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "duohub.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

content_ch1_level1 = """I am six years old. I see a nice picture. The picture is in a book. It is a picture of a big snake. The snake eats an animal. Here is the picture.

The book says, "Snakes eat the whole animal. And they sleep for six months."
I think about the life in the forest. I make my first picture. This is my picture number one.

I show my fantastic picture to one person. And I ask this person, "Are you scared?"
This person answers, "How can I be scared? It is a hat."
My picture is not a picture of a hat. It is a picture of a big snake. An elephant is inside the snake. Then I make my picture number two. The picture shows the inside of the big snake. Now people understand. This is my picture number two.

People tell me what they think. They tell me that it is not good to make pictures. They tell me that it is better to study geography, history, maths and grammar. After these words, I don’t want to make pictures. I don’t want to make pictures because my picture number one and picture number two are not good for the people. People don’t understand simple things.

And now, I am not a child. I am a big person. I have a job. I am a pilot. I fly planes. I fly in many countries. And it is true that geography is good for me. Geography can help me if I am lost in the night.

During my life, I work with the people a lot. They are usually serious people. Sometimes I meet a person who is a little normal. When I meet this person, I show him my picture number one. I always have this picture with me. I want to know if this person understands life. But the person always says, "It is a hat." Then I never speak to this person about big snakes or forests or stars. And we speak about work, sport and family. And the person is happy. For him I am a normal man.

I live alone. I don’t know people for an open conversation. But one day it all changes. I have an accident in the Sahara Desert.
Something is broken in my plane. I have nobody in the plane with me. It is not easy to repair the plane alone. But I must do it. It is a question of life or death. I have water for only a week."""

title = "[Nivel 1 (A1/A2)] Cap. 1 - Hat"
key_vocab = '["snake", "picture", "scared", "pilot", "desert", "accident"]'

cursor.execute("""
    UPDATE readings
    SET title = ?, content = ?, key_vocabulary = ?, topic = 'The Little Prince / Robinson Crusoe in Levels'
    WHERE day_number = 1 AND level = 'A1'
""", (title, content_ch1_level1, key_vocab))

conn.commit()
print("Updated Level 1 Chapter 1 with 100% exact text from website!")
conn.close()
