Token usage calculation
========================

Input tokens
--------------
The application features a token calculator. It attempts to forecast the number of tokens that 
a particular query will consume and displays this estimate in real time. This gives you improved 
control over your token usage. The app provides detailed information about the tokens used for the user's prompt, 
the system prompt, any additional data, and those used within the context (the memory of previous entries).

**Remember that these are only approximate calculations and do not include, for example, the number of tokens consumed by certain tokens. You can find the exact number of tokens used on the OpenAI website.**

.. image:: images/v2_tokens1.png
   :width: 400

Total tokens
-------------
After receiving a response from the model, the application displays the actual total number of tokens used for the query.

.. image:: images/v2_tokens2.png
   :width: 400