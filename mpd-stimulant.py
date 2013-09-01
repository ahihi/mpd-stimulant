#!/usr/bin/env python
import argparse
import os
from select import select
import socket
import subprocess
import sys
import threading
import time

import mpd

def msg(text):
    print >> sys.stderr, text

def disconnect(client):
    try:
        client.disconnect()
    except mpd.ConnectionError:
        pass

def stimulant(args):
    params = ["/usr/bin/caffeinate", args.mpc]
    def add_param(key, value):
        if value != None:
            params.extend([key, value])
    add_param("--host", args.host)
    add_param("--port", args.port)
    add_param("--password", args.password)
    params.extend(["idle", "player"])
    subprocess.check_output(params)

class AuthError(Exception):
    pass

env_host = os.environ.get("MPD_HOST", "localhost")
env_port = os.environ.get("MPD_PORT", None)

env_password = None
if env_host.find("@") >= 0:
    (env_password, env_host) = env_host.split("@", 1)

parser = argparse.ArgumentParser(
    formatter_class = argparse.RawTextHelpFormatter
)
parser.add_argument(
    "--mpc",
    dest = "mpc",
    help = "MPC path",
    default = "/usr/local/bin/mpc"
)
parser.add_argument(
    "--host",
    dest = "host",
    help = "MPD host",
    default = env_host
)
parser.add_argument(
    "--port",
    dest = "port",
    help = "MPD port",
    default = env_port
)
parser.add_argument(
    "--password",
    dest = "password",
    help = "MPD password",
    default = env_password
)
parser.add_argument(
    "--reconnect-interval",
    dest = "reconnect_interval",
    help = "seconds to wait before reconnecting on connection failure (default: 30)",
    type = float,
    default = 30
)

args = parser.parse_args()

client = mpd.MPDClient()
try:
    while True:
        try:
            msg("Connecting to MPD...")
            client.connect(args.host, args.port)
            msg("Connected.")
            if args.password != None:
                try:
                    msg("Authenticating...")
                    client.password(args.password)
                    msg("Authenticated.")
                except mpd.CommandError, e:
                    raise AuthError(e)

            stim_thread = None
            while True:
                status = client.status()                    
                if status["state"] == "play":
                    stim_thread = threading.Thread(target = stimulant, args = (args,))
                    stim_thread.daemon = True
                    stim_thread.start()
                client.send_idle("player")
                select((client,), (), ())
                client.fetch_idle()
        except (mpd.ConnectionError, AuthError, socket.error), e:
            msg("Error: %s" % e)
            msg("Reconnecting in %d seconds..." % args.reconnect_interval)
            time.sleep(args.reconnect_interval)
        finally:
            disconnect(client)
except KeyboardInterrupt, e:
    pass
