# license: gnu gpl 3 https://gnu.org/licenses/gpl-3.0.en.html
# sources: https://github.com/gmankab/tg_backup

try:
    from setup import (  # type: ignore
        modules_path,
        win_py_file,
        app_version,
        is_windows,
        proj_path,
        is_linux,
        app_name,
        portable,
        os_name,
        yes_no,
        run_st,
        run,
    )
except ModuleNotFoundError:
    from tg_backup.setup import (  # type: ignore
        modules_path,
        win_py_file,
        app_version,
        is_windows,
        proj_path,
        is_linux,
        app_name,
        portable,
        os_name,
        run_st,
        yes_no,
        run,
    )
from betterdata import Data
from pathlib import Path
from pyrogram.handlers import (
    MessageHandler,
)
from pyrogram import (
    filters,
    types,
)
import pyrogram as pg
import rich.traceback
import rich.progress
import rich.pretty
import rich.tree
import platform
import rich
import json
import sys
import os


class PollException(Exception):
    pass


class UnsupportedException(Exception):
    pass


rich.pretty.install()
rich.traceback.install(
    show_locals = True
)
c = rich.console.Console()

if sys.argv[-1].replace(
    '\\', '/'
).rsplit(
    '/', 1
)[-1] not in (
    '-m',
    'tg_backup',
    'tg_backup.py',
    'tg_backup_win.py',
):
    data_path = Path(
        sys.argv[-1]
    )
    if data_path.exists() and not data_path.is_dir():
        data_path = Path(
        f'{modules_path}/{app_name}_data'
    )
        c.log(f'can\'t use {sys.argv[-1]} as data path, it is not dir, using {data_path} instead')
    else:
        c.log(f'set {app_name} data path to [deep_sky_blue1]{sys.argv[-1]}')
else:
    data_path = Path(
        f'{modules_path}/{app_name}_data'
    )
if not data_path.exists():
    data_path.mkdir(
        exist_ok = True,
        parents = True,
    )
config_path = Path(
    f'{data_path}/{app_name}.yml'
)
log_path = Path(
    f'{data_path}/{app_name}.log'
)
config = Data(
    file_path = config_path
)
temp_data = Data()

print = c.print
log = c.log
pp = rich.pretty.pprint
reload = None
if os_name == 'Linux':
    try:
        os_name = platform.freedesktop_os_release()['PRETTY_NAME']
    except Exception:
        pass
os_name = f'{os_name} {platform.release()}'
python_imp = f'{platform.python_implementation()} {platform.python_version()}'
pip = f'{sys.executable} -m pip'


app_full_name = f'''\
gmanka {app_name} {app_version},
pyrogram {pg.__version__},
{python_imp}\
'''

acceptable_link_formats = '''\
acceptable link formats:
@chat_name
t.me/chat_name
t.me/c/1657778608
t.me/+6XqO65TrfatjNGU6
web.telegram.org/k/#-1657778608
'''
acceptable_links_examples = [
    '@chat_name',
    't.me/chat_name',
    't.me/+6XqO65TrfatjNGU6',
    'web.telegram.org/k/#-1657778608',
]

if portable:
    app_full_name = f'portable {app_full_name}'

start_message = app_full_name.replace(
    ',\n',
    '\n'
) + f'''
{os_name}
source code - https://github.com/gmankab/tg_backup
config path - `{config_path}`
'''


log(
    start_message,
    highlight = False,
)


async def is_chat_exist(
    bot: pg.client.Client,
    chat_id: str | int,
) -> types.Chat | bool:
    prefixes = ['-100', '-']
    if isinstance(
        chat_id,
        str,
    ):
        if (
            chat_id.isdigit()
        ) or (
            chat_id[0] == '-' and chat_id[1:].isdigit()
        ):
            for prefix in prefixes:
                chat_id = chat_id.replace(
                    prefix,
                    '',
                )
        to_check = [chat_id]
        for prefix in prefixes:
            to_check.append(prefix + chat_id)
    else:
        to_check = [chat_id]
    for i in to_check:
        if isinstance(
            i,
            str,
        ):
            if (
                chat_id.isdigit()
            ) or (
                chat_id[0] == '-' and chat_id[1:].isdigit()
            ):
                i = int(i)
        try:
            return await bot.get_chat(i)
        except Exception:
            pass
    return False


