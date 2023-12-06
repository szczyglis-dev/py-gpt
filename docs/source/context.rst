Context and memory
==================

Short and long-term memory
--------------------------
**PYGPT** lets you chat in continuous mode, which uses a long context for the conversation. 
It saves the entire conversation context and automatically includes it with all messages sent to 
the AI (prompts). Plus, you can go back to previous conversations at any time. 
The app saves your chat history, and you can pick up right where you left off.


Handling multiple contexts
---------------------------
On the left side of the screen, you'll see a list of saved contexts. You can add as many contexts as you 
want and easily switch between them. Whenever you need to, you can jump back to any previous conversation. 
The app automatically makes a summary (title) for each context, just like ``ChatGPT`` does, 
but you can also change it whenever you want.

.. image:: images/v2_context_list.png
   :width: 400

You can disable context support in the settings by using the following option:

.. code-block:: ini

   Config -> Settings -> Use context 


Clearing history
-----------------

You can clear the entire memory (all contexts) by selecting the menu option:

.. code-block:: ini

   File -> Clear history...


Context storage
-----------------
On the application side, the context is stored in the user's directory as ``JSON`` files. 
In addition, all history is also saved to ``.txt`` files for easy reading.