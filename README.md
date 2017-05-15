# Google Voice for Raspberry Pi
This project allow to have a hot word ( in this case JARVIS ), to trigger Google Assistant and ask any questions. 
The future version of the SDK will probably integrate the hot word but in the meantime this can be used.

#Google Assistant
Install Google Assistant SDK on your Raspberry Pi (preferably on version 3) and test the sample to make sure the authentication is working.
https://developers.google.com/assistant/sdk/prototype/getting-started-pi-python/

Locate the file assistant_credentials.json  and make sure you update the one on this folder to make the script working with Google services.

#Snowboy
This project has been setup with the keyword JARVIS, but on the main.py, you can modify this file, just download the file on the root and update on the python file.

#Custom command
I used this base code on my home setup, I left the method to intercept a command voice and do some custom actions, look at the Voice.py

#License
Feel free to use this code as you would like, I am more than happy to share what I found out that works for me.
