# KBPrasp_bot - a bot for helping students of College of business and law

This bot is developed with various features in mind to let people use most of the College of business and law's services right in a telegram chat.


## Installation

The installation process is plain and simple.

1. Clone the repository
2. Set up a mysql database server and create a database
3. Create necessary tables in the database, using setup.sql file in the `db` directory
4. Create an app in your [Telegram core](https://my.telegram.org/apps) and grab api id and api hash
5. Go to [BotFather](https://t.me/BotFather) and get your bot token
6. Fill the .env file with the necessary data
7. Set up python virtual environment and install requirements from requirements.txt
8. Fill database tables with data, acuired from scripts in the `tools` directory
9. Run the bot with `python main.py`

If you use docker, there is a Dockerfile to build a docker image.

## Contributing

If you want to contribute to the bot, you can do so by forking the repository, making changes and sending a pull request.

## License

This project is licensed under the GPLv3 License - see the LICENSE file for details

