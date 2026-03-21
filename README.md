<<<<<<< HEAD
# ML-project
=======
# StockScope
Our Company Stockscope comprises of four talented and motivated individuals, each bringing a unique set of skills and qualities to the group. It aims to make the process of trading stocks a little less daunting by using the power of Artificial Intelligence. We have to tried to predict stock prices and movement using LSTM Neural Network to predict future prices of the stock and BERT model and Technical Analysis to predict the future movement of price.

## Group Members

| S.No. | Name                | Enrollment no  |
| ----- | ------------------- | -------------- |
| 1.    | Gitanjala Srivardhan|        |
| 2.    | Arjun Ganesh        |       |
| 3.    | Krishna Pahariya    |      |
| 4.    | Shyam Agarwal       | 23116089       |

# Requirements
- Nodejs (https://nodejs.org/en/download)
- Python (https://www.python.org/downloads/)
- Yarn (https://classic.yarnpkg.com/lang/en/docs/install/#windows-stable)

# Steps for Installation: 
1. Clone the repository in your local directory using the command `git clone https://github.com/tanaykapadia/StockScope.git`
2. Change directory to cloned Repository `cd StockScope`
3. Install Client-Side dependencies `cd Client && npm start`
4. Install Express-Server-Side dependencies `cd Backend && yarn install`
5. Now we will be Installing Flask-Server-Side dependencies `cd ML_Model`
6. Creation and activating the virtual environment: 
`sudo apt install python3-venv`
`python3 -m venv ML_Model`
`source ML_Model/bin/activate`
7. Install dependencies `pip install -r requirements.txt`

# Steps to run the Client:
1. `cd Client`
2. `npm start`

# Steps to run the Express-Server:
1. `cd Backend`
2. Create a .env file similar to that given in .env.example file
2. `yarn start`

# Steps to run the Flask-Server:
1. `cd ML_Model`
2. `python3 app.py`
>>>>>>> f1189d8 (Initial Commit)
