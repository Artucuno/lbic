from interactions import listen

from lbic import LoadClient, ClientSettings, ResourceType
from argparse import ArgumentParser

# Get node name from command line arguments
parser = ArgumentParser()
parser.add_argument('node_name', type=str, help='The name of the node')
parser.add_argument('webserver_port', type=int, help='The port of the webserver')
parser.add_argument('socket_url', type=str, help='The URL of the other client')

args = parser.parse_args()

# Create client settings object
settings = ClientSettings(
    socket_identifier=args.node_name,
    webserver_port=args.webserver_port,
    socket_urls=[args.socket_url],
    balance_type=ResourceType.cpu,
)

# Create a client with the default settings
bot = LoadClient(settings)
bot.load_extension('cogs.test_cog')


@listen
async def on_ready():
    print(f"Logged in as {bot.app}")
    print(f"Node name: {bot.settings.socket_identifier}")
    await bot.sio.emit('hello', {'name': bot.settings.socket_identifier})  # Send a hello message to all nodes (Just an example)

# Start the client
bot.start("your_token_here")