async def parse_chat_link(
    bot: pg.client.Client,
    chat_link: str
) -> tuple[types.Chat | str | None]:
    clean_chat_link = clean_link(chat_link)
    if not clean_chat_link:
        return None, clean_link
    elif clean_chat_link[:6] == 't.me/+':
        to_check = clean_chat_link
    elif clean_chat_link[:7] == 't.me/c/':
        to_check = clean_chat_link[7:].split('/')[0]
        clean_chat_link = 't.me/c/' + to_check
    elif clean_chat_link[:4] == 't.me':
        clean_chat_link = clean_chat_link.replace(
            't.me/',
            '@',
        )
        to_check = clean_chat_link
    elif clean_chat_link[0] == '@':
        to_check = clean_chat_link
    elif '.telegram.org/' in clean_chat_link:
        to_check = clean_chat_link.rsplit(
            '#',
            1,
        )[-1]
    else:
        return f'{clean_chat_link} is not clickable link to telegram chat', clean_chat_link
    chat = await is_chat_exist(
        bot,
        to_check,
    )
    if chat:
        return chat, clean_chat_link
    else:
        return f'{clean_chat_link} is a bad link', clean_chat_link


async def init_config() -> None:
    if config['app_version'] != app_version:
        config['app_version'] = app_version

    if 'check_updates' not in config:
        act = yes_no.choose(
            text = '[deep_sky_blue1]do you want to check updates on start?'
        )
        match act:
            case 'yes':
                config['check_updates'] = True
            case 'no':
                config['check_updates'] = False
            case 'exit':
                sys.exit()

    if (
        not config['api_id']
    ) or (
        not config['api_hash']
    ):
        print(
            '\nPlease open https://my.telegram.org/apps and get api_id and api_hash')
        print(
            '''\
[bold red]WARNING:[/bold red] [bold white]use only your own api_id and api_hash.[/bold white] I already tried to take them from decompiled official telegram app, and 20 minutes later my telegram account get banned. Then I wrote email with explanation on recover@telegram.org and on the next day and they unbanned me.
''', highlight = False
        )

    for item in (
        'api_id',
        'api_hash',
        'phone_number',
    ):
        config.interactive_input(item)
    if not config['can_configure']:
        config['can_configure'] = 'only_me'
    if not config['logs_chat']:
        config['logs_chat'] = 'saved_messages'
    if not config['timeout']:
        config['timeout'] = 10
    if 'pathes' not in config:
        config['pathes'] = []
    temp_data['config_handlers'] = []
    # if not config['7z_path']:
    architecture = platform.platform()
    if 'aarch64' in architecture and is_linux:
        config['7z_path'] = f'{data_path}/7z_linux_arm64'
    elif 'x86_64' in architecture and is_linux:
        config['7z_path'] = f'{data_path}/7z_linux_x86_64'
    elif 'x86_64' in architecture and is_linux:
        config['7z_path'] = f'{data_path}/7z_windows_x86.exe'
    else:
        config['7z_path'] = '7z'
    print(run_st(config['7z_path']))


async def set_logs_chat(
    bot: pg.client.Client,
    msg: types.Message
) -> None:
    chat_link = await split_msg(msg)
    if not chat_link:
        return
    reply = await applying(msg)
    logs_chat, clean_chat_link = await parse_chat_link(
        bot,
        chat_link
    )
    if isinstance(
        logs_chat,
        str,
    ):
        await reply.edit_text(
            logs_chat,
            disable_web_page_preview = True,
        )
    else:
        config['logs_chat'] = clean_chat_link
        temp_data['logs_chat'] = logs_chat
        await init_logs_chat(
            bot,
        )
        await reply.edit_text(
            f'successfully set {chat_link} as chat for settings and logs, please open it',
            disable_web_page_preview = True,
        )


async def help(
    bot: pg.client.Client,
    msg: types.Message = None,
    chat_id = None,
) -> None:
    if msg:
        reply_msg_id = msg.id
        chat_id = msg.chat.id
    else:
        reply_msg_id = None

    text = f'''
logs_chat = {config.logs_chat}

`/init_config CHAT_LINK`

example:
/init_config {config.logs_chat}

your config file path:
`{config_path}`

users, who can configure {app_name}:
can_configure = **{config.can_configure}**

`/set_can_configure_only_me`
`/set_can_configure_all_members_of_this_chat`

you can pass different config path as comman line argument

you can see acceptable link formats via this command:
/show_acceptable_link_formats
'''
    await bot.send_message(
        chat_id = chat_id,
        text = text,
        reply_to_message_id = reply_msg_id,
        disable_web_page_preview = True
    )

    text = '''\
folders_to_backup:
'''

    await bot.send_message(
        text = text,
        reply_to_message_id = reply_msg_id,
        chat_id = chat_id,
        disable_web_page_preview = True,
    )


