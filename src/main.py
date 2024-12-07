import json
import os
from dotenv import load_dotenv

import discord
import colorama

from groq import Groq
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain.chains import ConversationChain
from langchain_groq import ChatGroq



# Auth
load_dotenv()
auth = os.getenv("AUTH")
groq_auth = os.getenv("GROQ_AUTH")

client = discord.Client(intents=discord.Intents.all())
colorama.init()

class colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    MSG = '\033[96m' # OKCYAN
    RESP = '\033[92m' # OKGREEN
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class Personality:
    """ An individual Personality object
    """
    def __init__(self, prompt: str):
        self.prompt = prompt

    def replace(self, item, replacement):
        self.prompt = self.prompt.replace(item, replacement)
        return self.prompt


class Personalities:
    """ A collection of prompts/personalities to pass to the chatbot as the initial setup message.
    """
    Alizey = Personality("Pretend you are a girl named Alizey, talking to a user named ${name}. Your hobbies are: being a history nerd, reading novels, makeup, hanging out with friends, etc. All your responses from now on should be as how Alizey would talk. The messages from now on would represent a normal Discord chat. Make sure your responses are girly and in all lowercase letters. Do not talk about posting images or anything like that, because you cannot post images. Do not talk about being an AI. You are not an AI, you are Alizey.")



class FileHandler:
    """
    A one-door interface for reading and writing operations
    """
    file = "memory.json"

    def write(content: dict):
        """ For write operations.
        Overwrites by default.
        Turns into json by default.
        """
        with open(FileHandler.file, "w") as f:
            f.write(json.dumps(content, indent=4))

    def read(**kwargs) -> str:
        """ For read operations.

        :kwargs
            :into_json (bool) => whether response should be in json or not
            :overwrite (bool) => if file contents are none, whether they should be overwritten or not

        :returns
            str | json
        """
        into_json = kwargs.get("into_json", True)
        overwrite = kwargs.get("overwrite", False)
        content = None

        with open(FileHandler.file, "r") as f:
            content = f.read()
            if into_json:
                try:
                    content = json.loads(content)
                except json.decoder.JSONDecodeError:
                    print(f"JSON decode error in FileHandler.read:\ncontent= {content}")
                    if overwrite:
                        content = {}
                        FileHandler.write(content)

        return content
    
    def read_config():
        with open("config.json", "r") as f:
            return json.loads(f.read())
    


class MemoryHandlerBase:
    """ Base for memory handling operations
    """
    def __init__(self, user: discord.User | discord.Member, personality: Personality):
        """
        :param user => The user the memory is assigned to
        :param personality => The personality to pass to the chatbot in the initial setup message
        """
        self.user = user
        self.personality = personality
        self.personality.replace("${name}", self.user.name)

    def _setup_new_memory(self):
        """ Setup the chatbot for a newly created memory.
        """
        self.chat(self.personality.prompt)

    def _memory_exists(self) -> bool:
        """ Use this to check if the memory list for the user exists or not
        """
        user = str(self.user.id)
        parent_dict = self._get_all_memories()
        check = parent_dict.get(user, False)
        if check != False:
            return True
        else:
            return False

    def _get_memory(self) -> list | None:
        """ Get a memory list for the user from memory.json.

        :returns
            Memory list if user is found.
            None if it isn't.
    
        :behavior
            Creates a new memory list if user is not found
        """
        user = str(self.user.id)

        parent_dict = FileHandler.read()
        try:
            result = parent_dict[user]
        except KeyError:
            result = []

        return result
            
    def _get_all_memories(self) -> dict:
        """ Get all memory lists from memory.json

        :returns
            memory.json contents in a dict, e.g.
            {
                "123": []
            }
        """
        # get parent dict
        parent_dict = FileHandler.read()
        return parent_dict


    def _save_msg(self, msg: dict):
        """ Save a msg to memory list of the user

        :param msg => A dict object containing "input" and "output" keys
        """
        parent_dict = self._get_all_memories()
        user = str(self.user.id)

        memory_list = self._get_memory()
        memory_list.append(msg)
        parent_dict[user] = memory_list
        FileHandler.write(parent_dict)


    def _get_buffer(self, empty: bool=False) -> ConversationBufferWindowMemory:
        """ Use this to get a ConversationBufferWindowMemory object loaded with recent memory.

        :param empty => Whether to return an empty buffer or not. True if memory off and False if on.
        :returns
            ConversationBufferWindowMemory

        """
        buffer = ConversationBufferWindowMemory(k=100, return_messages=True)
        if not empty:
            # load msgs to the buffer
            memory_list = self._get_memory()
            for message in memory_list:
                for input, output in message.items():
                    buffer.save_context(
                        {'input':input}, {'output':output}
                    )
        return buffer
    
    def _load_context(self, user: discord.User | discord.Member):
        """ Use this to load previous memory from a chat, as a way to provide context for the chatbot.

        :param user => The user to load context from.
        """

    def _judge_user(self, user: discord.User | discord.Member):
        """ Use this to judge how a user is based on their previous messages.
            This can help the chatbot be more relevant to them during a chat.

        :param user => The user to judge

        :behavior
            Goes through previous messages found in DMs or mutual servers, then passes that history to Groq which generates a description and judgement based on the given context.

        """


