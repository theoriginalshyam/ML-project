# AlgoFlux

AlgoFlux is an AI-assisted stock analysis platform built to simplify market research and decision support for learners and retail investors. It combines a modern web interface, a secure REST backend, and a Python machine learning service into a single end-to-end product.

## Detailed Website Description

AlgoFlux provides a guided workflow where users authenticate, choose a stock ticker, select a date window, and request short-horizon predictions. The platform then combines model-generated forecasts with sentiment and basic market context to present a more actionable view than raw charts alone.

The website focuses on three goals:

1. Reduce friction in stock analysis with a clean, task-oriented interface.
2. Make ML-powered forecasting accessible to non-experts.
3. Present model outputs in understandable visual and tabular formats.

### What Users Can Do

1. Register and sign in using JWT-based authentication.
2. Explore a protected dashboard after login.
3. Submit stock prediction requests by providing:
	- Ticker symbol
	- Start date
	- Number of forecast days
4. View prediction outputs, including:
	- Forecast values
	- Advice generated from model output
	- Sentiment score
	- Graph and tabular presentation of predicted points
5. Access additional pages such as About, Learn, and News.

### How The System Works

1. Frontend (React)
	- Captures user input and manages application flow.
	- Sends authenticated API requests to the Node backend.

2. Backend (Node.js + Express + MongoDB)
	- Handles authentication, authorization, and user management.
	- Validates and forwards ML-related requests to the Python service.
	- Stores user and token data in MongoDB.

3. ML Service (Flask + Python)
	- Accepts prediction/search requests from backend.
	- Runs model logic and returns prediction payloads.
	- Uses environment-based secret validation for service-to-service calls.

This architecture keeps concerns separated: UI in Client, API and auth in Backend, and model computation in ML_Models.

## Group Members

| S.No. | Name                 | Enrollment no |
| ----: | -------------------- | ------------- |
| 1.    | Gitanjala Srivardhan |               |
| 2.    | Arjun Ganesh         |               |
| 3.    | Krishna Pahariya     |               |
| 4.    | Shyam Agarwal        | 23116089      |

## Requirements

- Node.js
- Python
- Yarn Classic
- MongoDB (local or Atlas)

## Installation

1. Clone the repository.
2. Open the project folder.
3. Install frontend dependencies:
	- Move to Client
	- Run npm install
4. Install backend dependencies:
	- Move to Backend
	- Run yarn install
5. Install ML service dependencies:
	- Move to ML_Models
	- Create virtual environment
	- Activate virtual environment
	- Run pip install -r requirements.txt

## Run The Project

1. Start Backend
	- Move to Backend
	- Create .env from .env.example and fill values
	- Run yarn dev

2. Start ML Service
	- Move to ML_Models
	- Activate virtual environment
	- Run python app.py

3. Start Client
	- Move to Client
	- Run npm start

## Default Local Ports

- Client: 3000
- Backend: 5000
- ML Service: 6969
