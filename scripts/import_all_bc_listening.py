import asyncio
import edge_tts
import json
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "duohub.db")
DOCS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "material", "listening")

os.makedirs(DOCS_PATH, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

# Curated British Council Listening Curriculum (60 Tracks: 12 per level A1, A2, B1, B2, C1)
LESSONS = [
    # ==========================================
    # LEVEL A1 (12 LESSONS)
    # ==========================================
    {
        "id_code": "a1_01_request_from_your_boss",
        "day_number": 1,
        "level": "A1",
        "title": "A Request from Your Boss",
        "topic": "Workplace Tasks & Priority Management",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a1-listening/a-request-from-your-boss",
        "audio_filename": "a1_request_from_your_boss.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Hi, Mario. Can you help me prepare some things for the next month?"),
            ("en-GB-RyanNeural", "OK, sure. What can I help you with?"),
            ("en-GB-SoniaNeural", "I need to visit the customer in Germany. It's important."),
            ("en-GB-RyanNeural", "What can I do to help?"),
            ("en-GB-SoniaNeural", "Can you send an email to the customer? Ask them when I can visit them next week. Please do this first. It's a priority and very urgent."),
            ("en-GB-RyanNeural", "Right. I'll do it today."),
            ("en-GB-SoniaNeural", "Thanks. This next task is also important. Can you invite everyone to the next team meeting?"),
            ("en-GB-RyanNeural", "Yes, I will."),
            ("en-GB-SoniaNeural", "But first you need to book a meeting room. After that, please send everyone an email about it."),
            ("en-GB-RyanNeural", "Yes, of course."),
            ("en-GB-SoniaNeural", "And finally, can you write a short report about our new project? I have to give a presentation to our managers next month. Please do it when you have time – sometime in the next two or three weeks. It's not too urgent."),
            ("en-GB-RyanNeural", "Sure, no problem. I can do it this week."),
            ("en-GB-SoniaNeural", "There's no hurry. Take your time.")
        ],
        "chunks": [
            "Hi Mario. Can you help me prepare some things for the next month?",
            "I need to visit the customer in Germany. It's important.",
            "Can you send an email to the customer? Ask them when I can visit them next week.",
            "Please do this first. It's a priority and very urgent.",
            "Can you invite everyone to the next team meeting?",
            "But first you need to book a meeting room.",
            "And finally, can you write a short report about our new project?",
            "There's no hurry. Take your time."
        ]
    },
    {
        "id_code": "a1_02_booking_a_table",
        "day_number": 2,
        "level": "A1",
        "title": "Booking a Table at a Restaurant",
        "topic": "Restaurant Reservation & Confirmation",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a1-listening/booking-table",
        "audio_filename": "a1_booking_a_table.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Good evening, Mario's Restaurant. How can I help you?"),
            ("en-GB-RyanNeural", "Hello, I would like to book a table for dinner, please."),
            ("en-GB-SoniaNeural", "Of course. For what day and what time?"),
            ("en-GB-RyanNeural", "For tomorrow night, Wednesday, at seven thirty."),
            ("en-GB-SoniaNeural", "And for how many people?"),
            ("en-GB-RyanNeural", "A table for four people, please."),
            ("en-GB-SoniaNeural", "Inside or outside on the terrace?"),
            ("en-GB-RyanNeural", "Outside on the terrace, please, if possible."),
            ("en-GB-SoniaNeural", "Wonderful. Can I take your name and contact phone number?"),
            ("en-GB-RyanNeural", "Yes, my name is David Miller, and my number is 555-0192."),
            ("en-GB-SoniaNeural", "Great. Table for four, Wednesday at seven thirty. We look forward to seeing you tomorrow, Mr. Miller."),
            ("en-GB-RyanNeural", "Thank you very much. Goodbye.")
        ],
        "chunks": [
            "Good evening, Mario's Restaurant. How can I help you?",
            "Hello, I would like to book a table for dinner, please.",
            "For tomorrow night, Wednesday, at seven thirty.",
            "A table for four people, please.",
            "Outside on the terrace, please, if possible.",
            "Can I take your name and contact phone number?",
            "We look forward to seeing you tomorrow, Mr. Miller."
        ]
    },
    {
        "id_code": "a1_03_the_first_english_class",
        "day_number": 3,
        "level": "A1",
        "title": "The First English Class",
        "topic": "Classroom Welcome, Rules & Schedule",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a1-listening/the-first-english-class",
        "audio_filename": "a1_the_first_english_class.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Good morning everyone, and welcome to our English class."),
            ("en-GB-SoniaNeural", "My name is Ms. Jenkins, and I am your teacher for this term."),
            ("en-GB-SoniaNeural", "Before we begin, here are three important rules for our course."),
            ("en-GB-SoniaNeural", "First, please arrive on time. Our class starts at nine o'clock sharp every morning."),
            ("en-GB-SoniaNeural", "Second, please speak in English as much as you can, even when you make mistakes. Making mistakes is part of learning."),
            ("en-GB-SoniaNeural", "Third, bring your notebook, a pen, and an English dictionary every day."),
            ("en-GB-SoniaNeural", "Our homework will be posted on the board every Thursday."),
            ("en-GB-SoniaNeural", "Does anyone have any questions? Great, let's open our books to page five.")
        ],
        "chunks": [
            "Good morning everyone, and welcome to our English class.",
            "My name is Ms. Jenkins, and I am your teacher for this term.",
            "First, please arrive on time. Our class starts at nine o'clock sharp.",
            "Second, please speak in English as much as you can.",
            "Making mistakes is part of learning.",
            "Third, bring your notebook, a pen, and an English dictionary.",
            "Let's open our books to page five."
        ]
    },
    {
        "id_code": "a1_04_organising_a_group_project",
        "day_number": 4,
        "level": "A1",
        "title": "Organising a Group Project",
        "topic": "Student Collaboration & Task Division",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a1-listening/organising-group-project",
        "audio_filename": "a1_organising_a_group_project.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Hi Lucas, we need to organise our project for Friday."),
            ("en-GB-RyanNeural", "Yes, Clara. We have ten minutes for the presentation."),
            ("en-GB-SoniaNeural", "Exactly. Let's divide the slides. Who wants to do the introduction?"),
            ("en-GB-RyanNeural", "I can do the introduction and explain the background."),
            ("en-GB-SoniaNeural", "Perfect. Then I will present the data and research results."),
            ("en-GB-RyanNeural", "Good idea. What about the conclusion and questions?"),
            ("en-GB-SoniaNeural", "We can both answer the questions from the audience at the end."),
            ("en-GB-RyanNeural", "Agreed. Let's meet tomorrow at two in the library to practice together."),
            ("en-GB-SoniaNeural", "Sounds like a plan. See you tomorrow.")
        ],
        "chunks": [
            "Hi Lucas, we need to organise our project for Friday.",
            "We have ten minutes for the presentation.",
            "Let's divide the slides. Who wants to do the introduction?",
            "I can do the introduction and explain the background.",
            "Then I will present the data and research results.",
            "Let's meet tomorrow at two in the library to practice together."
        ]
    },
    {
        "id_code": "a1_05_a_voicemail_message",
        "day_number": 5,
        "level": "A1",
        "title": "A Voicemail Message",
        "topic": "Office Voicemail, Order Confirmation & Callback",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a1-listening/voicemail-message",
        "audio_filename": "a1_a_voicemail_message.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Hello, this is a message for Mr. Javier Flores."),
            ("en-GB-SoniaNeural", "My name is Sarah Jenkins from Metro Logistics."),
            ("en-GB-SoniaNeural", "I am calling regarding your delivery order number 4082."),
            ("en-GB-SoniaNeural", "We need to confirm your delivery address before shipping the package tomorrow morning."),
            ("en-GB-SoniaNeural", "Please call us back at 555-0144 when you get this message."),
            ("en-GB-SoniaNeural", "Our office is open today until six in the evening."),
            ("en-GB-SoniaNeural", "If you call after six, you can leave another message with your confirmation."),
            ("en-GB-SoniaNeural", "Thank you, and have a pleasant day.")
        ],
        "chunks": [
            "Hello, this is a message for Mr. Javier Flores.",
            "My name is Sarah Jenkins from Metro Logistics.",
            "I am calling regarding your delivery order number 4082.",
            "We need to confirm your delivery address before shipping the package.",
            "Please call us back at 555-0144 when you get this message.",
            "Our office is open today until six in the evening."
        ]
    },
    {
        "id_code": "a1_06_finding_the_library",
        "day_number": 6,
        "level": "A1",
        "title": "Finding the Library",
        "topic": "Campus Directions & University Facilities",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a1-listening/finding-library",
        "audio_filename": "a1_finding_the_library.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Excuse me, could you tell me where the university library is?"),
            ("en-GB-SoniaNeural", "Yes, of course. Go straight past the science building and turn left at the cafeteria."),
            ("en-GB-RyanNeural", "Past the science building and left at the cafeteria, got it."),
            ("en-GB-SoniaNeural", "Then walk through the small garden. The library is the large glass building right in front of you."),
            ("en-GB-RyanNeural", "Is it open today?"),
            ("en-GB-SoniaNeural", "Yes, it is open until eight o'clock in the evening."),
            ("en-GB-RyanNeural", "Thank you very much for your help!"),
            ("en-GB-SoniaNeural", "You're welcome. Have a nice day!")
        ],
        "chunks": [
            "Excuse me, could you tell me where the university library is?",
            "Go straight past the science building and turn left at the cafeteria.",
            "Walk through the small garden. The library is the large glass building.",
            "It is open until eight o'clock in the evening."
        ]
    },
    {
        "id_code": "a1_07_first_day_at_school",
        "day_number": 7,
        "level": "A1",
        "title": "First Day at School",
        "topic": "Introductions, Timetable & Lockers",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a1-listening/first-day-school",
        "audio_filename": "a1_first_day_at_school.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Hello, are you new here too?"),
            ("en-GB-RyanNeural", "Yes, it's my first day. My name is Alex."),
            ("en-GB-SoniaNeural", "Nice to meet you, Alex. I'm Mia. Do you have your timetable yet?"),
            ("en-GB-RyanNeural", "Yes, here it is. Our first class is history in room 12."),
            ("en-GB-SoniaNeural", "Room 12 is on the second floor. Have you found your locker?"),
            ("en-GB-RyanNeural", "Not yet. My locker number is 45."),
            ("en-GB-SoniaNeural", "It's right next to mine in the main hall. Come on, I'll show you."),
            ("en-GB-RyanNeural", "Thanks so much, Mia!")
        ],
        "chunks": [
            "Yes, it's my first day. My name is Alex.",
            "Nice to meet you, Alex. I'm Mia.",
            "Our first class is history in room 12.",
            "Room 12 is on the second floor.",
            "It's right next to mine in the main hall. I'll show you."
        ]
    },
    {
        "id_code": "a1_08_getting_organised",
        "day_number": 8,
        "level": "A1",
        "title": "Getting Organised",
        "topic": "Study Routines, Planners & Weekly Goals",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a1-listening/getting-organised",
        "audio_filename": "a1_getting_organised.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Emma, how do you manage to do all your homework on time?"),
            ("en-GB-SoniaNeural", "I use a digital calendar on my phone. Every Sunday evening, I write down all my deadlines for the week."),
            ("en-GB-RyanNeural", "That sounds simple. What do you do if you have a big exam?"),
            ("en-GB-SoniaNeural", "I break my revision into small twenty-minute sessions each day."),
            ("en-GB-RyanNeural", "Twenty minutes a day? That's really smart."),
            ("en-GB-SoniaNeural", "Yes, it prevents stress and helps you remember things better.")
        ],
        "chunks": [
            "How do you manage to do all your homework on time?",
            "I use a digital calendar on my phone.",
            "Every Sunday evening, I write down all my deadlines for the week.",
            "I break my revision into small twenty-minute sessions each day.",
            "It prevents stress and helps you remember things better."
        ]
    },
    {
        "id_code": "a1_09_important_people",
        "day_number": 9,
        "level": "A1",
        "title": "Important People in My Life",
        "topic": "Family, Mentors & Role Models",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a1-listening/important-people",
        "audio_filename": "a1_important_people.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Today I want to talk about three people who inspire me."),
            ("en-GB-SoniaNeural", "First is my grandmother. She was a nurse for forty years and always taught me to be kind."),
            ("en-GB-SoniaNeural", "Second is my older brother, David. He works in engineering and taught me never to give up when things are difficult."),
            ("en-GB-SoniaNeural", "And third is my high school English teacher, Mr. Clark, who encouraged me to read books every single day."),
            ("en-GB-SoniaNeural", "Who are the most important people in your life?")
        ],
        "chunks": [
            "Today I want to talk about three people who inspire me.",
            "First is my grandmother. She was a nurse for forty years.",
            "Second is my older brother. He taught me never to give up.",
            "Third is my English teacher, who encouraged me to read books every day."
        ]
    },
    {
        "id_code": "a1_10_meeting_people_at_a_dinner",
        "day_number": 10,
        "level": "A1",
        "title": "Meeting People at a Dinner Party",
        "topic": "Social Greetings, Occupations & Small Talk",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a1-listening/meeting-people-dinner",
        "audio_filename": "a1_meeting_people_at_a_dinner.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Good evening. Mind if I sit here?"),
            ("en-GB-SoniaNeural", "Not at all, please go ahead. I'm Sophie."),
            ("en-GB-RyanNeural", "Nice to meet you, Sophie. I'm Carlos. Are you a friend of Mark?"),
            ("en-GB-SoniaNeural", "Yes, we work together at the architecture firm. And what about you?"),
            ("en-GB-RyanNeural", "We went to university together ten years ago. I work in software development now."),
            ("en-GB-SoniaNeural", "That's fascinating! Do you live here in London?"),
            ("en-GB-RyanNeural", "Yes, I moved here three years ago.")
        ],
        "chunks": [
            "Good evening. Mind if I sit here?",
            "Nice to meet you, Sophie. I'm Carlos.",
            "We work together at the architecture firm.",
            "We went to university together ten years ago.",
            "I moved here three years ago."
        ]
    },
    {
        "id_code": "a1_11_missing_a_class",
        "day_number": 11,
        "level": "A1",
        "title": "Missing a Class",
        "topic": "Absence Notification, Notes & Homework Catch-Up",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a1-listening/missing-class",
        "audio_filename": "a1_missing_a_class.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Hi Sarah, were you in biology class yesterday morning?"),
            ("en-GB-SoniaNeural", "Yes, I was. Where were you?"),
            ("en-GB-RyanNeural", "I had a dentist appointment and couldn't attend. Did the teacher assign any homework?"),
            ("en-GB-SoniaNeural", "Yes, we have to read chapter four and complete questions one to six on page thirty."),
            ("en-GB-RyanNeural", "Can I borrow your class notes to copy them?"),
            ("en-GB-SoniaNeural", "Sure! I took photos of them on my phone, so I can send them to you right now."),
            ("en-GB-RyanNeural", "That's wonderful, thank you so much!")
        ],
        "chunks": [
            "Were you in biology class yesterday morning?",
            "I had a dentist appointment and couldn't attend.",
            "We have to read chapter four and complete questions one to six.",
            "I took photos of my notes, so I can send them to you right now."
        ]
    },
    {
        "id_code": "a1_12_understanding_an_announcement",
        "day_number": 12,
        "level": "A1",
        "title": "Understanding a Station Announcement",
        "topic": "Public Transit, Train Platforms & Delays",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a1-listening/understanding-announcement",
        "audio_filename": "a1_understanding_an_announcement.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Attention all passengers. This is an announcement for the 10:15 train to Manchester Piccadilly."),
            ("en-GB-SoniaNeural", "The train is now departing from platform four instead of platform two."),
            ("en-GB-SoniaNeural", "Please cross the bridge to platform four immediately."),
            ("en-GB-SoniaNeural", "Due to earlier track maintenance, the train will arrive ten minutes late at Manchester."),
            ("en-GB-SoniaNeural", "We apologise for any inconvenience caused. Thank you for travelling with Northern Rail.")
        ],
        "chunks": [
            "Attention all passengers for the 10:15 train to Manchester.",
            "The train is now departing from platform four instead of platform two.",
            "Please cross the bridge to platform four immediately.",
            "The train will arrive ten minutes late at Manchester."
        ]
    },

    # ==========================================
    # LEVEL A2 (12 LESSONS)
    # ==========================================
    {
        "id_code": "a2_01_morning_briefing",
        "day_number": 13,
        "level": "A2",
        "title": "A Morning Briefing at Work",
        "topic": "Operations Kickoff, Priorities & Safety Standards",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a2-listening/morning-briefing",
        "audio_filename": "a2_morning_briefing.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Morning team. Let's do a quick five-minute briefing before we kick off today's shift."),
            ("en-GB-RyanNeural", "We have three main operational priorities today."),
            ("en-GB-RyanNeural", "First, container shipment forty-two arrived early at the loading dock, so we need two teams to inspect and unload by eleven o'clock."),
            ("en-GB-RyanNeural", "Second, the safety audit is scheduled for two this afternoon. Please double-check that all emergency exits are clear and personal protective equipment is worn at all times."),
            ("en-GB-RyanNeural", "Lastly, if anyone notices any delay in the inventory software, report it immediately to technical support so we avoid shipping bottlenecks."),
            ("en-GB-RyanNeural", "Any questions? Alright, let's have a productive and safe day.")
        ],
        "chunks": [
            "Morning team. Let's do a quick five-minute briefing before we kick off today's shift.",
            "We have three main operational priorities today.",
            "Container shipment forty-two arrived early at the loading dock.",
            "The safety audit is scheduled for two this afternoon.",
            "Please double-check that all emergency exits are clear.",
            "Report any delay immediately to technical support so we avoid shipping bottlenecks."
        ]
    },
    {
        "id_code": "a2_02_free_time_sports_centre",
        "day_number": 14,
        "level": "A2",
        "title": "Free Time & Sports Centre Activities",
        "topic": "Calling Reception, Membership, Schedule & Fees",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a2-listening/free-time",
        "audio_filename": "a2_free_time_sports_centre.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Hello, Riverside Leisure Centre. How can I help you today?"),
            ("en-GB-RyanNeural", "Hi, I'm calling to find out about your adult swimming classes and gym facilities."),
            ("en-GB-SoniaNeural", "Certainly. Our heated swimming pool is open from six in the morning until nine at night. We have lane swimming every weekday morning, and beginner technique classes on Tuesdays and Thursdays at seven in the evening."),
            ("en-GB-RyanNeural", "That sounds ideal. How much does a monthly pass cost?"),
            ("en-GB-SoniaNeural", "A standard monthly pass including pool and gym access is forty-five pounds. If you join as a pair with a friend, we currently offer a ten percent discount for both members."),
            ("en-GB-RyanNeural", "That is great value. Can I register online or do I need to visit in person?"),
            ("en-GB-SoniaNeural", "You can easily register directly on our website, or drop by with your ID card anytime this afternoon."),
            ("en-GB-RyanNeural", "Excellent, thank you for your help.")
        ],
        "chunks": [
            "Hello, Riverside Leisure Centre. How can I help you today?",
            "I'm calling to find out about your adult swimming classes and gym facilities.",
            "Our heated swimming pool is open from six in the morning until nine at night.",
            "We have lane swimming every weekday morning, and beginner classes on Tuesdays.",
            "If you join as a pair with a friend, we offer a ten percent discount.",
            "You can easily register directly on our website."
        ]
    },
    {
        "id_code": "a2_03_changing_meeting_plans",
        "day_number": 15,
        "level": "A2",
        "title": "Changing Meeting Plans",
        "topic": "Phone Coordination, Transport Delay & Rescheduling",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a2-listening/changing-plans",
        "audio_filename": "a2_changing_meeting_plans.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Hello, Amanda speaking."),
            ("en-GB-RyanNeural", "Hi Amanda, it's Daniel. I'm afraid I have a bit of a problem regarding our meeting this afternoon."),
            ("en-GB-SoniaNeural", "Oh, is everything alright?"),
            ("en-GB-RyanNeural", "Yes, but my train has been delayed by almost an hour due to signal problems outside the city. I won't be able to make it to your office by two o'clock."),
            ("en-GB-SoniaNeural", "Don't worry at all. Would you prefer to push it back to four o'clock, or would tomorrow morning work better for you?"),
            ("en-GB-RyanNeural", "Four o'clock today would be fantastic if your schedule allows it. I should definitely arrive by three thirty."),
            ("en-GB-SoniaNeural", "Four o'clock is completely fine. I'll update the calendar invitation right away and send you the new link."),
            ("en-GB-RyanNeural", "Thanks so much for your understanding, Amanda. See you at four.")
        ],
        "chunks": [
            "I'm afraid I have a bit of a problem regarding our meeting this afternoon.",
            "My train has been delayed by almost an hour due to signal problems.",
            "I won't be able to make it to your office by two o'clock.",
            "Would you prefer to push it back to four o'clock, or would tomorrow work better?",
            "Four o'clock today would be fantastic if your schedule allows it.",
            "I'll update the calendar invitation right away and send you the new link."
        ]
    },
    {
        "id_code": "a2_04_facts_and_figures",
        "day_number": 16,
        "level": "A2",
        "title": "Facts & Figures: Quarterly Report",
        "topic": "Data Presentation, Growth Metrics & Consistency",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a2-listening/facts-and-figures",
        "audio_filename": "a2_facts_and_figures.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Good morning, ladies and gentlemen. Today I would like to present the key performance metrics of our learning program over the past quarter."),
            ("en-GB-SoniaNeural", "As you can see on the screen, active daily participation increased by thirty-four percent compared to last year."),
            ("en-GB-SoniaNeural", "More importantly, eighty-two percent of our participants completed their daily targets of fifteen minutes of reading and five minutes of speaking without breaking their streaks."),
            ("en-GB-SoniaNeural", "We also observed a forty percent reduction in comprehension errors during weekly check-ins."),
            ("en-GB-SoniaNeural", "In conclusion, consistent daily practice in pairs has proven to be twice as effective as occasional long study sessions. Thank you for your attention, and now I'd be glad to take any questions.")
        ],
        "chunks": [
            "Today I would like to present the key performance metrics of our learning program.",
            "Active daily participation increased by thirty-four percent compared to last year.",
            "Eighty-two percent of participants completed their daily targets without breaking their streaks.",
            "We also observed a forty percent reduction in comprehension errors.",
            "Consistent daily practice in pairs has proven to be twice as effective."
        ]
    },
    {
        "id_code": "a2_05_giving_directions_in_town",
        "day_number": 17,
        "level": "A2",
        "title": "Giving Directions in Town",
        "topic": "Street Navigation, Landmarks & Finding Central Station",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a2-listening/giving-directions",
        "audio_filename": "a2_giving_directions_in_town.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Excuse me, could you help me? I'm trying to find the central train station, but I think I am turned around."),
            ("en-GB-SoniaNeural", "No problem at all, it's quite close. Go straight along this avenue for two blocks until you see the cathedral on your left."),
            ("en-GB-RyanNeural", "Straight ahead past the cathedral, okay."),
            ("en-GB-SoniaNeural", "Exactly. At the traffic lights right after the cathedral, turn right onto Victoria Street. Keep walking for about three minutes, pass the public library, and you'll see the main entrance of the station right across the square."),
            ("en-GB-RyanNeural", "Turn right after the cathedral, pass the library, and it's on the square. How long does the walk take?"),
            ("en-GB-SoniaNeural", "It's only about an eight-minute walk from here."),
            ("en-GB-RyanNeural", "Wonderful. Thank you so much for your help!"),
            ("en-GB-SoniaNeural", "You're welcome! Have a safe journey.")
        ],
        "chunks": [
            "I'm trying to find the central train station, but I think I am turned around.",
            "Go straight along this avenue for two blocks until you see the cathedral.",
            "At the traffic lights right after the cathedral, turn right onto Victoria Street.",
            "Keep walking for about three minutes, pass the public library.",
            "You'll see the main entrance of the station right across the square.",
            "It's only about an eight-minute walk from here."
        ]
    },
    {
        "id_code": "a2_06_changing_a_meeting_time",
        "day_number": 18,
        "level": "A2",
        "title": "Changing a Meeting Time",
        "topic": "Calendar Sync, Scheduling & Time Confirmation",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a2-listening/changing-meeting-time",
        "audio_filename": "a2_changing_a_meeting_time.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Hi Sarah, do you have a second? I need to ask you about our project review on Thursday."),
            ("en-GB-SoniaNeural", "Sure, what's up? It's currently booked for ten in the morning, right?"),
            ("en-GB-RyanNeural", "Yes, but our client from Bristol asked for a video call at that exact time. Would it be possible to move our meeting to two thirty in the afternoon?"),
            ("en-GB-SoniaNeural", "Let me check my calendar. At two thirty I have a quick team sync, but three o'clock is completely free."),
            ("en-GB-RyanNeural", "Three o'clock sounds perfect. That gives me plenty of time after the client call."),
            ("en-GB-SoniaNeural", "Great, I'll update the calendar invite to three o'clock on Thursday.")
        ],
        "chunks": [
            "I need to ask you about our project review on Thursday.",
            "Would it be possible to move our meeting to two thirty?",
            "Three o'clock is completely free.",
            "I'll update the calendar invite to three o'clock on Thursday."
        ]
    },
    {
        "id_code": "a2_07_going_to_the_cinema",
        "day_number": 19,
        "level": "A2",
        "title": "Going to the Cinema",
        "topic": "Movie Genres, Showtimes & Ticket Purchases",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a2-listening/going-cinema",
        "audio_filename": "a2_going_to_the_cinema.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Hi Jack, are you free this evening? A few of us are planning to go to the cinema."),
            ("en-GB-RyanNeural", "That sounds fun! What film are you going to see?"),
            ("en-GB-SoniaNeural", "We are choosing between the new science-fiction thriller and the comedy film."),
            ("en-GB-RyanNeural", "I definitely prefer the science-fiction one. What time does it start?"),
            ("en-GB-SoniaNeural", "There is a screening at seven fifteen and another at nine thirty."),
            ("en-GB-RyanNeural", "Seven fifteen is great. Should I buy my ticket online in advance?"),
            ("en-GB-SoniaNeural", "Yes, it's safer because the theatre usually gets very busy on Friday nights.")
        ],
        "chunks": [
            "A few of us are planning to go to the cinema.",
            "We are choosing between the science-fiction thriller and the comedy.",
            "There is a screening at seven fifteen and another at nine thirty.",
            "It's safer to buy tickets online because the theatre gets busy."
        ]
    },
    {
        "id_code": "a2_08_leaving_a_message",
        "day_number": 20,
        "level": "A2",
        "title": "Leaving a Message",
        "topic": "Receptionist Inquiries, Callbacks & Urgent Notes",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a2-listening/leaving-message",
        "audio_filename": "a2_leaving_a_message.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Good morning, Sterling Consulting. How can I help you?"),
            ("en-GB-RyanNeural", "Hello, may I please speak to Mr. Richard Bennett?"),
            ("en-GB-SoniaNeural", "I'm sorry, Mr. Bennett is currently in a conference call and unavailable. Would you like to leave a message?"),
            ("en-GB-RyanNeural", "Yes, please. This is Thomas Evans from Apex Technologies. Could you ask him to call me back regarding the revised budget proposal?"),
            ("en-GB-SoniaNeural", "Certainly, Mr. Evans. Can I confirm your telephone number?"),
            ("en-GB-RyanNeural", "Yes, it is 020 7946 0198."),
            ("en-GB-SoniaNeural", "Thank you, Mr. Evans. I will make sure he receives this message as soon as he leaves his meeting.")
        ],
        "chunks": [
            "May I please speak to Mr. Richard Bennett?",
            "Mr. Bennett is currently in a conference call. Would you like to leave a message?",
            "Could you ask him to call me back regarding the revised budget proposal?",
            "I will make sure he receives this message as soon as he leaves his meeting."
        ]
    },
    {
        "id_code": "a2_09_making_an_appointment",
        "day_number": 21,
        "level": "A2",
        "title": "Making a Medical Appointment",
        "topic": "Healthcare Clinic, Symptoms & Doctor Availability",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a2-listening/making-appointment",
        "audio_filename": "a2_making_an_appointment.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Oakfield Health Practice, good afternoon."),
            ("en-GB-RyanNeural", "Hello, I would like to make an appointment to see a doctor this week, please."),
            ("en-GB-SoniaNeural", "Of course. Are you currently registered as a patient with our surgery?"),
            ("en-GB-RyanNeural", "Yes, I am. My name is Oliver Reed."),
            ("en-GB-SoniaNeural", "Thank you, Oliver. What seems to be the trouble?"),
            ("en-GB-RyanNeural", "I have had a bad cough and sore throat for over five days now."),
            ("en-GB-SoniaNeural", "Dr. Davies has an opening tomorrow morning at eleven fifteen. Would that suit you?"),
            ("en-GB-RyanNeural", "Yes, tomorrow at eleven fifteen is perfect. Thank you.")
        ],
        "chunks": [
            "I would like to make an appointment to see a doctor this week.",
            "Are you currently registered as a patient with our surgery?",
            "I have had a bad cough and sore throat for five days now.",
            "Dr. Davies has an opening tomorrow morning at eleven fifteen."
        ]
    },
    {
        "id_code": "a2_10_missing_a_flight",
        "day_number": 22,
        "level": "A2",
        "title": "Missing a Flight at the Airport",
        "topic": "Airline Counter, Boarding Gate & Rebooking",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a2-listening/missing-flight",
        "audio_filename": "a2_missing_a_flight.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Excuse me, I was supposed to be on flight BA 304 to Amsterdam, but my connecting train was delayed. Is the gate still open?"),
            ("en-GB-SoniaNeural", "I am very sorry, sir, but that flight closed its doors fifteen minutes ago and is currently preparing for take-off."),
            ("en-GB-RyanNeural", "Oh no, what should I do? I have an essential business meeting tomorrow morning."),
            ("en-GB-SoniaNeural", "Don't panic. There is another scheduled flight to Amsterdam this evening at eight forty-five. There are still three economy seats available."),
            ("en-GB-RyanNeural", "Can you please transfer my ticket to that flight?"),
            ("en-GB-SoniaNeural", "Yes, I can arrange that for you right now at the customer service desk.")
        ],
        "chunks": [
            "I was supposed to be on flight BA 304 to Amsterdam, but my train was delayed.",
            "That flight closed its doors fifteen minutes ago.",
            "There is another scheduled flight to Amsterdam this evening at eight forty-five.",
            "I can arrange that for you right now at the customer service desk."
        ]
    },
    {
        "id_code": "a2_11_shopping_for_clothes",
        "day_number": 23,
        "level": "A2",
        "title": "Shopping for Clothes",
        "topic": "Fitting Room, Sizing, Colors & Returns Policy",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a2-listening/shopping-clothes",
        "audio_filename": "a2_shopping_for_clothes.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Excuse me, do you have this wool jumper in a medium?"),
            ("en-GB-SoniaNeural", "Let me check our stock room. Yes, here is one in medium, and we also have it in dark navy and grey."),
            ("en-GB-RyanNeural", "I like the navy one. Where are the changing rooms?"),
            ("en-GB-SoniaNeural", "They are just around the corner on your left."),
            ("en-GB-RyanNeural", "Thank you... The fit is very good. What is your returns policy if I change my mind?"),
            ("en-GB-SoniaNeural", "You have thirty days to return or exchange it as long as you keep the receipt and original tags.")
        ],
        "chunks": [
            "Do you have this wool jumper in a medium?",
            "Here is one in medium, and we also have it in dark navy and grey.",
            "Where are the changing rooms?",
            "You have thirty days to return or exchange it with the receipt."
        ]
    },
    {
        "id_code": "a2_12_talking_about_an_interview",
        "day_number": 24,
        "level": "A2",
        "title": "Talking About a Job Interview",
        "topic": "Job Application, Interview Feedback & Next Steps",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/a2-listening/talking-about-interview",
        "audio_filename": "a2_talking_about_an_interview.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Hi Dan! How did your job interview go this morning?"),
            ("en-GB-RyanNeural", "I think it went quite well overall. The interview panel was very welcoming and polite."),
            ("en-GB-SoniaNeural", "What kind of questions did they ask you?"),
            ("en-GB-RyanNeural", "They asked about my past experience in logistics coordination, how I handle tight deadlines, and why I want to work for their company."),
            ("en-GB-SoniaNeural", "Did you feel comfortable answering?"),
            ("en-GB-RyanNeural", "Yes, practicing my answers beforehand helped immensely. They said they will inform me of their decision by Friday afternoon."),
            ("en-GB-SoniaNeural", "Fingers crossed! I'm sure you will get positive news.")
        ],
        "chunks": [
            "How did your job interview go this morning?",
            "The interview panel was very welcoming and polite.",
            "They asked about my past experience and how I handle tight deadlines.",
            "Practicing my answers beforehand helped immensely.",
            "They said they will inform me of their decision by Friday afternoon."
        ]
    },

    # ==========================================
    # LEVEL B1 (12 LESSONS)
    # ==========================================
    {
        "id_code": "b1_01_a_job_interview",
        "day_number": 25,
        "level": "B1",
        "title": "A Professional Job Interview",
        "topic": "Career Background, Problem-Solving & Strengths",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b1-listening/a-job-interview",
        "audio_filename": "b1_a_job_interview.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Welcome, Mr. Henderson. To start off, could you walk us through your background in operations?"),
            ("en-GB-RyanNeural", "Certainly. For the past four years, I have served as an assistant operations manager, overseeing inventory pipelines and ensuring timely distribution."),
            ("en-GB-SoniaNeural", "Could you describe a challenging situation you encountered and how you resolved it?"),
            ("en-GB-RyanNeural", "During peak season last winter, a core transport partner experienced a regional strike. I quickly negotiated emergency terms with two secondary suppliers, which avoided shipment delays and safeguarded our delivery commitments."),
            ("en-GB-SoniaNeural", "That demonstrates commendable adaptability and crisis management under pressure.")
        ],
        "chunks": [
            "Could you walk us through your background in operations?",
            "For the past four years, I have served as an assistant operations manager.",
            "I quickly negotiated emergency terms with two secondary suppliers.",
            "That demonstrates commendable adaptability and crisis management."
        ]
    },
    {
        "id_code": "b1_02_a_phone_call_from_a_customer",
        "day_number": 26,
        "level": "B1",
        "title": "A Phone Call from an Unhappy Customer",
        "topic": "Customer Service, Complaint Handling & Resolution",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b1-listening/a-phone-call-customer",
        "audio_filename": "b1_a_phone_call_from_a_customer.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Customer Support, this is Helen speaking. How may I assist you today?"),
            ("en-GB-RyanNeural", "Yes, I am calling because my company placed a bulk order for industrial printers two weeks ago, and nothing has arrived yet."),
            ("en-GB-SoniaNeural", "I completely understand your frustration, sir. May I take your order reference number so I can investigate the shipment status immediately?"),
            ("en-GB-RyanNeural", "The reference is PR-88210. Our office operations are severely disrupted by this delay."),
            ("en-GB-SoniaNeural", "I see the issue here. The shipment was routed through customs for routine inspection. I will escalate this with the freight carrier right now and personally monitor the delivery until it reaches your warehouse tomorrow morning.")
        ],
        "chunks": [
            "My company placed a bulk order two weeks ago, and nothing has arrived yet.",
            "May I take your order reference number so I can investigate immediately?",
            "The shipment was routed through customs for routine inspection.",
            "I will escalate this with the freight carrier and personally monitor the delivery."
        ]
    },
    {
        "id_code": "b1_03_a_student_discussion",
        "day_number": 27,
        "level": "B1",
        "title": "A University Student Discussion",
        "topic": "Academic Research, Methodology & Critical Thinking",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b1-listening/a-student-discussion",
        "audio_filename": "b1_a_student_discussion.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "What do you think of Professor Davies' thesis on automated supply chains?"),
            ("en-GB-SoniaNeural", "His quantitative findings are compelling, but I believe he underestimates the necessity of human supervision in unpredictable environments."),
            ("en-GB-RyanNeural", "That aligns with my perspective. While predictive algorithms enhance efficiency, unforeseen disruptions still require immediate human intuition and strategic intervention."),
            ("en-GB-SoniaNeural", "Precisely. Let's incorporate that comparative analysis into the second chapter of our joint paper.")
        ],
        "chunks": [
            "What do you think of the thesis on automated supply chains?",
            "His quantitative findings are compelling, but underestimate human supervision.",
            "Unforeseen disruptions still require immediate human intuition.",
            "Let's incorporate that comparative analysis into our joint paper."
        ]
    },
    {
        "id_code": "b1_04_a_weather_forecast",
        "day_number": 28,
        "level": "B1",
        "title": "A Regional Weather Forecast",
        "topic": "Meteorological Report, Fronts & Travel Warnings",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b1-listening/a-weather-forecast",
        "audio_filename": "b1_a_weather_forecast.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Good afternoon. Here is the regional forecast for the British Isles over the coming weekend."),
            ("en-GB-SoniaNeural", "An Atlantic low-pressure system is sweeping across northern Scotland, bringing heavy rain and gale-force coastal gusts reaching fifty miles per hour."),
            ("en-GB-SoniaNeural", "Meanwhile, central and southern England will enjoy sunny spells on Saturday with temperatures hovering around eighteen degrees Celsius, before scattered showers move inland on Sunday afternoon."),
            ("en-GB-SoniaNeural", "Motorists are advised to exercise caution along northern motorways due to reduced visibility.")
        ],
        "chunks": [
            "Here is the regional forecast for the British Isles over the weekend.",
            "An Atlantic low-pressure system is bringing heavy rain and gale-force gusts.",
            "Southern England will enjoy sunny spells with mild temperatures.",
            "Motorists are advised to exercise caution due to reduced visibility."
        ]
    },
    {
        "id_code": "b1_05_interview_about_listening_skills",
        "day_number": 29,
        "level": "B1",
        "title": "An Interview About Effective Listening",
        "topic": "Active Listening, Paraphrasing & Communication",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b1-listening/an-interview-about-listening-skills",
        "audio_filename": "b1_interview_about_listening_skills.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Welcome back. Today we are speaking with Dr. Karen Wright about how active listening transforms workplace collaboration."),
            ("en-GB-SoniaNeural", "Thank you, Mark. Most people believe hearing words is sufficient, but true active listening requires giving undivided attention and reflecting back what the speaker intended."),
            ("en-GB-RyanNeural", "What practical technique can professionals implement right away?"),
            ("en-GB-SoniaNeural", "Paraphrasing. Before offering your solution, summarize: 'What I am hearing is that our main constraint is time, is that accurate?' This eliminates costly misunderstandings.")
        ],
        "chunks": [
            "Active listening transforms workplace collaboration.",
            "Most people believe hearing words is sufficient, but active listening requires undivided attention.",
            "Paraphrasing eliminates costly misunderstandings.",
            "Summarize the speaker's main constraint before offering your solution."
        ]
    },
    {
        "id_code": "b1_06_arriving_late_to_class",
        "day_number": 30,
        "level": "B1",
        "title": "Arriving Late to a Seminar",
        "topic": "Etiquette, Accountability & Seminar Discussion",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b1-listening/arriving-late-class",
        "audio_filename": "b1_arriving_late_to_class.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Professor Miller, I sincerely apologize for entering twenty minutes late."),
            ("en-GB-SoniaNeural", "Take a seat quietly, please. We were examining case studies on cross-cultural negotiations."),
            ("en-GB-RyanNeural", "Thank you. The underground suffered a power outage near Holborn station."),
            ("en-GB-SoniaNeural", "Understood. Please borrow the lecture handouts from James and be prepared to participate in the group breakout discussion in ten minutes.")
        ],
        "chunks": [
            "I sincerely apologize for entering twenty minutes late.",
            "We were examining case studies on cross-cultural negotiations.",
            "The underground suffered a power outage near Holborn station.",
            "Be prepared to participate in the group breakout discussion."
        ]
    },
    {
        "id_code": "b1_07_chatting_about_a_series",
        "day_number": 31,
        "level": "B1",
        "title": "Chatting About a Television Series",
        "topic": "Story Arc, Character Arcs & Cinematography",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b1-listening/chatting-about-series",
        "audio_filename": "b1_chatting_about_a_series.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Have you caught up with the finale of that mystery series we were discussing?"),
            ("en-GB-RyanNeural", "I watched it last night! The plot twist in the penultimate episode completely altered my interpretation of the main protagonist."),
            ("en-GB-SoniaNeural", "I found the character development remarkably well-paced. Rather than relying on cheap suspense, the writers planted subtle psychological clues from the beginning."),
            ("en-GB-RyanNeural", "And the soundtrack elevated the tension significantly. Highly recommended.")
        ],
        "chunks": [
            "The plot twist in the penultimate episode completely altered my interpretation.",
            "I found the character development remarkably well-paced.",
            "The writers planted subtle psychological clues from the beginning.",
            "The soundtrack elevated the tension significantly."
        ]
    },
    {
        "id_code": "b1_08_difficult_situations_at_work",
        "day_number": 32,
        "level": "B1",
        "title": "Difficult Situations at Work",
        "topic": "Conflict Resolution, Constructive Feedback & Compromise",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b1-listening/difficult-situations-work",
        "audio_filename": "b1_difficult_situations_at_work.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Elena, I wanted to discuss the disagreement during yesterday's budget meeting."),
            ("en-GB-SoniaNeural", "I appreciate you bringing it up, David. We both felt strongly about resource allocation."),
            ("en-GB-RyanNeural", "I recognize that my tone became overly defensive when deadlines were questioned. My intention was solely to protect our developers from burnout."),
            ("en-GB-SoniaNeural", "I understand your concern. Moving forward, let's schedule pre-alignment sessions so we present a unified strategy to senior leadership.")
        ],
        "chunks": [
            "I wanted to discuss the disagreement during yesterday's meeting.",
            "We both felt strongly about resource allocation.",
            "My intention was solely to protect our developers from burnout.",
            "Let's schedule pre-alignment sessions so we present a unified strategy."
        ]
    },
    {
        "id_code": "b1_09_giving_advice_to_a_friend",
        "day_number": 33,
        "level": "B1",
        "title": "Giving Advice to a Friend",
        "topic": "Career Transition, Upskilling & Work-Life Balance",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b1-listening/giving-advice-friend",
        "audio_filename": "b1_giving_advice_to_a_friend.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "I feel stuck in my current role, Maria. The work has become repetitive and lacks growth opportunities."),
            ("en-GB-SoniaNeural", "Have you thought about pursuing professional certifications or attending industry networking events?"),
            ("en-GB-RyanNeural", "I have, but finding time alongside forty hours of work each week feels daunting."),
            ("en-GB-SoniaNeural", "Try dedicating just thirty minutes every weekday morning before opening your work laptop. Micro-habits compound surprisingly quickly over six months.")
        ],
        "chunks": [
            "I feel stuck in my current role. The work lacks growth opportunities.",
            "Have you thought about pursuing professional certifications?",
            "Dedicate thirty minutes every weekday morning before work.",
            "Micro-habits compound surprisingly quickly over six months."
        ]
    },
    {
        "id_code": "b1_10_instructions_for_an_exam",
        "day_number": 34,
        "level": "B1",
        "title": "Official Exam Instructions",
        "topic": "Standardized Testing, Timers & Protocol",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b1-listening/instructions-for-an-exam",
        "audio_filename": "b1_instructions_for_an_exam.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Good morning, candidates. Please place your personal belongings in the designated lockers at the back of the examination hall."),
            ("en-GB-SoniaNeural", "Mobile phones and electronic watches must be switched completely off."),
            ("en-GB-SoniaNeural", "The examination lasts precisely two hours and fifteen minutes. Part one consists of reading comprehension, followed by written analysis."),
            ("en-GB-SoniaNeural", "You may not leave your desk during the initial forty-five minutes or final fifteen minutes. You may now turn over your papers.")
        ],
        "chunks": [
            "Please place your personal belongings in the designated lockers.",
            "Mobile phones and electronic watches must be switched off.",
            "The examination lasts precisely two hours and fifteen minutes.",
            "You may now turn over your papers."
        ]
    },
    {
        "id_code": "b1_11_meeting_new_people",
        "day_number": 35,
        "level": "B1",
        "title": "Meeting New People at a Conference",
        "topic": "Networking Pitch, Business Cards & Common Ground",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b1-listening/meeting-new-people",
        "audio_filename": "b1_meeting_new_people.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Hello, did you attend the keynote speech on sustainable energy earlier?"),
            ("en-GB-SoniaNeural", "Yes, I did! I was particularly intrigued by their statistical projections regarding offshore wind infrastructure."),
            ("en-GB-RyanNeural", "Same here. I'm Marcus, by the way. I head green procurement for an industrial manufacturer in Leeds."),
            ("en-GB-SoniaNeural", "Pleasure to meet you, Marcus. I'm Rachel, an environmental policy researcher at Edinburgh University. Here is my card—we should explore potential research synergies.")
        ],
        "chunks": [
            "Did you attend the keynote speech on sustainable energy?",
            "I was intrigued by their projections regarding offshore wind infrastructure.",
            "I head green procurement for an industrial manufacturer.",
            "Here is my card—we should explore potential research synergies."
        ]
    },
    {
        "id_code": "b1_12_renting_a_house",
        "day_number": 36,
        "level": "B1",
        "title": "Renting a House: Lease Inquiries",
        "topic": "Tenancy Agreement, Deposit & Maintenance Clauses",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b1-listening/renting-a-house",
        "audio_filename": "b1_renting_a_house.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Good afternoon. I am inquiring about the two-bedroom property listed on Kensington Avenue."),
            ("en-GB-SoniaNeural", "Yes, that apartment is currently available for occupancy starting next month. The monthly rent is twelve hundred pounds, excluding council tax and utilities."),
            ("en-GB-RyanNeural", "What is required regarding security deposits and reference checks?"),
            ("en-GB-SoniaNeural", "A deposit equivalent to five weeks' rent is standard, held in a government-backed tenancy deposit scheme, alongside proof of steady employment.")
        ],
        "chunks": [
            "I am inquiring about the two-bedroom property on Kensington Avenue.",
            "The monthly rent is twelve hundred pounds, excluding council tax.",
            "What is required regarding security deposits and reference checks?",
            "A deposit equivalent to five weeks' rent is standard."
        ]
    },

    # ==========================================
    # LEVEL B2 (12 LESSONS)
    # ==========================================
    {
        "id_code": "b2_01_a_business_interview",
        "day_number": 37,
        "level": "B2",
        "title": "A Corporate Strategy Interview",
        "topic": "Market Disruption, Agile Management & Capital",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b2-listening/a-business-interview",
        "audio_filename": "b2_a_business_interview.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Today on Business Insight, we are joined by venture capitalist Eleanor Vance to analyze the shifting landscape of enterprise tech."),
            ("en-GB-SoniaNeural", "Thank you, Arthur. What we are witnessing is an aggressive pivot from bloated software suites toward lean, highly specialized vertical solutions."),
            ("en-GB-RyanNeural", "Many legacy corporations struggle to adapt to such rapid iteration cycles."),
            ("en-GB-SoniaNeural", "Indeed. Organizations that fail to decentralize decision-making inevitably become vulnerable to agile startups operating with fractional overheads.")
        ],
        "chunks": [
            "We are joined by venture capitalist Eleanor Vance to analyze enterprise tech.",
            "We are witnessing an aggressive pivot toward lean vertical solutions.",
            "Legacy corporations struggle to adapt to rapid iteration cycles.",
            "Firms that fail to decentralize become vulnerable to agile startups."
        ]
    },
    {
        "id_code": "b2_02_a_digital_detox_podcast",
        "day_number": 38,
        "level": "B2",
        "title": "A Digital Detox Podcast",
        "topic": "Attention Economy, Cognitive Fatigue & Mindful Tech",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b2-listening/a-digital-detox-podcast",
        "audio_filename": "b2_a_digital_detox_podcast.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Welcome to Deep Focus. Today we examine what happens when knowledge workers disconnect from notifications for seven consecutive days."),
            ("en-GB-RyanNeural", "Our cognitive research demonstrates that constant smartphone vibrations induce chronic baseline anxiety and fragment short-term memory."),
            ("en-GB-SoniaNeural", "Participants who instituted tech-free evenings reported a sixty percent improvement in restorative sleep patterns and a noticeable revival of creative contemplation.")
        ],
        "chunks": [
            "We examine what happens when knowledge workers disconnect for seven days.",
            "Smartphones induce chronic baseline anxiety and fragment short-term memory.",
            "Tech-free evenings yielded a sixty percent improvement in sleep patterns."
        ]
    },
    {
        "id_code": "b2_03_a_lecture_about_public_art",
        "day_number": 39,
        "level": "B2",
        "title": "A Lecture on Public Art & Urban Spaces",
        "topic": "Civic Identity, Sculptures & Urban Regeneration",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b2-listening/a-lecture-about-public-art",
        "audio_filename": "b2_a_lecture_about_public_art.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Public art should never be viewed merely as ornamental decoration within metropolitan centers."),
            ("en-GB-SoniaNeural", "Historically, monuments and architectural installations function as contested arenas where collective memory, political ideology, and civic identity intersect."),
            ("en-GB-SoniaNeural", "When municipal planners incorporate democratic community dialogue into public art commissions, civic engagement and neighborhood pride increase dramatically.")
        ],
        "chunks": [
            "Public art should never be viewed merely as ornamental decoration.",
            "Monuments function as arenas where collective memory and civic identity intersect.",
            "Community dialogue in art commissions increases neighborhood pride dramatically."
        ]
    },
    {
        "id_code": "b2_04_a_talk_about_motivation",
        "day_number": 40,
        "level": "B2",
        "title": "A Keynote Talk on Intrinsic Motivation",
        "topic": "Behavioral Psychology, Autonomy & Mastery",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b2-listening/a-talk-about-motivation",
        "audio_filename": "b2_a_talk_about_motivation.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "The traditional model of workplace incentives—carrots and sticks—is fundamentally flawed when applied to complex cognitive work."),
            ("en-GB-RyanNeural", "Decades of psychological experiments confirm that extrinsic rewards narrow cognitive focus, extinguishing organic creativity."),
            ("en-GB-RyanNeural", "True engagement stems from three innate psychological needs: autonomy over one's craft, the pursuit of mastery, and connection to a meaningful purpose.")
        ],
        "chunks": [
            "The traditional model of carrots and sticks is fundamentally flawed.",
            "Extrinsic rewards narrow cognitive focus and extinguish organic creativity.",
            "True engagement stems from autonomy, mastery, and meaningful purpose."
        ]
    },
    {
        "id_code": "b2_05_interview_about_two_books",
        "day_number": 41,
        "level": "B2",
        "title": "Literary Review: Two Modern Novels",
        "topic": "Narrative Technique, Dystopian Themes & Subtext",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b2-listening/an-interview-about-two-books",
        "audio_filename": "b2_interview_about_two_books.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Both authors interrogate how contemporary societies grapple with environmental degradation, yet their stylistic executions diverge radically."),
            ("en-GB-RyanNeural", "Indeed. While Miller employs visceral, claustrophobic prose to evoke impending collapse, Chen opts for biting political satire to expose institutional apathy."),
            ("en-GB-SoniaNeural", "It is precisely that stylistic contrast that makes reading them back-to-back such a stimulating intellectual exercise.")
        ],
        "chunks": [
            "Both authors interrogate environmental degradation through divergent styles.",
            "Miller employs claustrophobic prose while Chen opts for biting satire.",
            "The stylistic contrast makes reading them an intellectually stimulating exercise."
        ]
    },
    {
        "id_code": "b2_06_catch_up_after_a_trip",
        "day_number": 42,
        "level": "B2",
        "title": "Catching Up After a Sabbatical",
        "topic": "Cultural Immersion, Perspective Shifts & Returning",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b2-listening/catch-up-after-a-trip",
        "audio_filename": "b2_catch_up_after_a_trip.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Clara, it's wonderful to see you back in the studio! How was your six-month sabbatical across South America?"),
            ("en-GB-SoniaNeural", "Honestly, transformative. Stepping away from deadline-driven consulting forced me to reassess what truly constitutes productive living."),
            ("en-GB-RyanNeural", "Did you find it difficult to re-acclimate to corporate pacing upon your return?"),
            ("en-GB-SoniaNeural", "Initially, yes. But having experienced radically diverse cultural rhythms, I now guard my mental energy and work boundaries far more deliberately.")
        ],
        "chunks": [
            "How was your six-month sabbatical across South America?",
            "Stepping away forced me to reassess what constitutes productive living.",
            "I guard my mental energy and work boundaries far more deliberately."
        ]
    },
    {
        "id_code": "b2_07_creating_a_study_group",
        "day_number": 43,
        "level": "B2",
        "title": "Establishing an Academic Study Cohort",
        "topic": "Peer Accountability, Peer Review & Collaborative Synergies",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b2-listening/creating-a-study-group",
        "audio_filename": "b2_creating_a_study_group.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "If our study cohort is to be effective, we must establish rigorous ground rules rather than treating meetings as casual social gatherings."),
            ("en-GB-RyanNeural", "I agree. We should mandate that every member reads the assigned case studies in advance and prepares two critical discussion questions."),
            ("en-GB-SoniaNeural", "Excellent. We will also rotate the session facilitator role each week to ensure equitable participation and diverse analytical viewpoints.")
        ],
        "chunks": [
            "We must establish rigorous ground rules rather than casual gatherings.",
            "Every member must read assigned case studies in advance.",
            "Rotate the facilitator role each week to ensure equitable participation."
        ]
    },
    {
        "id_code": "b2_08_film_reviews",
        "day_number": 44,
        "level": "B2",
        "title": "Critical Film Reviews",
        "topic": "Cinematography, Directorial Vision & Pacing",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b2-listening/film-reviews",
        "audio_filename": "b2_film_reviews.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Director Nolan's newest historical drama has polarized critics worldwide."),
            ("en-GB-SoniaNeural", "Visually, the non-linear editing and practical sound effects create an overwhelming sensory immersion."),
            ("en-GB-RyanNeural", "However, several reviewers contend that the emotional resonance was sacrificed in favor of relentless technical virtuosity."),
            ("en-GB-SoniaNeural", "That is a valid criticism, yet the sheer audacious scale of the production is undeniably masterclass cinema.")
        ],
        "chunks": [
            "The newest historical drama has polarized critics worldwide.",
            "Non-linear editing and sound design create sensory immersion.",
            "Emotional resonance was sacrificed for technical virtuosity.",
            "The sheer audacious scale of the production is masterclass cinema."
        ]
    },
    {
        "id_code": "b2_09_how_to_study_effectively",
        "day_number": 45,
        "level": "B2",
        "title": "Cognitive Science: How to Study Effectively",
        "topic": "Spaced Retrieval, Interleaving & Neuroplasticity",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b2-listening/how-to-study-effectively",
        "audio_filename": "b2_how_to_study_effectively.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Rereading highlighted passages creates a dangerous cognitive illusion known as the fluency trap."),
            ("en-GB-RyanNeural", "Students assume because information looks familiar, they have mastered it. But memory consolidation only occurs through effortful retrieval practice."),
            ("en-GB-SoniaNeural", "Techniques like spaced flashcards and interleaving diverse problem types force the brain to rebuild neural pathways, maximizing long-term retention.")
        ],
        "chunks": [
            "Rereading highlighted passages creates the fluency trap illusion.",
            "Memory consolidation only occurs through effortful retrieval practice.",
            "Spaced flashcards and interleaving force the brain to rebuild neural pathways."
        ]
    },
    {
        "id_code": "b2_10_innovations_in_business",
        "day_number": 46,
        "level": "B2",
        "title": "Technological Innovations in Business",
        "topic": "Machine Learning, Supply Visibility & Predictive Logistics",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b2-listening/innovations-in-business",
        "audio_filename": "b2_innovations_in_business.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Modern manufacturing ecosystems are shifting from reactive maintenance to real-time predictive diagnostic models."),
            ("en-GB-SoniaNeural", "By embedding IoT sensors throughout factory infrastructure, plant supervisors receive automated alerts before mechanical components suffer catastrophic fatigue."),
            ("en-GB-RyanNeural", "This predictive visibility drastically minimizes unplanned downtime and optimizes spare parts inventory management.")
        ],
        "chunks": [
            "Manufacturing is shifting from reactive maintenance to predictive diagnostic models.",
            "IoT sensors alert supervisors before components suffer catastrophic fatigue.",
            "Predictive visibility minimizes downtime and optimizes spare parts management."
        ]
    },
    {
        "id_code": "b2_11_negotiating_an_agreement",
        "day_number": 47,
        "level": "B2",
        "title": "Negotiating a Commercial Agreement",
        "topic": "Contractual Clauses, Liability Caps & Win-Win Terms",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b2-listening/negotiating-an-agreement",
        "audio_filename": "b2_negotiating_an_agreement.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "We have reviewed your proposed service level agreement, but the proposed liability cap remains unacceptable for our compliance board."),
            ("en-GB-RyanNeural", "We recognize your exposure risk, Ms. Thorne. If we increase the indemnity ceiling to three million pounds, would you consent to extending the contract duration from two to three years?"),
            ("en-GB-SoniaNeural", "That trade-off demonstrates good faith. Provided the termination for convenience clause remains reciprocal, we can sign off on those revised terms.")
        ],
        "chunks": [
            "The proposed liability cap remains unacceptable for our compliance board.",
            "If we increase the indemnity ceiling, would you consent to a three-year contract?",
            "That trade-off demonstrates good faith. We can sign off on those terms."
        ]
    },
    {
        "id_code": "b2_12_team_meeting_at_work",
        "day_number": 48,
        "level": "B2",
        "title": "Strategic Team Alignment Meeting",
        "topic": "Resource Bottlenecks, Cross-Functional Sync & OKRs",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/b2-listening/team-meeting-work",
        "audio_filename": "b2_team_meeting_at_work.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Let's review our quarterly key results. The engineering team has successfully resolved the backend latency issues, reducing database queries by forty percent."),
            ("en-GB-SoniaNeural", "That's exceptional progress. However, marketing has raised concerns that our onboarding flow is experiencing a twenty percent drop-off during user registration."),
            ("en-GB-RyanNeural", "Understood. Let's form a dedicated task force uniting product design and frontend developers to streamline that specific friction point within the next sprint.")
        ],
        "chunks": [
            "Engineering has reduced backend database queries by forty percent.",
            "Our onboarding flow is experiencing a twenty percent drop-off during registration.",
            "Let's form a dedicated task force to streamline that specific friction point."
        ]
    },

    # ==========================================
    # LEVEL C1 (12 LESSONS)
    # ==========================================
    {
        "id_code": "c1_01_a_talk_about_creativity",
        "day_number": 49,
        "level": "C1",
        "title": "The Neurobiology of Breakthrough Creativity",
        "topic": "Cognitive Incubation, Default Mode Network & Innovation",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/c1-listening/a-talk-about-creativity",
        "audio_filename": "c1_a_talk_about_creativity.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Popular mythology depicts creative epiphany as an erratic, thunderbolt inspiration visited upon rare geniuses."),
            ("en-GB-SoniaNeural", "Neuroimaging reveals a profoundly different reality: creative breakthroughs emerge from the intricate interplay between executive control networks and the spontaneous default mode network."),
            ("en-GB-SoniaNeural", "Without deliberate periods of cognitive incubation and low-stimulus reflection, the human brain cannot synthesize disparate conceptual schemas into truly groundbreaking paradigms.")
        ],
        "chunks": [
            "Creative epiphany is not an erratic thunderbolt visited upon rare geniuses.",
            "Breakthroughs emerge between executive control and the default mode network.",
            "Without periods of cognitive incubation, the brain cannot synthesize groundbreaking paradigms."
        ]
    },
    {
        "id_code": "c1_02_art_consultancy_presentation",
        "day_number": 50,
        "level": "C1",
        "title": "Art Consultancy: High-Value Cultural Assets",
        "topic": "Provenance Verification, Secondary Market & Asset Class",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/c1-listening/an-art-consultancy-presentation",
        "audio_filename": "c1_art_consultancy_presentation.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "In an era of macroeconomic volatility, institutional investors are increasingly allocating capital toward blue-chip contemporary art as an uncorrelated store of value."),
            ("en-GB-SoniaNeural", "However, navigating secondary auction ecosystems requires forensic provenance due diligence and rigorous spectroscopic material analysis."),
            ("en-GB-RyanNeural", "Precisely. Capital preservation hinges on authenticating legal title, condition reports, and historical museum exhibition pedigree.")
        ],
        "chunks": [
            "Institutional investors allocate capital toward blue-chip art as an uncorrelated store of value.",
            "Secondary auction ecosystems require forensic provenance due diligence.",
            "Capital preservation hinges on legal title and museum exhibition pedigree."
        ]
    },
    {
        "id_code": "c1_03_challenges_in_the_workplace",
        "day_number": 51,
        "level": "C1",
        "title": "Navigating Systemic Workplace Dynamics",
        "topic": "Siloed Communication, Power Asymmetry & Cultural Drift",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/c1-listening/challenges-in-the-workplace",
        "audio_filename": "c1_challenges_in_the_workplace.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "When multinational enterprises undergo rapid mergers, the most perilous impediment is rarely financial synergy, but latent cultural incompatibility."),
            ("en-GB-RyanNeural", "Siloed fiefdoms emerge as legacy managers instinctively consolidate institutional power, breeding passive resistance to modern compliance directives."),
            ("en-GB-SoniaNeural", "Overcoming this friction requires transparent executive empathy, cross-pollinated project squads, and uncompromising psychological safety.")
        ],
        "chunks": [
            "The most perilous impediment in mergers is latent cultural incompatibility.",
            "Siloed fiefdoms emerge as legacy managers consolidate institutional power.",
            "Overcoming friction requires transparent executive empathy and psychological safety."
        ]
    },
    {
        "id_code": "c1_04_ethical_business_practices",
        "day_number": 52,
        "level": "C1",
        "title": "Ethical Governance in Modern Capitalism",
        "topic": "Shareholder Primacy, ESG Audits & Greenwashing",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/c1-listening/ethical-business-practices",
        "audio_filename": "c1_ethical_business_practices.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "The historical dogma of Milton Friedman—that a corporation's sole fiduciary duty is shareholder value maximization—has suffered catastrophic intellectual erosion."),
            ("en-GB-SoniaNeural", "Consumers and institutional sovereign funds now scrutinize supply-chain labor provenance and lifecycle carbon footprints with unprecedented vigor."),
            ("en-GB-RyanNeural", "Performative greenwashing statements are swiftly unmasked by independent investigative audits, inflicting irreparable reputational damage on negligent brands.")
        ],
        "chunks": [
            "The dogma that a corporation's sole duty is shareholder value has suffered erosion.",
            "Sovereign funds scrutinize supply-chain labor provenance and carbon footprints.",
            "Performative greenwashing statements are swiftly unmasked by investigative audits."
        ]
    },
    {
        "id_code": "c1_05_leadership_emotional_intelligence",
        "day_number": 53,
        "level": "C1",
        "title": "Leadership & Emotional Intelligence at Scale",
        "topic": "Executive Presence, Empathic Feedback & Resonance",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/c1-listening/leadership-and-emotional-intelligence",
        "audio_filename": "c1_leadership_emotional_intelligence.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Technical prowess and quantitative acumen may secure an executive appointment, but emotional intelligence determines whether an enterprise thrives or atrophies."),
            ("en-GB-RyanNeural", "Resonant leaders exhibit metacognitive self-regulation under duress, reframing organizational setbacks as empirical learning opportunities."),
            ("en-GB-SoniaNeural", "By fostering authentic vulnerability rather than projecting dogmatic infallibility, they galvanize cross-disciplinary talent into sustained, passionate alignment.")
        ],
        "chunks": [
            "Technical prowess may secure an appointment, but emotional intelligence determines whether firms thrive.",
            "Resonant leaders exhibit metacognitive self-regulation under duress.",
            "Authentic vulnerability galvanizes talent into sustained, passionate alignment."
        ]
    },
    {
        "id_code": "c1_06_managing_organisational_change",
        "day_number": 54,
        "level": "C1",
        "title": "Managing Transformational Organisational Change",
        "topic": "Kotter's Model, Change Resistance & Strategic Alignment",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/c1-listening/managing-change-in-an-organisation",
        "audio_filename": "c1_managing_organisational_change.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Seventy percent of enterprise digital transformation initiatives fail to achieve their anticipated returns on investment."),
            ("en-GB-SoniaNeural", "The fundamental diagnosis is invariably organizational inertia: leadership promulgates architectural mandates without articulating a compelling, empathetic case for why front-line workers should alter ingrained habits."),
            ("en-GB-RyanNeural", "Change must be socialized through peer champions and anchored in immediate operational wins to dismantle systemic skepticism.")
        ],
        "chunks": [
            "Seventy percent of digital transformations fail to achieve anticipated ROI.",
            "Leadership promulgates mandates without articulating an empathetic rationale.",
            "Change must be socialized through peer champions and immediate operational wins."
        ]
    },
    {
        "id_code": "c1_07_negotiating_high_stakes_contract",
        "day_number": 55,
        "level": "C1",
        "title": "Negotiating a High-Stakes M&A Contract",
        "topic": "Mergers & Acquisitions, Earnouts & Indemnity Caps",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/c1-listening/negotiating-a-high-stakes-contract",
        "audio_filename": "c1_negotiating_high_stakes_contract.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Counsel, our acquisition syndicate will not endorse closing this transaction while the seller's representations omit unquantified intellectual property litigations."),
            ("en-GB-RyanNeural", "We can accommodate your exposure concerns by structuring an escrow holdback of fifteen percent for twenty-four months post-acquisition."),
            ("en-GB-SoniaNeural", "If that escrow is supplemented by an earn-out mechanism tethered to EBITDA milestones, we believe our principals will sanction execution.")
        ],
        "chunks": [
            "Our syndicate will not close while representations omit unquantified IP litigations.",
            "We can structure an escrow holdback of fifteen percent for twenty-four months.",
            "Tethering an earn-out mechanism to EBITDA milestones permits execution."
        ]
    },
    {
        "id_code": "c1_08_persuasion_and_influence",
        "day_number": 56,
        "level": "C1",
        "title": "The Art of Persuasion & Influence in Business",
        "topic": "Rhetorical Framing, Cialdini's Principles & Stakeholders",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/c1-listening/persuasion-and-influence-in-business",
        "audio_filename": "c1_persuasion_and_influence.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Persuasion is frequently mischaracterized as coercion, whereas sophisticated influence is the discipline of uncovering latent alignment between disparate agendas."),
            ("en-GB-SoniaNeural", "Effective rhetoricians frame proposals through the risk-aversion paradigm of their audience, emphasizing downside mitigation before dangling upside potential."),
            ("en-GB-RyanNeural", "When stakeholders perceive that their autonomy is thoroughly respected, institutional consensus coalesces seamlessly.")
        ],
        "chunks": [
            "Sophisticated influence is the discipline of uncovering latent alignment.",
            "Effective rhetoricians frame proposals through the risk-aversion paradigm of their audience.",
            "When stakeholder autonomy is respected, consensus coalesces seamlessly."
        ]
    },
    {
        "id_code": "c1_09_sustainability_corporate_responsibility",
        "day_number": 57,
        "level": "C1",
        "title": "Corporate Sustainability: Circular Economy Paradigms",
        "topic": "Lifecycle Assessment, Closed-Loop Systems & Scope 3",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/c1-listening/sustainability-and-corporate-responsibility",
        "audio_filename": "c1_sustainability_corporate_responsibility.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "Transitioning toward genuine circularity demands fundamentally redesigning product architecture for disassembly, modular reuse, and zero virgin landfill extraction."),
            ("en-GB-RyanNeural", "Most multinational audits currently fall short because they fixate on Scope 1 direct emissions while disregarding upstream Scope 3 supplier logistics."),
            ("en-GB-SoniaNeural", "Corporations that successfully integrate closed-loop supply chains insulate themselves from geopolitical raw material shortages while capturing premium consumer loyalty.")
        ],
        "chunks": [
            "Circularity demands redesigning products for disassembly and modular reuse.",
            "Audits fixate on Scope 1 emissions while disregarding upstream Scope 3 logistics.",
            "Closed-loop supply chains insulate firms from raw material shortages."
        ]
    },
    {
        "id_code": "c1_10_technological_disruption_industry",
        "day_number": 58,
        "level": "C1",
        "title": "Technological Disruption & Market Darwinism",
        "topic": "Innovator's Dilemma, Generative AI & Asymmetric Threats",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/c1-listening/technological-disruption-in-industry",
        "audio_filename": "c1_technological_disruption_industry.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Clayton Christensen's classic Innovator's Dilemma is unfolding today at unprecedented velocity across software, legal, and financial sectors."),
            ("en-GB-SoniaNeural", "Incumbents optimize margins for existing premium clientele while novel algorithmic models capture low-margin exploratory tiers and rapidly scale upward."),
            ("en-GB-RyanNeural", "Those who perceive these technological shifts as passing fads will inevitably suffer the exact obsolescence that befell traditional film photography.")
        ],
        "chunks": [
            "The Innovator's Dilemma is unfolding at unprecedented velocity.",
            "Incumbents optimize margins while algorithmic models capture low-margin tiers.",
            "Those who ignore these shifts will suffer the obsolescence of traditional film photography."
        ]
    },
    {
        "id_code": "c1_11_future_of_work_automation",
        "day_number": 59,
        "level": "C1",
        "title": "The Future of Knowledge Work & Cognitive Automation",
        "topic": "Augmented Intelligence, Skill Decay & Human Moats",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/c1-listening/the-future-of-work-and-automation",
        "audio_filename": "c1_future_of_work_automation.mp3",
        "dialogue": [
            ("en-GB-SoniaNeural", "As frontier neural networks achieve parity with human syntactic generation and computational synthesis, what constitutes the enduring human competitive moat?"),
            ("en-GB-RyanNeural", "The defensible frontier resides in contextual discernment, philosophical ethics, and the synthesis of ambiguous human emotional nuances."),
            ("en-GB-SoniaNeural", "The knowledge workers of tomorrow will not compete with algorithmic intelligence; rather, they will function as high-context curators orchestrating complex model constellations.")
        ],
        "chunks": [
            "What constitutes the enduring human competitive moat as neural networks advance?",
            "The defensible frontier resides in contextual discernment and philosophical ethics.",
            "Future workers will function as high-context curators orchestrating model constellations."
        ]
    },
    {
        "id_code": "c1_12_urban_planning_smart_cities",
        "day_number": 60,
        "level": "C1",
        "title": "Urban Planning: Smart Megacities of 2050",
        "topic": "Biophilic Architecture, Autonomous Transit & Density",
        "source": "https://learnenglish.britishcouncil.org/skills/listening/c1-listening/urban-planning-and-smart-cities",
        "audio_filename": "c1_urban_planning_smart_cities.mp3",
        "dialogue": [
            ("en-GB-RyanNeural", "Designing sustainable megacities capable of housing thirty million residents requires repudiating car-centric suburban sprawling architectures."),
            ("en-GB-SoniaNeural", "The emerging paradigm integrates fifteen-minute biophilic urban density, subterranean autonomous freight logistics, and passive microclimate cooling networks."),
            ("en-GB-RyanNeural", "By harmonizing ecological restoration with high-density architectural ingenuity, 21st-century cities can become carbon-negative sanctuaries rather than environmental burdens.")
        ],
        "chunks": [
            "Designing megacities requires repudiating car-centric sprawling architectures.",
            "The emerging paradigm integrates fifteen-minute density and autonomous freight logistics.",
            "21st-century cities can become carbon-negative sanctuaries rather than burdens."
        ]
    }
]

