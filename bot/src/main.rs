extern crate dotenv;

use dotenv::dotenv;
use teloxide::{prelude::*, utils::command::BotCommands};

#[derive(BotCommands, Clone)]
#[command(rename_rule = "lowercase", description = "The following commands are supported:")]
enum Command {
    #[command(description = "Display this help message.")]
    Help,
    #[command(description = "For first time users to create a new account.")]
    Start(String),
}

async fn command_handler(bot: Bot, msg: Message, cmd: Command) -> ResponseResult<()> {
    match cmd {
        Command::Help => bot.send_message(msg.chat.id, Command::descriptions().to_string()).await?,
        Command::Start(username) => {
            // TODO: Check if the user already exists in the database
            if username.is_empty() {
                bot.send_message(msg.chat.id, "Please provide a username!").await?;
                return Ok(());
            } else {
                bot.send_message(
                    msg.chat.id, 
                    format!(
                        "Welcome {username}! If there is any project or submission deadlines that you would like me to keep track of, feel free to tell me!"
                    )).await?
            }
        }
    };

    Ok(())
}

async fn message_handler(msg: Message, bot: Bot) -> ResponseResult<()> {
    bot.send_message(msg.chat.id, "Hello, World!").await?;
    Ok(())
}

#[tokio::main]
async fn main() {
    dotenv().ok();
    // TODO: Set up database connection
    let bot = Bot::from_env();
    bot.set_my_commands(Command::bot_commands())
        .await
        .expect("Failed to set bot commands");

    let handler = dptree::entry()
        .branch(Update::filter_message().filter_command::<Command>().endpoint(command_handler))
        .branch(Update::filter_message().endpoint(message_handler));

    Dispatcher::builder(bot, handler)
        .enable_ctrlc_handler()
        .build()
        .dispatch()
        .await;
}
