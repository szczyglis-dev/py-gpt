:: This script is used to install the app dependencies and run the app using the virtual environment
call python -m venv venv
call venv\Scripts\activate
call pip install -r requirements.txt
call python run.py %*