class Chatbot(MemoryHandlerBase):

    def __init__(self, user: discord.User | discord.Member, personality: Personality = Personalities.Alizey):
        """ Each chatbot instance should be assigned to ONE person.

        :param user => The person assigned to this instance of the chatbot.
        :param personality => The personality to pass to the chatbot in the initial setup message
        """
        super().__init__(user, personality)
        self.channel = user
        self.auth_key = groq_auth
        self.grai = Groq(api_key=self.auth_key)

    def parse_message(self, msg: discord.Message) -> str:
        """ Parse the message into a prompt to make it send-able to the chatbot

        :returns
            Prompt
        """
        content = f"{str(msg.author.name)}: {msg.content}"
        content = content.replace(client.user.mention, client.user.display_name)
        return content

    def parse_response(self, resp: str) -> str:
        """ Parse the response to make it send-able in the chat

        :returns
            Parsed response
        """
        resp = resp.replace("alizey.xoxo: ", "")
        return resp



    def chat(self, prompt: str, **kwargs) -> str:
        """ Chat with the chatbot.

        :param prompt => The prompt (or message) to respond to.
        :kwargs
            memory (bool): Whether memory should be used or not.

        :returns
            A string containing the response.
        """
        memory_perm = kwargs.get("memory", True)

        """ Note:
        In this method, memory_perm refers to the `memory` kwarg.
        Whereas memory refers to a ConversationBufferWindowMemory object.
        """
        if memory_perm: #kwarg memory=True
            memory = self._get_buffer()
        else: #kwarg memory=False
            memory = self._get_buffer(True) 

        groq_chat = ChatGroq(
            groq_api_key=self.auth_key,
            model_name="llama3-8b-8192"
        )

        conversation = ConversationChain(
            llm=groq_chat,
            memory=memory
        )
        resp = conversation.predict(input=prompt)

        # Save msg to the memory_list
        self._save_msg({
            'input':prompt,
            'output':resp
        })

        return resp

        """
        else: # memory=False
            chat = self.grai.chat.completions.create(
                messages=[
                {
                "role": "user",
                "content": prompt
                }],
                model="llama3-8b-8192")

            return chat.choices[0].message.content
        """

    async def respond(self, msg: discord.Message, **kwargs):
        """
        High-level interface for self.chat.
        Use this for responding to a message through a client.event method.
        """
        if not self._memory_exists():
            self._setup_new_memory()

        content = self.parse_message(msg)
        resp = self.chat(content)
        resp = self.parse_response(resp)

        ### for debugging
        if msg.channel.id == 1294309997194383442:
            await msg.channel.send(resp)
            return
        ###

        perm = Console.ask(f"{colors.HEADER}msg: {colors.ENDC}{colors.MSG}{msg.content}{colors.ENDC}\n{colors.HEADER}response: {colors.ENDC}{colors.RESP}{resp}{colors.ENDC}\nsend?")
        if perm:
            await msg.channel.send(resp)
            print("sent")
        else:
            print("not sent.")



class Console:
    """
    For console operations
    """
    CONFIG = FileHandler.read_config()
    VERSION = CONFIG["version"]
    STREAM = CONFIG["stream"] # whether incoming messages should be streamed

    def info():
        print(f"\n{colors.HEADER}>>> mass-chatbot {Console.VERSION} <<< {colors.ENDC}")

    def log(thing):
        print(thing)

    def ask(inp):
        perm = input(f"{inp} [y/n]\n>>>")
        if perm == "y":
            return True
        else:
            return False


@client.event
async def on_ready():
    await client.change_presence(status=discord.Status.online)
    Console.info()
    print(f"{colors.WARNING}Logged in.{colors.ENDC}")



@client.event
async def on_message(message):
    """ All chatbot instance handling happens here.
    """
    chatbot = Chatbot(message.author)
    if Console.STREAM:
        Console.log(f"{colors.OKBLUE}{message.guild.name}/{message.channel.name}/{message.author.display_name} : {message.content} {colors.ENDC}")


    if client.user.mentioned_in(message):
        if "show memory" in message.content:
            Console.log(chatbot._get_memory())
        else:
            await chatbot.respond(message)



if __name__ == "__main__":
    client.run(auth, bot=False)