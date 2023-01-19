try:
    from init_tg import (
        init_logs_chat,
        app_full_name,
        init_config,
        update_app,
        temp_data,
        proj_path,
        data_path,
        app_name,
        log_path,
        os_name,
        config,
        print,
        Path,
        rich,
        log,
        pg,
        os,
        c,
    )
except ModuleNotFoundError:
    from tg_backup.init_tg import (
        init_logs_chat,
        app_full_name,
        init_config,
        update_app,
        temp_data,
        proj_path,
        data_path,
        app_name,
        log_path,
        os_name,
        backup,
        config,
        print,
        Path,
        rich,
        log,
        pg,
        os,
        c,
    )

from pyrogram import errors
import shutil
import asyncio


log_console = None


async def main() -> None:
    await init_config()
    if config['tg_session']:
        bot = pg.client.Client(
            name = app_name,
            session_string = config.tg_session,
        )
        first_start = False
    else:
        phone_number = str(config.phone_number)
        if phone_number[0] != '+':
            phone_number = '+' + phone_number
        bot = pg.client.Client(
            name = app_name,
            api_id = config.api_id,
            api_hash = config.api_hash,
            phone_number = phone_number,
            app_version = app_full_name,
            device_model = os.getlogin(),
            system_version = os_name,
            in_memory = True,
            workers = 1,
        )
        first_start = True
    try:
        async with bot:
            global print
            global log_console
            global log
            temp_data['me'] = await bot.get_users('me')
            if first_start:
                config['tg_session'] = await bot.export_session_string()
            temp_data['handlers'] = {
                add:
                    ['add', 'a'],
            }
            await init_logs_chat(
                bot,
            )
            with open(
                log_path,
                'a'
            ) as log_file:
                log_console = rich.console.Console(
                    file = log_file,
                    width = 80,
                )
                def new_print(*args, **kwargs):
                    c.print(*args, **kwargs)
                    log_console.print(*args, **kwargs)

                def new_log(*args, **kwargs):
                    c.log(*args, **kwargs)
                    log_console.log(*args, **kwargs)

                print = new_print
                log = new_log
                await update_app(bot)

                while True:
                    await backup(
                        bot,
                    )
    except errors.AuthKeyUnregistered:
        config['tg_session'] = None
        await main()


async def sleep():
    with rich.progress.Progress(
        rich.progress.TextColumn("[progress.description]{task.description}"),
        rich.progress.BarColumn(),
        rich.progress.TimeRemainingColumn(),
    ) as timer:
        timer1 = timer.add_task(
            f'waiting for {config.timeout} seconds',
            total = config['timeout'],
        )
        step = 0.1
        while not timer.finished:
            timer.update(
                timer1,
                advance = step
            )
            await asyncio.sleep(step)



async def backup(
    bot,
):
    try:
        # cache_dir = Path(f'{data_path}/cache')
        # for file in config['pathes']:
        #     file = Path(file)
        #     shutil.rmtree(
        #         cache_dir,
        #         ignore_errors = True,
        #     )
        #     cache_dir.mkdir(
        #         exist_ok = True,
        #         parents = True,
        #     )
        #     log(file)
        #     log(file.name)
        #     os.system(
        #         f'7z a -tzip -v100M {cache_dir}/{file.name} {file}'
        #     )
        await sleep()
    except Exception:
        error_path = f'{proj_path}/error.txt'
        with open(
            error_path,
            'w',
        ) as file:
            c_error = rich.console.Console(
                width = 80,
                file = file,
            )
            c_error.print_exception(
                show_locals = True
            )
        c.print_exception(
            show_locals = True
        )
        log_console.print_exception(
            show_locals = True
        )
        await bot.send_document(
            chat_id = temp_data.logs_chat.id,
            document = error_path,
        )


async def add(
    bot: pg.client.Client,
    msg: pg.types.Message,
):
    splitted = msg.text.split()[1:]
    for path in splitted:
        path = Path(path)
        if path.exists():
            config['pathes'].append(
                str(path)
            )
            await msg.reply(f'successfully added {path}')
        else:
            await msg.reply(f'file {path} not exists on your computer')
    config.to_file()


asyncio.run(main())
