import sys
import pathlib
from google import genai
from google.genai import types
print('python', sys.version)
print('module google.genai file', genai.__file__)
print('types has GenerateContentConfig', hasattr(types, 'GenerateContentConfig'))
print('Client has chats attr', hasattr(genai.Client, 'chats'))
print('Client methods', [m for m in dir(genai.Client) if not m.startswith('_')])
