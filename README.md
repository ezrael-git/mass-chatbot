# mass-chatbot
*Disclaimer:* Self-botting is against Discord TOS. I will not be responsible if your account gets permanently disabled for using this script.
## What is this?
A self-botting script that takes control of your account and utilizes AI to respond to DMs and mentions.
If you want to automate talking to multiple users at once on a fake account, this could be the tool you need.

**Why would anyone want to do that?** I personally need to for reasons I cannot disclose.

## Installing
Assuming you have Python and git bash installed.
Run the following commands:
```
git clone https://github.com/ezrael-git/mass-chatbot
pip install -r requirements.txt
```

## Run
To run the script just use the following commands
```
cd mass-chatbot/src
py main.py
```

## Environmental variables
Create a new file `.env` with the variables `AUTH` (your Discord token) and `GROQ_AUTH` (your Groq API key).

## Editing personality and behaviour
You can edit the chatbot's behaviour by going into the `Chatbot.handle_message` method where it initializes the `Chatbot` object.
In the second arg you can either pass one of the existing `Personality`s (see `Personalities` class) or create one of your own with a custom prompt. E.g.
```py
chatbot = Chatbot(message.author, Personality("Your name is ezrael-git and your hobbies are xyz."))
``` 