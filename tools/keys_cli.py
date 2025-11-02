#!/usr/bin/env python3
import argparse
from core.key_store import key_store

parser = argparse.ArgumentParser(description="Encrypted API key store")
sub = parser.add_subparsers(dest="cmd", required=True)

s_set = sub.add_parser("set"); s_set.add_argument("name"); s_set.add_argument("value")
s_get = sub.add_parser("get"); s_get.add_argument("name")
s_ls  = sub.add_parser("ls")

parser.add_argument("--pass", dest="pw", default=None, help="passphrase override")

args = parser.parse_args()
if args.cmd == "set":
    key_store.set(args.name, args.value, passphrase=args.pw)
    print("OK")
elif args.cmd == "get":
    print(key_store.get(args.name))
elif args.cmd == "ls":
    # redacted view
    ks = key_store; ks.load(passphrase=args.pw)
    print("\n".join(sorted(f"{k}=***{v[-4:]}" for k,v in ks._cache.items())))
