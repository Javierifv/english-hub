import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "duohub.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

content_ch1_family = """My name is Robinson. I am from England. I am eighteen years old. My father is German. My mother is English. I have two brothers. I have one sister. We are a good family.

My father is a good businessman. We have money. I have a good school. I have a good life. But I have a dream. I want to travel. I want to see the world.

My father is a good man. He wants the best for me. But my dream is not his dream. He is not happy. The situation is not easy.

It is morning. My father is in his room. He wants to speak with me. I go to his room. My father has some questions. My father wants to know why I want to travel.

My father says, "Travelling is dangerous. Travelling is not comfortable. You can die."

I think about it. Travelling is dangerous. It is not comfortable. I can die. But it is also very interesting. I can see new countries. I can meet new people.

I think about travelling every day. Maybe my mother can help me.

I speak with my mother. I tell my mother, "I want to travel. I want to see the world. Please, speak with my father. Maybe with your help, I can travel."

My mother loves me. But she thinks that travelling is dangerous. She thinks that my place is at home. She thinks that life in England is the best for me.

One year later, I visit one big town. The name of this town is Hull.

I meet my friend. His father has a ship. They travel to London. My friend tells me, "Go with me."

I think about it. I am not prepared. But I can try if travelling is for me.

I go to London. I am very happy. It is my first long journey. It is very interesting. The first hour is good. But then we have problems. We see a storm. The storm is big. The wind is strong. The ship goes up and down. I have fear. I think about my home. I think about my comfortable bed.

The storm is finished in the morning. The weather is nice. And the evening is beautiful. Everything is quiet.

One man comes to me. We speak. We speak about the storm. I speak about my fear. The man gives me a drink. I drink very much. I sleep very well at night.

The next day, I forget about my home. I forget about my comfortable bed. I dream more about travelling."""

title = "[Nivel 1 (A1/A2)] Cap. 1 - Family"
key_vocab = json.dumps(["travel", "dream", "businessman", "dangerous", "situation", "journey", "storm", "ship"])

cursor.execute("""
    UPDATE readings
    SET title = ?, content = ?, key_vocabulary = ?, topic = 'Robinson Crusoe', source = 'https://www.robinsoncrusoeinlevels.com/'
    WHERE day_number = 1 AND level = 'A1'
""", (title, content_ch1_family, key_vocab))

conn.commit()
print("Updated Level 1 Chapter 1 with Robinson Crusoe - Family!")
conn.close()