async def generate_lesson_audio(lesson):
    out_path = os.path.join(AUDIO_DIR, lesson["audio_filename"])
    if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
        return
        
    print(f"Generating audio: {lesson['title']} [{lesson['level']}]...")
    with open(out_path, "wb") as f_out:
        for voice, text in lesson["dialogue"]:
            communicate = edge_tts.Communicate(text, voice)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f_out.write(chunk["data"])

async def main():
    print(f"=== Generating Missing British Council Audios ({len(LESSONS)} tracks total) ===")
    for l in LESSONS:
        await generate_lesson_audio(l)
        
    print("\n=== Updating Database: listening_shadowing ===")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Clean and re-populate with full 60-track curriculum
    cur.execute("DELETE FROM listening_shadowing")
    conn.commit()
    
    for l in LESSONS:
        full_transcript = " ".join([text for _, text in l["dialogue"]])
        audio_url = f"/audio/{l['audio_filename']}"
        word_count = len(full_transcript.split())
        est_duration = max(25, round(word_count / 2.5))
        
        cur.execute("""
        INSERT INTO listening_shadowing (day_number, title, level, audio_url, transcript, duration_seconds, shadowing_chunks, audio_filename, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            l["day_number"],
            l["title"],
            l["level"],
            audio_url,
            full_transcript,
            est_duration,
            json.dumps(l["chunks"], ensure_ascii=False),
            l["audio_filename"],
            l["source"]
        ))
        
    conn.commit()
    conn.close()
    print(f"[OK] Successfully loaded all {len(LESSONS)} tracks across A1, A2, B1, B2, C1 into data/duohub.db!")

if __name__ == "__main__":
    asyncio.run(main())
