import interactions
from interactions import Extension, slash_command, Button, ButtonStyle, component_callback, ComponentContext

from lbic import LoadClient


class MyExtension(Extension):
    def __init__(self, bot: LoadClient):
        self.bot = bot
        self.count = 0
        self.bot.webserver.on_event('button_press', self.button_press)  # Register event handler

    def button_press(self, sid, data):  # Event handler for button_press event
        self.count = data
        print(f'Button pressed {self.count} times')

    @component_callback("button_pressed")
    async def my_callback(self, ctx: ComponentContext):
        self.count += 1
        await self.bot.sio.emit('button_press', self.count)  # Emit event to all connected nodes
        embed = interactions.Embed(title=f"Times button has been clicked - {self.count}", description=f"{self.count}")
        embed.set_footer(text=f"{self.bot.socket_identifier} ({self.bot.latency * 100}ms)")
        buttons = [Button(label="Increase Count", style=ButtonStyle.PRIMARY, custom_id="button_pressed")]
        await ctx.edit_origin(content=f"Hello, {ctx.author}!", embed=embed, components=buttons)

    @slash_command()
    async def button(self, ctx):
        """Button test"""
        embed = interactions.Embed(title=f"Times button has been clicked - {self.count}", description=f"{self.count}")
        embed.set_footer(text=f"{self.bot.socket_identifier} ({self.bot.latency * 100}ms)")
        buttons = [Button(label="Increase Count", style=ButtonStyle.PRIMARY, custom_id="button_pressed")]
        await ctx.send(f"Hello, {ctx.author}!", embed=embed, components=buttons)

    @slash_command()
    async def nodes(self, ctx):
        """Get all nodes"""
        a = ''
        for f in self.bot.nodes:
            a += f'{self.bot.socket_identifier} ({self.bot.latency * 100}ms): {f.name} - {f.connected}\n'
        await ctx.channel.send(a)


def setup(bot):
    MyExtension(bot)