async def split_msg(
    msg: types.Message,
) -> str | None:
    msg_words = msg.text.split()
    match len(msg_words):
        case 1:
            text = f'''\
you must paste link to chat after "{msg.text}"

examples:
'''
            for link in acceptable_links_examples:
                text += f'{msg.text} {link}\n'
            await msg.reply(
                text,
                disable_web_page_preview = True,
            )
        case 2:
            return clean_link(
                msg_words[-1]
            )
        case _:
            await msg.reply(
                'you must paste only 1 link',
                disable_web_page_preview = True,
            )


async def set_can_configure_all_members_of_this_chat(
    bot: pg.client.Client,
    msg: types.Message,
) -> None:
    reply: types.Message = await msg.reply(
        'applying...',
        quote = True,
    )

    config['can_configure'] = 'all_members'
    await refresh_config_handlers(
        bot,
    )
    await reply.edit_text(
        f'''\
successfully set **can_configure** to **{config.can_configure}**

use `/help` to configure {app_name}
'''
    )


async def set_can_configure_only_me(
    bot: pg.client.Client,
    msg: types.Message,
) -> None:
    reply: types.Message = await msg.reply(
        'applying...',
        quote = True,
    )

    config['can_configure'] = 'only_me'
    await refresh_config_handlers(
        bot,
    )
    await reply.edit_text(
        f'''\
successfully set **can_configure** to **{config.can_configure}**

use `/help` to configure {app_name}
'''
    )


async def show_acceptable_link_formats(
    bot: pg.client.Client,
    msg: types.Message,
) -> None:
    await msg.reply(
        text = acceptable_link_formats,
        quote = True,
    )


async def applying(
    msg: types.Message
) -> types.Message:
    return await msg.reply(
        text = 'applying...',
        quote = True,
    )


async def text_wrap(
    text: str,
    chunk_size: int = 1024,
):
    for chunk_start in range(
        0,
        len(text),
        chunk_size
    ):
        yield text[
            chunk_start:chunk_start + chunk_size
        ]


def get_msg_link(
    msg: types.Message,
) -> str | None:
    if (
        not msg.link
    ) or (
        msg.link[15] == '-'
    ):
        return None
    else:
        return clean_link(msg.link)


def clean_link(
    link: str,
) -> str:
    if not link:
        return
    return str(
        link.replace(
            'https://',
            '',
        ).replace(
            'http://',
            '',
        )
    )


async def refresh_config_handlers(
    bot: pg.client.Client,
) -> None:
    logs_chat = temp_data['logs_chat']
    for handler in temp_data['config_handlers']:
        bot.remove_handler(*handler)
    temp_data['config_handlers'] = []

    def blank_filters(
        commands: list[str] | str,
    ) -> None:
        match config.can_configure:
            case 'only_me':
                return filters.chat(
                    logs_chat.id
                ) & filters.user(
                    'me'
                ) & filters.command(
                    commands
                )
            case 'all_members':
                return filters.chat(
                    logs_chat.id
                ) & filters.command(
                    commands
                )

    async def new_handler(
        func,
        commands: list[str] | str,
    ) -> None:
        local_filters = blank_filters(
            commands = commands
        )
        raw_handler = MessageHandler(
            func,
            filters = local_filters,
        )
        handler = bot.add_handler(
            raw_handler
        )
        temp_data['config_handlers'].append(
            handler
        )

    for func, commands in list(
        {
            help:
                ['help', 'h'],
            set_can_configure_all_members_of_this_chat:
                'set_can_configure_all_members_of_this_chat',
            set_can_configure_only_me:
                'set_can_configure_only_me',
            show_acceptable_link_formats:
                'show_acceptable_link_formats',
            set_logs_chat:
                'set_logs_chat',
        }.items()
    ) + list(
        temp_data['handlers'].items()
    ):
        await new_handler(
            func = func,
            commands = commands,
        )


