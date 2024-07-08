# NUSBuddy

A reliable AI assistant in the form of a Telegram bot that will keep track of each students’ projects and homework submissions. 

## Setup

For those who want to set up their own personal Telegram bot.

### Install Git and Python

Follow the instructions [here](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) to install Git on your computer. Also follow this [guide](https://realpython.com/installing-python/) to install Python if you haven't already.

### Clone repository

Open a command line window and run these commands to clone this entire repository and install the additional dependencies required.

```
git clone https://github.com/SociallyIneptWeeb/NUSBuddy
cd NUSBuddy
pip install -r requirements.txt
```

### Obtain your Telegram bot token

Using the Telegram app, message the [BotFather](https://telegram.me/BotFather) by issuing the `/newbot` command and following the steps until you're given a new token. You can find a step-by-step guide [here](https://core.telegram.org/bots/features#creating-a-new-bot).

Your token will look something like this:

`4839574812:AAFD39kkdpWt3ywyRZergyOLMaJhac60qc`

### Environment variables

1. Rename the [.env.sample](.env.sample) file to `.env`
2. Update the `TELEGRAM_TOKEN` with the token from the previous step.
3. Update the `OPENAI_KEY` with an API key from OpenAI on this [page](https://platform.openai.com/api-keys).

### Docker Compose

Ensure you have Docker Compose installed, then run the following command to create and run the Postgres database in a docker container.

`docker-compose up -d`

## Usage

Run the following command in the [src](./src) directory to start your telegram bot.

`python telebot.py`

## Database Schema
![](images/schema.png?raw=true)
