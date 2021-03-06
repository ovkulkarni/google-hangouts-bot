import plugins
import sqlite3
from control import *
from admin import is_admin, is_tag
from ixio import ixio

def _initialise():
    plugins.register_user_command('quote')
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS quotes (author TEXT, quote TEXT, id INTEGER PRIMARY KEY AUTOINCREMENT)")
    c.execute("CREATE TABLE IF NOT EXISTS unapp_quotes (author TEXT, quote TEXT, id INTEGER PRIMARY KEY AUTOINCREMENT)")   
    conn.commit()
    conn.close()

def add(conn, q, author, admin=True):
    c = conn.cursor()
    quote = q.replace("**", "\*\*").replace("*", "\*").replace("__", "\_\_").replace("_", "\_") #wtf is this lmfao
    if admin:
        c.execute("INSERT INTO quotes(author, quote) VALUES (?, ?)", [author.lower(), quote])
        conn.commit()
        rply = "Successfully added quote {}!".format(c.lastrowid)
    else:
        c.execute("INSERT INTO unapp_quotes(author, quote) VALUES (?, ?)", [author.lower(), quote])
        conn.commit()
        rply = ["Quote submitted for approval.",
            "New quote submitted for approval. To approve, do\n! approve quote {}\n<b>Quote {}:</b> {} -- {}".format(c.lastrowid, c.lastrowid, quote, author)]
    return rply

def retrieve(conn, id_, author, full=True):
    c = conn.cursor()
    if not id_:
        if not full:
            c.execute('SELECT * FROM quotes ORDER BY RANDOM() LIMIT 1')
            q = c.fetchone()
            rply = format_quote(q)
        else:
            c.execute('SELECT * FROM quotes')
            q = c.fetchall()
            quotes = []
            for i in q:
                quotes.append(format_quote(i))
                rply =  '\n'.join(quotes)
    elif not author:
        c.execute('SELECT * FROM quotes WHERE id = ?', [id_])
        q = c.fetchone()
        rply = format_quote(q)
    elif author:
        if not full:
            c.execute('SELECT * FROM quotes WHERE author = ? ORDER BY RANDOM() LIMIT 1', [id_])
            q = c.fetchone() 
            rply = format_quote(q)
        elif id_:
            c.execute('SELECT * FROM quotes WHERE author = ?', [id_])
            q = c.fetchall()
            quotes = []
            for i in q:
                quotes.append(format_quote(i))
                rply =  '\n'.join(quotes)
    return rply

def delete(conn, id_):
   c = conn.cursor()
   c.execute("DELETE from quotes where id=?", [id_])
   conn.commit()

def edit(conn, id_, quote):
    c = conn.cursor()
    c.execute("SELECT * from quotes where id=?", [id_])
    if c.fetchone():
         c.execute("UPDATE quotes SET quote=? WHERE id=?", [quote, id_])
         rply = "Successfully edited quote {}".format(id_)
    else:
         rply = "No such quote."
    conn.commit()
    return rply

def format_quote(q):
    quote = "Quote {}: {} - {}".format(q[2], q[1], q[0])
    return quote

def quote(bot, event, *args):
    '''Manipulate quotes. Format is /bot quote [-a, -l]
To add quotes: /bot quote -a quote - author
To list all quotes: /bot quote -l
To list specific person's quotes: /bot quote -l name
To get a specific quote: /bot quote quote_number
To get a random quote: /bot quote
To get a random quote for a specifc author: /bot quote name'''
    msg = None
    try:
        conn = sqlite3.connect('bot.db')
        if not args:
            msg = retrieve(conn, None, None, full=False)
        elif args[0] not in ['-a', '-d', '-l', '-e'] and args[0].startswith('-'):
            msg = "Invalid Flag"
        elif args[0] in ['-d', '-e']:
            if len(args) < 2:
               msg = "You're missing arguments!"
            elif is_admin(bot, event) or is_tag(bot, event, 'quote-admin'): # admin only quote functions
                if args[0] == "-d": # delete quotes
                    delete(conn, args[1])
                    msg = "Successfully deleted quote"
                elif args[0] == "-e": # edit quotes
                    msg = edit(conn, args[1], " ".join(args[2:]))
            else:
                msg = "You're not an admin!"
        elif args[0] == "-l": # list quotes from author
            if len(args) == 1:
                msg = str(retrieve(conn, None, True))
            else:
                msg = str(retrieve(conn, args[1], True))
        elif args[0] == "-a":
            text = " ".join(args[1:]).split(' - ')
            if event.user.first_name.lower() == text[1]:
                msg = "You can't submit your own quote!" # self-submission
            else:
                if is_admin(bot, event) or is_tag(bot, event, 'quote-admin'):
                    msg = add(conn, text[0], text[1])
                else:
                    rply = add(conn, text[0], text[1], admin=False)
                    yield from bot.coro_send_message(CONTROL, _(rply[1]))
                    msg = rply[0]
        else:
            text = " ".join(args)
            author = True if not text.isnumeric() else False
            msg = retrieve(conn, text, author, full=False)
        #to_send = _(msg)
        print(msg)
        split = msg.split('\n')
        if len(split) > 4:
            msg = "<b>Message truncated:</b> See full message at {}\nHere are the last 4 lines: \n{}".format(
            	ixio(msg), "\n".join(split[-4:])) 
        #yield from bot.coro_send_message(event.conv, _(str(len(leng))))        
        yield from bot.coro_send_message(event.conv, _(msg))
        conn.close()
    except TypeError:
        msg = 'No such quote'
        yield from bot.coro_send_message(event.conv, _(msg))
    except BaseException as e:
        msg = '{} -- {}'.format(str(e), event.text)
        raise e
        yield from bot.coro_send_message(CONTROL, _(msg))