async def init_logs_chat(
    bot: pg.client.Client,
) -> None:
    me = temp_data['me']
    if config['logs_chat'] == 'saved_messages':
        temp_data['logs_chat'] = temp_data['me']
        if me.username:
            to_print = f'https://t.me/{me.username}'
        else:
            phone = config['phone_number']
            for i in ' +()-_':
                while i in phone:
                    phone = phone.replace(
                        i,
                        '',
                    )
            to_print = f'https://t.me/+{phone}'
    else:
        if not temp_data['logs_chat']:
            temp_data['logs_chat'] = (
                await parse_chat_link(
                    bot,
                    config['logs_chat'],
                )
            )[0]
        if not temp_data['logs_chat']:
            config['logs_chat'] = 'saved_messages'
            init_logs_chat(bot)
            return
        to_print = 'https://' + config[
            'logs_chat'
        ].replace(
            "@",
            "t.me/"
        )
    print(
        f'\n[bold green]please open telegram and see your logs chat - [/bold green][bold]{to_print}'
    )
    text = start_message.replace(
        'https://',
        ''
    ) + f'\nuse `/help` to configure {app_name}'
    if config['logs_chat'] == 'saved_messages':
        text += '\n\nit is [recommended](https://bugs.telegram.org/c/19148) to change the chat for logs with the command `/set_logs_chat` CHAT_LINK'
    elif temp_data['logs_chat'].type == pg.enums.ChatType.GROUP:
        text += '''\n
this chat is not supergroup, it is [recommended](https://bugs.telegram.org/c/19148) to use supergroups

if you want to convert group to supergroup, you must create public @name to group and then delete this @name, or link group to any channel
''',
    await bot.send_message(
        text = text,
        chat_id = temp_data['logs_chat'].id,
        disable_web_page_preview = True,
    )
    if log_path.exists() and log_path.stat().st_size:
        await bot.send_document(
            document = log_path,
            chat_id = temp_data['logs_chat'].id,
        )
        log_path.unlink(missing_ok = True)

    if not config['backup_paths']:
        await bot.send_message(
            chat_id = temp_data['logs_chat'].id,
            text = '''
please add path to files you need to backup from your computer:

`/add` **path**
'''
        )
    if not config['max_megabytes_filesize']:
        if temp_data['me'].is_premium:
            config['max_megabytes_filesize'] = 4000
        else:
            config['max_megabytes_filesize'] = 2000
    await refresh_config_handlers(
        bot,
    )


async def update_app(
    bot: pg.client.Client,
    forced = False,
):
    if not config.check_updates:
        return
    if not forced:
        print('[deep_sky_blue1]checking for updates')
        with rich.progress.Progress(
            transient = True
        ) as progr:
            progr.add_task(
                total = None,
                description = ''
            )
            packages = []
            pip_list = f'{pip} list --format=json --path {modules_path}'
            all_packages_str = run(pip_list)
            start = all_packages_str.find('[')
            end = all_packages_str.rfind(']') + 1
            all_packages_str = all_packages_str[start:end]
            try:
                all_packages = json.loads(
                    all_packages_str
                )
            except json.JSONDecodeError:
                progr.stop()
                print(
                    f'''
    {pip_list} command returned non-json output:

    {all_packages_str}
    '''
                )
                return
            for package in all_packages:
                if package['name'] != app_name:
                    packages.append(
                        package['name']
                    )

            command = f'{pip} list --outdated --format = json --path {modules_path}'
            for package in packages:
                command += f' --exclude {package}'

            updates_found_str = run(command)
            updates_found = app_name in updates_found_str
            progr.stop()

        if not updates_found:
            print('updates not found')
            return
    if not forced:
        await bot.send_message(
            chat_id = temp_data['logs_chat'].id,
            text = f'''\
    please open console to update app
    changelog - github.com/gmankab/{app_name}/blob/main/changelog.md
    ''',
        )
        act = yes_no.choose(
            text = f'''\
    [green]found updates, do you want to update {app_name}?
    changelog - https://github.com/gmankab/tg_backup/blob/main/changelog.md
    '''
        )
        match act:
            case 'yes':
                pass
            case 'no':
                return
            case 'exit':
                sys.exit()

    requirements = "betterdata easyselect gmanka_yml pyrogram tgcrypto humanize rich"

    await restart(
        commands = f'{pip} install --upgrade --no-cache-dir --force-reinstall {app_name} {requirements} --no-warn-script-location -t {modules_path}'
    )


async def restart(
    commands: str | list[str] | tuple[str],
):
    if is_windows:
        final_command = f'taskkill /f /pid {os.getpid()}'
    else:
        final_command = f'kill -2 {os.getpid()}'
    async def add_sleep():
        nonlocal final_command
        if is_windows:
            final_command += ' && sleep 1 && '
        else:
            final_command += ' && timeout /t 1 && '
    if isinstance(commands, str):
        commands = [commands]
    for command in commands:
        await add_sleep()
        final_command += command

    await add_sleep()
    final_command += f'{sys.executable} {proj_path}'
    print(f'restarting with command:\n{final_command}')
    os.system(
        final_command
    )
